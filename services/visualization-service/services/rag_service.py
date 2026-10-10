"""Chat RAG sobre los instrumentos del usuario y del sistema.

Ingesta: la colección `instrumentos` la escribe el storage-service (solo con
metadatos aprobados). `indexar()` le pide asegurar la ingesta de los
instrumentos de una investigación; los no aprobados se reportan como omitidos.

Consulta: se vectoriza la pregunta y se recuperan los fragmentos más cercanos
(ficha del instrumento, reactivos con sus resultados, texto de entrevistas).
  - Con `instrumentoIds`: solo la investigación activa.
  - Sin ellos: todo el acervo aprobado del sistema.
La respuesta la genera Ollama (SSE o JSON) y cada consulta queda en `rag_log`.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from shared.db.core.config import settings
from shared.models.rag_log import RagLog

from models import ChatRequest, ChatResponse, FuenteChatOut, IndexRequest
from services import ollama_client, prompt, storage_client, vectores

logger = logging.getLogger("visualization-service")

_TIPOS = {"Encuesta", "Entrevista", "Prueba estandarizada"}
MENSAJE_SIN_CONTEXTO = (
    "No encontré información sobre eso en los instrumentos consultados. Recuerda que "
    "solo entran al RAG los instrumentos con metadatos aprobados por su autor; "
    "puedes ampliar la selección de tu investigación."
)


def fabrica_sesiones():
    """Sesión de BD para registrar consultas (reemplazable en pruebas)."""
    from shared.db.session import SessionLocal

    return SessionLocal()


# ── Ingesta ────────────────────────────────────────────────────────────────────


def indexar(peticion: IndexRequest) -> dict[str, Any]:
    resultados: list[dict[str, Any]] = []
    for instrumento_id in peticion.instrumentoIds:
        if not instrumento_id.isdigit():
            resultados.append(
                {"instrumentoId": instrumento_id, "chunks": 0, "estado": "omitido", "motivo": "Identificador inválido."}
            )
            continue
        id_crudo = int(instrumento_id)
        try:
            if not peticion.reindexar:
                estado = storage_client.estado_indice(id_crudo)
                if estado.get("indexado"):
                    resultados.append(
                        {"instrumentoId": instrumento_id, "chunks": estado.get("chunks", 0), "estado": "indexado", "motivo": None}
                    )
                    continue
            r = storage_client.indexar(id_crudo, reindexar=True)
            resultados.append(
                {"instrumentoId": instrumento_id, "chunks": r.get("chunks", 0), "estado": r.get("estado", "indexado"), "motivo": r.get("motivo")}
            )
        except storage_client.StorageError as exc:
            if exc.status_code is None:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            resultados.append({"instrumentoId": instrumento_id, "chunks": 0, "estado": "omitido", "motivo": str(exc)})

    indexados = [r for r in resultados if r["estado"] == "indexado"]
    total = sum(int(r["chunks"] or 0) for r in indexados)
    return {
        "coleccion": settings.CHROMA_COLLECTION_INSTRUMENTOS,
        "total_chunks": total,
        "instrumentos": resultados,
        "mensaje": f"{len(indexados)} de {len(resultados)} instrumento(s) disponibles en el RAG ({total} fragmentos).",
    }


# ── Recuperación ───────────────────────────────────────────────────────────────


def _kpis(valor: Any) -> list[str]:
    if isinstance(valor, list):
        return [str(k) for k in valor]
    if isinstance(valor, str) and valor:
        try:
            datos = json.loads(valor)
        except json.JSONDecodeError:
            return []
        return [str(k) for k in datos] if isinstance(datos, list) else []
    return []


def recuperar(peticion: ChatRequest) -> tuple[list[dict[str, Any]], list[FuenteChatOut]]:
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc
    if coleccion is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Aún no hay instrumentos en el RAG: aprueba los metadatos de tus instrumentos.",
        )
    try:
        vector = vectores.embed_text(peticion.pregunta)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo cargar el modelo de embeddings: %s", exc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No se pudo cargar el modelo de embeddings.") from exc

    ids = [i for i in (peticion.instrumentoIds or []) if i]
    where = {"instrumentoId": {"$in": ids}} if ids else None
    try:
        res = coleccion.query(
            query_embeddings=[vector],
            n_results=peticion.top_k,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc

    fragmentos: list[dict[str, Any]] = []
    for meta, doc, dist in zip(
        (res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0], (res.get("distances") or [[]])[0]
    ):
        meta = meta or {}
        fragmentos.append(
            {
                "instrumentoId": str(meta.get("instrumentoId", "")),
                "titulo": str(meta.get("titulo", "")),
                "tipo": meta.get("tipo") if meta.get("tipo") in _TIPOS else "Encuesta",
                "investigador": str(meta.get("investigador", "")),
                "kpis": _kpis(meta.get("kpis")),
                "seccion": str(meta.get("seccion", "")),
                "fragmento": str(doc or ""),
                "score": round(1.0 - float(dist), 4),
            }
        )

    fuentes: list[FuenteChatOut] = []
    vistos: set[str] = set()
    for f in fragmentos:
        if f["instrumentoId"] in vistos:
            continue
        vistos.add(f["instrumentoId"])
        fuentes.append(
            FuenteChatOut(
                instrumentoId=f["instrumentoId"],
                titulo=f["titulo"],
                tipo=f["tipo"],
                investigador=f["investigador"],
                kpis=f["kpis"],
                fragmento=f["fragmento"],
            )
        )
    return fragmentos, fuentes


def registrar_consulta(pregunta: str, respuesta: str, modelo: str, chunks: int, inicio: float) -> None:
    """Guarda la consulta en rag_log (mejor esfuerzo: nunca rompe el chat)."""
    try:
        sesion = fabrica_sesiones()
        try:
            sesion.add(
                RagLog(
                    pregunta=pregunta,
                    respuesta=respuesta,
                    modelo_usado=modelo,
                    chunks_usados=chunks,
                    latencia_ms=int((time.monotonic() - inicio) * 1000),
                )
            )
            sesion.commit()
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo registrar la consulta RAG: %s", exc)


# ── Respuesta ──────────────────────────────────────────────────────────────────


async def responder(peticion: ChatRequest):
    inicio = time.monotonic()
    modelo = peticion.modelo or settings.OLLAMA_MODEL
    fragmentos, fuentes = recuperar(peticion)
    contexto = peticion.contexto.model_dump() if peticion.contexto else None
    texto_prompt = prompt.construir(peticion.pregunta, fragmentos, contexto)

    if peticion.stream:
        return StreamingResponse(
            _sse(peticion.pregunta, texto_prompt, modelo, fragmentos, fuentes, inicio),
            media_type="text/event-stream",
        )

    if not fragmentos:
        respuesta, degradado = MENSAJE_SIN_CONTEXTO, False
    else:
        respuesta, degradado = await ollama_client.generar_no_stream(texto_prompt, modelo)
    registrar_consulta(peticion.pregunta, respuesta, modelo, len(fragmentos), inicio)
    return ChatResponse(respuesta=respuesta, fuentes=fuentes, modelo=modelo, degradado=degradado)


async def _sse(pregunta, texto_prompt, modelo, fragmentos, fuentes, inicio):  # noqa: ANN001
    partes: list[str] = []
    if fragmentos:
        async for trozo in ollama_client.generar_stream(texto_prompt, modelo):
            partes.append(trozo)
            yield f"event: token\ndata: {json.dumps({'t': trozo}, ensure_ascii=False)}\n\n"
    else:
        partes.append(MENSAJE_SIN_CONTEXTO)
        yield f"event: token\ndata: {json.dumps({'t': MENSAJE_SIN_CONTEXTO}, ensure_ascii=False)}\n\n"
    datos_fuentes = json.dumps({"fuentes": [f.model_dump() for f in fuentes]}, ensure_ascii=False)
    yield f"event: fuentes\ndata: {datos_fuentes}\n\n"
    yield "event: fin\ndata: {}\n\n"
    registrar_consulta(pregunta, "".join(partes), modelo, len(fragmentos), inicio)
