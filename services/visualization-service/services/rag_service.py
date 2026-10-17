"""Chat RAG sobre los instrumentos del usuario y del sistema.

Ingesta: la colección `instrumentos` la escribe el storage-service (solo con
metadatos aprobados). `indexar()` le pide asegurar la ingesta de los
instrumentos de una investigación; los no aprobados se reportan como omitidos.

Consulta: se vectoriza la pregunta y se recuperan los fragmentos más cercanos
(ficha del instrumento, reactivos con sus resultados, texto de entrevistas).
Solo pasan los que alcanzan `RAG_MIN_SCORE`; si ninguno lo hace, se responde
`MENSAJE_SIN_CONTEXTO` sin llamar al LLM.
  - Con `instrumentoIds`: solo la investigación activa.
  - Sin ellos: todo el acervo aprobado del sistema.
La respuesta la genera Ollama (SSE o JSON) y cada consulta queda en `rag_log`.
"""
from __future__ import annotations

import json
import logging
import time
import unicodedata
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from shared.db.core.config import settings
from shared.models.rag_log import RagLog

from models import ChatRequest, ChatResponse, FuenteChatOut, IndexRequest
from services import ollama_client, prompt, storage_client, vectores

logger = logging.getLogger("visualization-service")

_TIPOS = {"Encuesta", "Entrevista", "Prueba estandarizada"}
# Se piden más candidatos de los que caben y se eligen con tope por instrumento.
_CANDIDATOS_POR_FRAGMENTO = 4
_MAX_FICHAS_POR_INSTRUMENTO = 1
_MAX_FRAGMENTOS_POR_INSTRUMENTO = 3
MENSAJE_SIN_CONTEXTO = (
    f"{prompt.SIN_INFORMACION} Recuerda que solo entran al RAG los instrumentos con "
    "metadatos aprobados por su autor; puedes ampliar la selección de tu investigación."
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
            n_results=peticion.top_k * _CANDIDATOS_POR_FRAGMENTO,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc

    fragmentos: list[dict[str, Any]] = []
    encabezados: dict[str, int] = {}
    por_instrumento: dict[str, int] = {}
    for meta, doc, dist in zip(
        (res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0], (res.get("distances") or [[]])[0]
    ):
        meta = meta or {}
        score = round(1.0 - float(dist), 4)
        if score < settings.RAG_MIN_SCORE:
            continue  # poco relacionado: no se le da al LLM para que no improvise
        if len(fragmentos) >= peticion.top_k:
            break
        # Diversidad: las fichas (encabezado) se parecen a casi cualquier pregunta y,
        # sin tope, desplazan a los reactivos con resultados y al texto de entrevistas.
        inst, seccion = str(meta.get("instrumentoId", "")), str(meta.get("seccion", ""))
        if seccion == "encabezado" and encabezados.get(inst, 0) >= _MAX_FICHAS_POR_INSTRUMENTO:
            continue
        if por_instrumento.get(inst, 0) >= _MAX_FRAGMENTOS_POR_INSTRUMENTO:
            continue
        if seccion == "encabezado":
            encabezados[inst] = encabezados.get(inst, 0) + 1
        por_instrumento[inst] = por_instrumento.get(inst, 0) + 1
        fragmentos.append(
            {
                "instrumentoId": str(meta.get("instrumentoId", "")),
                "titulo": str(meta.get("titulo", "")),
                "tipo": meta.get("tipo") if meta.get("tipo") in _TIPOS else "Encuesta",
                "investigador": str(meta.get("investigador", "")),
                "kpis": _kpis(meta.get("kpis")),
                "seccion": str(meta.get("seccion", "")),
                "fragmento": str(doc or ""),
                "score": score,
            }
        )

    # Una fuente por instrumento, numerada en orden de relevancia. El prompt cita
    # con ese mismo número, así que [Fuente n] es la n-ésima tarjeta de la UI.
    fuentes: list[FuenteChatOut] = []
    numeros: dict[str, int] = {}
    for f in fragmentos:
        if f["instrumentoId"] in numeros:
            f["numero"] = numeros[f["instrumentoId"]]
            continue
        numeros[f["instrumentoId"]] = f["numero"] = len(numeros) + 1
        fuentes.append(
            FuenteChatOut(
                numero=f["numero"],
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

# Caracteres que el streaming retiene al final para poder quitar la frase de
# «sin información» si el modelo la pega tras una respuesta que sí dio.
_RETENCION = len(prompt.SIN_INFORMACION) + 8


def quitar_sin_informacion_sobrante(texto: str) -> str:
    """Quita la frase de «sin información» cuando acompaña a una respuesta real.

    El modelo de 3B a veces la añade al final aunque sí respondió; si es lo único
    que dijo, se conserva (es la negativa correcta).
    """
    frase = prompt.SIN_INFORMACION
    sin_frase = texto.replace(frase, "").strip()
    if frase not in texto or len(sin_frase) < 20:
        return texto
    return sin_frase


# Inicios con los que el modelo dice que no puede responder (la frase exacta del
# prompt o sus variantes: «No tengo información relacionada con la pregunta…»).
_NEGATIVAS = ("no tengo informacion relacionada", "lo siento, pero no tengo informacion", "no encontre informacion")


def es_negativa(texto: str) -> bool:
    """La respuesta es «no tengo información» (y no una respuesta real)."""
    normalizado = unicodedata.normalize("NFKD", texto.strip().lower()).encode("ascii", "ignore").decode()
    return len(normalizado) < 400 and normalizado.startswith(_NEGATIVAS)


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
        respuesta, degradado = await ollama_client.generar_no_stream(texto_prompt, modelo, sistema=prompt.SISTEMA)
        respuesta = quitar_sin_informacion_sobrante(respuesta)
    usados = len(fragmentos)
    if es_negativa(respuesta):  # no respondió con ellas: no se muestran como fuentes
        fuentes, usados = [], 0
    registrar_consulta(peticion.pregunta, respuesta, modelo, usados, inicio)
    return ChatResponse(respuesta=respuesta, fuentes=fuentes, modelo=modelo, degradado=degradado)


async def _sse(pregunta, texto_prompt, modelo, fragmentos, fuentes, inicio):  # noqa: ANN001
    partes: list[str] = []
    if fragmentos:
        # Se emite con un retraso de `_RETENCION` caracteres: al terminar, el
        # remanente se limpia de la frase de «sin información» sobrante.
        generado, enviados = "", 0
        async for trozo in ollama_client.generar_stream(texto_prompt, modelo, sistema=prompt.SISTEMA):
            generado += trozo
            hasta = len(generado) - _RETENCION
            if hasta > enviados:
                yield f"event: token\ndata: {json.dumps({'t': generado[enviados:hasta]}, ensure_ascii=False)}\n\n"
                enviados = hasta
        final = quitar_sin_informacion_sobrante(generado)
        if final.startswith(generado[:enviados]):
            resto = final[enviados:]
        else:  # la frase quedó antes de lo ya enviado: no se puede retirar
            resto = generado[enviados:]
            final = generado
        if resto:
            yield f"event: token\ndata: {json.dumps({'t': resto}, ensure_ascii=False)}\n\n"
        partes.append(final)
    else:
        partes.append(MENSAJE_SIN_CONTEXTO)
        yield f"event: token\ndata: {json.dumps({'t': MENSAJE_SIN_CONTEXTO}, ensure_ascii=False)}\n\n"
    respuesta = "".join(partes)
    usados = len(fragmentos)
    if es_negativa(respuesta):  # no respondió con ellas: no se muestran como fuentes
        fuentes, usados = [], 0
    datos_fuentes = json.dumps({"fuentes": [f.model_dump() for f in fuentes]}, ensure_ascii=False)
    yield f"event: fuentes\ndata: {datos_fuentes}\n\n"
    yield "event: fin\ndata: {}\n\n"
    registrar_consulta(pregunta, respuesta, modelo, usados, inicio)
