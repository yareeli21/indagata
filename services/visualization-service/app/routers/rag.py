"""Router RAG — POST /rag/index y POST /rag/chat (diseño §4.6, §4.7, §4.12).

Centro de la demo: indexa el contenido de los instrumentos de una investigación
en una colección Chroma por investigación y responde preguntas fundamentadas con
Ollama, citando las fuentes recuperadas.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core import chroma_client, embeddings, ollama_client, prompt, sources
from app.schemas.rag import (
    ChatRequest,
    ChatResponse,
    FuenteChatOut,
    IndexInstrumentoResultado,
    IndexRequest,
    IndexResponse,
)
from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

router = APIRouter(prefix="/rag", tags=["rag"])

# Tipos válidos para FuenteChatOut (§2.4); cualquier otro cae a "Encuesta".
_TIPOS_VALIDOS = {"Encuesta", "Entrevista", "Prueba estandarizada"}


def _tipo_seguro(valor) -> str:
    return valor if valor in _TIPOS_VALIDOS else "Encuesta"


def _deserializar_kpis(valor) -> list[str]:
    """Deserializa el string JSON de kpis guardado en la metadata de Chroma."""
    if isinstance(valor, list):
        return [str(k) for k in valor]
    if isinstance(valor, str) and valor:
        try:
            data = json.loads(valor)
        except json.JSONDecodeError:
            return []
        return [str(k) for k in data] if isinstance(data, list) else []
    return []


# ── POST /rag/index ────────────────────────────────────────────────────────────
@router.post("/index", response_model=IndexResponse, summary="Indexar instrumentos")
async def indexar(peticion: IndexRequest) -> IndexResponse:
    """Indexa los instrumentos de una investigación en su colección Chroma."""
    nombre = chroma_client.nombre_coleccion(peticion.investigacionId)

    try:
        cliente = chroma_client.get_client()
        if peticion.reindexar:
            try:
                cliente.delete_collection(name=nombre)
            except Exception:  # noqa: BLE001 - la colección puede no existir aún
                logger.debug("Colección %s inexistente al reindexar.", nombre)
        coleccion = chroma_client.get_or_create_collection(nombre, client=cliente)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status_code=502, detail="Vector store no disponible.")

    resultados: list[IndexInstrumentoResultado] = []
    total_chunks = 0

    for instrumento_id in peticion.instrumentoIds:
        artefacto = await sources.resolver_artefacto(instrumento_id)
        if artefacto is None:
            resultados.append(
                IndexInstrumentoResultado(
                    instrumentoId=instrumento_id,
                    chunks=0,
                    estado="omitido",
                    motivo=f"sin artefacto JSON para instrumentoId={instrumento_id}",
                )
            )
            continue

        from app.core import chunking

        texto = sources.extraer_texto(artefacto)
        chunks = chunking.trocear(texto)
        if not chunks:
            resultados.append(
                IndexInstrumentoResultado(
                    instrumentoId=instrumento_id,
                    chunks=0,
                    estado="omitido",
                    motivo=f"sin texto indexable para instrumentoId={instrumento_id}",
                )
            )
            continue

        meta = sources.extraer_metadata(artefacto, instrumento_id)
        kpis_json = json.dumps(meta.get("kpis", []), ensure_ascii=False)

        try:
            vectores = embeddings.embed_texts(chunks)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("No se pudo cargar el modelo de embeddings: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="No se pudo cargar el modelo de embeddings.",
            )

        ids = [f"{peticion.investigacionId}:{instrumento_id}:{n}" for n in range(len(chunks))]
        metadatas = [
            {
                "instrumentoId": instrumento_id,
                "titulo": meta.get("titulo", ""),
                "tipo": _tipo_seguro(meta.get("tipo")),
                "investigador": meta.get("investigador", ""),
                "kpis": kpis_json,
                "investigacionId": peticion.investigacionId,
                "chunk_index": n,
            }
            for n in range(len(chunks))
        ]

        try:
            chroma_client.upsert(coleccion, ids, vectores, chunks, metadatas)
        except Exception as exc:  # noqa: BLE001
            logger.error("Vector store no disponible: %s", exc)
            raise HTTPException(status_code=502, detail="Vector store no disponible.")

        total_chunks += len(chunks)
        resultados.append(
            IndexInstrumentoResultado(
                instrumentoId=instrumento_id,
                chunks=len(chunks),
                estado="indexado",
            )
        )

    indexados = sum(1 for r in resultados if r.estado == "indexado")
    return IndexResponse(
        coleccion=nombre,
        total_chunks=total_chunks,
        instrumentos=resultados,
        mensaje=f"Se indexaron {indexados} instrumento(s) con {total_chunks} fragmento(s).",
    )


# ── POST /rag/chat ───────────────────────────────────────────────────────────
def _coleccion_existente(nombre: str):
    """Obtiene la colección existente; 409 si no está indexada, 502 si Chroma cae."""
    try:
        cliente = chroma_client.get_client()
        existentes = {c.name for c in cliente.list_collections()}
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status_code=502, detail="Vector store no disponible.")
    if nombre not in existentes:
        raise HTTPException(
            status_code=409,
            detail="La investigación no está indexada todavía.",
        )
    return chroma_client.get_or_create_collection(nombre, client=cliente)


def _construir_fuentes(resultado: dict) -> list[FuenteChatOut]:
    """Deduplica por instrumentoId; `fragmento` = chunk más cercano."""
    metadatas = (resultado.get("metadatas") or [[]])[0]
    documentos = (resultado.get("documents") or [[]])[0]
    fuentes: list[FuenteChatOut] = []
    vistos: set[str] = set()
    for meta, doc in zip(metadatas, documentos):
        meta = meta or {}
        instrumento_id = str(meta.get("instrumentoId", ""))
        if instrumento_id in vistos:
            continue
        vistos.add(instrumento_id)
        fuentes.append(
            FuenteChatOut(
                instrumentoId=instrumento_id,
                titulo=str(meta.get("titulo", "")),
                tipo=_tipo_seguro(meta.get("tipo")),
                investigador=str(meta.get("investigador", "")),
                kpis=_deserializar_kpis(meta.get("kpis")),
                fragmento=str(doc or ""),
            )
        )
    return fuentes


@router.post("/chat", summary="Chat RAG fundamentado")
async def chat(peticion: ChatRequest):
    """Responde una pregunta fundamentada en los instrumentos de la investigación."""
    nombre = chroma_client.nombre_coleccion(peticion.investigacionId)
    coleccion = _coleccion_existente(nombre)
    modelo = peticion.modelo or settings.OLLAMA_MODEL

    try:
        vector = embeddings.embed_text(peticion.pregunta)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo cargar el modelo de embeddings: %s", exc)
        raise HTTPException(
            status_code=500, detail="No se pudo cargar el modelo de embeddings."
        )

    where = None
    if peticion.instrumentoIds:
        where = {"instrumentoId": {"$in": list(peticion.instrumentoIds)}}

    try:
        resultado = chroma_client.query(coleccion, vector, peticion.top_k, where=where)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status_code=502, detail="Vector store no disponible.")

    fuentes = _construir_fuentes(resultado)
    contexto = [f.model_dump() for f in fuentes]
    texto_prompt = prompt.construir(peticion.pregunta, contexto)

    if peticion.stream:
        return StreamingResponse(
            _sse(texto_prompt, modelo, fuentes),
            media_type="text/event-stream",
        )

    respuesta, degradado = await ollama_client.generar_no_stream(texto_prompt, modelo)
    return ChatResponse(
        respuesta=respuesta,
        fuentes=fuentes,
        modelo=modelo,
        degradado=degradado,
    )


async def _sse(texto_prompt: str, modelo: str, fuentes: list[FuenteChatOut]):
    """Emite SSE: event token/data por trozo, luego fuentes, luego fin (§4.9)."""
    async for trozo in ollama_client.generar_stream(texto_prompt, modelo):
        data = json.dumps({"t": trozo}, ensure_ascii=False)
        yield f"event: token\ndata: {data}\n\n"
    fuentes_data = json.dumps(
        {"fuentes": [f.model_dump() for f in fuentes]}, ensure_ascii=False
    )
    yield f"event: fuentes\ndata: {fuentes_data}\n\n"
    yield "event: fin\ndata: {}\n\n"
