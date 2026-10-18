"""Evaluación automática de cada respuesta del chat (métricas tipo RAGAS, sin referencia).

Se calculan EN SEGUNDO PLANO después de entregar la respuesta y se guardan en la
misma fila de `rag_log` (`metricas`, `modelo_juez`, `fecha_metricas`). Siguen las
definiciones de RAGAS 0.4.3 (`ragas.metrics.collections`), reimplementadas con
prompts cortos en español para el juez local (Ollama), sin las dependencias de
RAGAS (LangChain, datasets, instructor…) en el servicio del chat:

  fidelidad            (Faithfulness)  el juez parte la respuesta en afirmaciones y
                       verifica cada una contra el contexto que vio el modelo:
                       afirmaciones sustentadas / total.
  relevancia           (AnswerRelevancy, strictness=3) el juez genera 3 preguntas que
                       la respuesta contesta; se promedia el coseno de sus embeddings
                       con el de la pregunta original. Vale 0 si la respuesta es
                       evasiva (todas las generaciones la marcan como noncommittal).
  precision_contexto   (ContextUtilization = ContextPrecisionWithoutReference) el juez
                       decide si cada fragmento, en su orden, sirvió para la
                       respuesta (v_k ∈ {0,1}); precisión media ponderada:
                       Σ_k (precision@k · v_k) / (Σ v_k + 1e-10).

El juez es un modelo pequeño: las cifras son una evaluación APROXIMADA (la interfaz
lo advierte). Es configurable (`RAG_JUEZ_MODELO`) y se apaga con `RAG_METRICAS`.
La validación contra RAGAS real está en `tools/rag/evaluar_ragas.py`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable

from shared.db.core.config import settings
from shared.models.rag_log import RagLog

logger = logging.getLogger("visualization-service")

VERSION = "1.0"  # cambia si cambian los prompts o las fórmulas
_ESTRICTEZ = 3  # preguntas generadas en la relevancia (strictness de RAGAS)
_MAX_CONTEXTO = 6000  # caracteres de contexto por llamada (cabe en num_ctx 4096 con el prompt)

# Estados que ve la interfaz (también van en `metricas.estado`).
CALCULANDO, LISTO, OMITIDA, ERROR = "calculando", "listo", "omitida", "error"

# ── Prompts del juez (JSON, temperatura 0) ─────────────────────────────────────

# Un ejemplo resuelto en cada prompt: con instrucciones solas, el juez de 3B partía la
# respuesta en fragmentos sin verbo («calificaciones», «la pregunta p03») y alteraba cifras
# («el 10 % de los 60» en lugar de «10 de 60»), lo que bajaba la fidelidad de respuestas correctas.
_P_AFIRMACIONES = (
    "Divide la RESPUESTA en afirmaciones completas (cada una es una oración con sujeto y verbo, entendible "
    "sola). Copia las cifras y los IDs tal como aparecen. Ignora las citas como [Fuente 1].\n"
    'Ejemplo: RESPUESTA «En p04, el 13.3 % (4 de 30) del turno vespertino está de acuerdo [Fuente 1].» → '
    '{{"afirmaciones": ["En la pregunta p04, el 13.3 % del turno vespertino está de acuerdo.", '
    '"En la pregunta p04, 4 de 30 personas del turno vespertino están de acuerdo."]}}\n'
    'Responde solo JSON: {{"afirmaciones": ["...", "..."]}}\n\n'
    "PREGUNTA: {pregunta}\nRESPUESTA: {respuesta}"
)
# Veredictos por NÚMERO y con la razón antes del veredicto (el orden de RAGAS): cuando se
# le pedía copiar cada afirmación, el juez de 3B se trababa al copiarla («R005 respondño…»)
# y marcaba 0 afirmaciones que estaban literalmente en el contexto (evaluación de la Fase 4).
_P_VEREDICTOS = (
    "Para cada AFIRMACIÓN numerada decide si se puede deducir DIRECTAMENTE del CONTEXTO (1) o no (0). "
    "No uses conocimiento propio. Si la afirmación dice lo mismo que el CONTEXTO con otras palabras o comillas "
    "distintas, vale 1; si una cifra o un dato es distinto, vale 0. No copies las afirmaciones: usa su número.\n"
    'Responde solo JSON: {{"veredictos": [{{"n": 1, "razon": "<máximo 12 palabras>", "veredicto": 0 o 1}}]}}\n\n'
    "CONTEXTO:\n{contexto}\n\nAFIRMACIONES:\n{afirmaciones}"
)
_P_PREGUNTA = (
    "Escribe UNA pregunta que la RESPUESTA conteste exactamente. Indica también si la respuesta es "
    "evasiva o no se compromete (por ejemplo «no lo sé», «no tengo información»).\n"
    'Responde solo JSON: {{"pregunta": "...", "evasiva": true o false}}\n\nRESPUESTA: {respuesta}'
)
_P_UTILIDAD = (
    "¿El CONTEXTO sirvió para llegar a la RESPUESTA de la PREGUNTA? 1 si fue útil, 0 si no.\n"
    'Responde solo JSON: {{"razon": "<máximo 15 palabras>", "veredicto": 0 o 1}}\n\n'
    "PREGUNTA: {pregunta}\nRESPUESTA: {respuesta}\nCONTEXTO: {contexto}"
)

Juez = Callable[[str], Any]  # async: prompt → dict (JSON del juez) o None


async def _juez_ollama(prompt: str) -> dict[str, Any] | None:
    """Llamada al juez (Ollama, JSON, temperatura 0); None si no responde o no es JSON."""
    from services import ollama_client

    modelo = settings.RAG_JUEZ_MODELO or settings.OLLAMA_MODEL
    texto, degradado = await ollama_client.generar_no_stream(prompt, modelo, formato="json", opciones={"temperature": 0})
    if degradado:
        return None
    try:
        datos = json.loads(texto)
    except ValueError:
        logger.warning("Juez de métricas: respuesta no JSON %r", texto[:200])
        return None
    return datos if isinstance(datos, dict) else None


def _coseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def veredictos_por_numero(items: list[Any], total: int) -> list[int]:
    """Veredictos 0/1 en el orden de las afirmaciones (por su `n`, o por posición si no lo trae)."""
    def _uno(v: Any) -> int:
        return 1 if str((v or {}).get("veredicto") if isinstance(v, dict) else v).strip() in ("1", "True", "true") else 0

    con_numero = {int(i["n"]): _uno(i) for i in items if isinstance(i, dict) and str(i.get("n", "")).isdigit()}
    if len(con_numero) == total and set(con_numero) == set(range(1, total + 1)):
        return [con_numero[n] for n in range(1, total + 1)]
    if len(items) != total:
        raise ValueError(f"El juez devolvió {len(items)} veredictos para {total} afirmaciones.")
    return [_uno(i) for i in items]


def precision_media(veredictos: list[int]) -> float:
    """Precisión media ponderada de RAGAS (ContextPrecision / ContextUtilization)."""
    numerador = sum((sum(veredictos[: i + 1]) / (i + 1)) * v for i, v in enumerate(veredictos))
    return numerador / (sum(veredictos) + 1e-10)


# ── Métricas ───────────────────────────────────────────────────────────────────


async def fidelidad(pregunta: str, respuesta: str, contextos: list[str], juez: Juez) -> tuple[float | None, dict[str, Any]]:
    """Afirmaciones sustentadas por el contexto / total (None si no hay afirmaciones)."""
    datos = await juez(_P_AFIRMACIONES.format(pregunta=pregunta, respuesta=respuesta))
    afirmaciones = [str(a).strip() for a in (datos or {}).get("afirmaciones") or [] if str(a).strip()]
    if not afirmaciones:
        return None, {"afirmaciones": []}
    contexto = "\n".join(contextos)[:_MAX_CONTEXTO]
    lista = "\n".join(f"{i}. {a}" for i, a in enumerate(afirmaciones, start=1))
    datos = await juez(_P_VEREDICTOS.format(contexto=contexto, afirmaciones=lista))
    marcas = veredictos_por_numero((datos or {}).get("veredictos") or [], len(afirmaciones))
    no_sustentadas = [a for a, m in zip(afirmaciones, marcas) if not m]
    return sum(marcas) / len(marcas), {"afirmaciones": len(afirmaciones), "no_sustentadas": no_sustentadas}


async def relevancia(pregunta: str, respuesta: str, juez: Juez, embeber: Callable[[list[str]], list[list[float]]]
                     ) -> tuple[float | None, dict[str, Any]]:
    """Coseno medio entre la pregunta y 3 preguntas generadas desde la respuesta (0 si es evasiva)."""
    generadas: list[str] = []
    evasivas: list[bool] = []
    for _ in range(_ESTRICTEZ):
        datos = await juez(_P_PREGUNTA.format(respuesta=respuesta))
        if datos and str(datos.get("pregunta") or "").strip():
            generadas.append(str(datos["pregunta"]).strip())
            evasivas.append(bool(datos.get("evasiva")))
    if not generadas:
        return None, {"preguntas_generadas": []}
    vectores = embeber([pregunta, *generadas])
    media = sum(_coseno(vectores[0], v) for v in vectores[1:]) / len(generadas)
    valor = 0.0 if all(evasivas) else max(0.0, media)
    return valor, {"preguntas_generadas": generadas, "evasiva": all(evasivas)}


async def precision_contexto(pregunta: str, respuesta: str, contextos: list[str], juez: Juez) -> tuple[float | None, dict[str, Any]]:
    """¿Los fragmentos útiles para la respuesta están primero? (precisión media ponderada)."""
    if not contextos:
        return None, {"utiles": []}
    veredictos: list[int] = []
    for c in contextos:
        datos = await juez(_P_UTILIDAD.format(pregunta=pregunta, respuesta=respuesta, contexto=c[:1500]))
        veredictos.append(1 if str((datos or {}).get("veredicto")).strip() in ("1", "True", "true") else 0)
    return precision_media(veredictos), {"utiles": veredictos}


async def evaluar(pregunta: str, respuesta: str, contextos: list[str], juez: Juez | None = None,
                  embeber: Callable[[list[str]], list[list[float]]] | None = None) -> dict[str, Any]:
    """Las tres métricas de una respuesta, con su detalle (lo que se guarda en rag_log.metricas)."""
    from services import vectores

    juez = juez or _juez_ollama
    embeber = embeber or vectores.embed_texts
    salida: dict[str, Any] = {"estado": LISTO, "version": VERSION, "detalle": {}}
    for nombre, calculo in (
        ("fidelidad", fidelidad(pregunta, respuesta, contextos, juez)),
        ("relevancia", relevancia(pregunta, respuesta, juez, embeber)),
        ("precision_contexto", precision_contexto(pregunta, respuesta, contextos, juez)),
    ):
        try:
            valor, detalle = await calculo
        except Exception as exc:  # noqa: BLE001 — una métrica fallida no tumba las demás
            logger.warning("Métrica %s falló: %s", nombre, exc)
            valor, detalle = None, {"error": str(exc)[:200]}
        salida[nombre] = None if valor is None else round(float(valor), 3)
        salida["detalle"][nombre] = detalle
    return salida


# ── Cola en segundo plano ──────────────────────────────────────────────────────

_cerrojo: asyncio.Lock | None = None
_tareas: set[asyncio.Task] = set()


def omitida(motivo: str) -> dict[str, Any]:
    return {"estado": OMITIDA, "motivo": motivo, "version": VERSION}


async def _evaluar_consulta(rag_log_id: int, fabrica: Callable[[], Any]) -> None:
    """Calcula y guarda las métricas de una consulta (una a la vez: no compite con el chat)."""
    global _cerrojo
    _cerrojo = _cerrojo or asyncio.Lock()
    async with _cerrojo:
        sesion = fabrica()
        try:
            fila = sesion.get(RagLog, rag_log_id)
            if fila is None:
                return
            contextos = [c.get("texto", "") for c in fila.contexto_usado or [] if c.get("texto")]
            try:
                metricas = await evaluar(fila.pregunta, fila.respuesta or "", contextos)
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudieron calcular las métricas de la consulta %s: %s", rag_log_id, exc)
                metricas = {"estado": ERROR, "motivo": str(exc)[:200], "version": VERSION}
            fila.metricas = metricas
            fila.modelo_juez = settings.RAG_JUEZ_MODELO or settings.OLLAMA_MODEL
            fila.fecha_metricas = datetime.now(timezone.utc).replace(tzinfo=None)
            sesion.commit()
        finally:
            sesion.close()


def programar(rag_log_id: int, fabrica: Callable[[], Any]) -> None:
    """Agenda la evaluación de una consulta sin bloquear la respuesta del chat."""
    try:
        tarea = asyncio.get_running_loop().create_task(_evaluar_consulta(rag_log_id, fabrica))
    except RuntimeError:  # sin loop (no debería pasar dentro de FastAPI)
        logger.warning("Sin loop de eventos: no se evaluó la consulta %s", rag_log_id)
        return
    _tareas.add(tarea)  # referencia fuerte hasta que termine
    tarea.add_done_callback(_tareas.discard)


def estado_publico(fila: RagLog) -> dict[str, Any]:
    """Lo que ve la interfaz: estado, las tres métricas, el juez y la fecha."""
    metricas = fila.metricas or {}
    if not metricas:
        estado = CALCULANDO if settings.RAG_METRICAS else OMITIDA
        metricas = {"estado": estado, "motivo": None if settings.RAG_METRICAS else "Métricas desactivadas."}
    return {
        "consultaId": fila.rag_log_id,
        "estado": metricas.get("estado", LISTO),
        "motivo": metricas.get("motivo"),
        "fidelidad": metricas.get("fidelidad"),
        "relevancia": metricas.get("relevancia"),
        "precisionContexto": metricas.get("precision_contexto"),
        "noSustentadas": ((metricas.get("detalle") or {}).get("fidelidad") or {}).get("no_sustentadas") or [],
        "modeloJuez": fila.modelo_juez,
        "fecha": fila.fecha_metricas,
    }
