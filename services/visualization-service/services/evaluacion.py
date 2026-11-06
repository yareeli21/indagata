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

Además, sin juez (determinista): `cifras_sin_sustento`, las cifras de la respuesta que no aparecen en el
contexto usado (Fase 4 del rediseño, 28 oct).

Respuestas calculadas mostradas tal cual (`literal`): la fidelidad es 1 por construcción y el juez solo mide la
relevancia y la precisión del contexto contra el resultado calculado que se usó (antes no se medían). Si el juez
devuelve un número de veredictos distinto al de afirmaciones, se le vuelve a preguntar y, si insiste, se evalúa
cada afirmación por separado (antes la fidelidad quedaba vacía: «—»).

El juez es un modelo pequeño: las cifras son una evaluación APROXIMADA (la interfaz
lo advierte). Es configurable (`RAG_JUEZ_MODELO`) y se apaga con `RAG_METRICAS`.

Varios jueces sobre las mismas respuestas (experimento redactor × juez, 28 oct): `solicitar(..., modelo_juez=)` evalúa
con otro modelo; cada evaluación se guarda en `rag_metrica_juez` (una fila por respuesta y juez) y la del juez por
defecto también en `rag_log.metricas`, que es la que muestra la interfaz.
La validación contra RAGAS real está en `tools/rag/evaluar_ragas.py`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Callable

from shared.db.core.config import settings
from shared.models.rag_evaluacion import RagMetricaJuez
from shared.models.rag_log import RagLog

logger = logging.getLogger("visualization-service")

VERSION = "1.3"  # 1.3: un juez por parámetro y una evaluación por juez (rag_metrica_juez); 1.2: prompt de utilidad con ejemplo; 1.1: veredicto por afirmación si el juez se equivoca de cuenta; cifras sin sustento; calculadas medidas
_ESTRICTEZ = 3  # preguntas generadas en la relevancia (strictness de RAGAS)
_MAX_CONTEXTO = 6000  # caracteres de contexto por llamada (cabe en num_ctx 4096 con el prompt)

# Estados que ve la interfaz (también van en `metricas.estado`).
CALCULANDO, LISTO, OMITIDA, ERROR, CALCULADA = "calculando", "listo", "omitida", "error", "calculada"
PENDIENTE = "pendiente"  # bajo demanda: se calculará cuando la persona lo pida

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
_P_VEREDICTO_UNO = (
    "¿La AFIRMACIÓN se puede deducir DIRECTAMENTE del CONTEXTO? 1 si sí, 0 si no. No uses conocimiento propio; "
    "si una cifra o un dato es distinto, vale 0.\n"
    'Responde solo JSON: {{"razon": "<máximo 12 palabras>", "veredicto": 0 o 1}}\n\n'
    "CONTEXTO:\n{contexto}\n\nAFIRMACIÓN: {afirmacion}"
)
_P_PREGUNTA = (
    "Escribe UNA pregunta que la RESPUESTA conteste exactamente. Indica también si la respuesta es "
    "evasiva o no se compromete (por ejemplo «no lo sé», «no tengo información»).\n"
    'Responde solo JSON: {{"pregunta": "...", "evasiva": true o false}}\n\nRESPUESTA: {respuesta}'
)
# Con «¿El CONTEXTO sirvió para llegar a la RESPUESTA de la PREGUNTA?» el juez de 3B juzgaba el tema de la pregunta
# («no ayuda a determinar si los laboratorios son adecuados») y daba 0 a respuestas copiadas del contexto (28 oct,
# Fase 4). Ahora la instrucción dice qué cuenta como «usado» y trae un ejemplo resuelto, como los demás prompts.
_P_UTILIDAD = (
    "Decide si el CONTEXTO se usó para escribir la RESPUESTA: vale 1 si la RESPUESTA toma del CONTEXTO sus datos "
    "(cifras, IDs, opciones, nombres de preguntas) o se apoya en él; vale 0 si el CONTEXTO no tiene nada de lo que "
    "dice la RESPUESTA. No juzgues si la respuesta es buena ni si el tema de la pregunta es positivo o negativo.\n"
    'Ejemplo: PREGUNTA «¿cuántos trabajan?» RESPUESTA «Trabajan 12 de 40 (30 %) [Fuente 1].» CONTEXTO «Cumplen la '
    'condición 12 de 40 respondentes (30.0 %).» → {{"razon": "la respuesta toma 12 de 40 y 30 % del contexto", '
    '"veredicto": 1}}\n'
    'Responde solo JSON: {{"razon": "<máximo 15 palabras>", "veredicto": 0 o 1}}\n\n'
    "PREGUNTA: {pregunta}\nRESPUESTA: {respuesta}\nCONTEXTO: {contexto}"
)

Juez = Callable[[str], Any]  # async: prompt → dict (JSON del juez) o None


def juez_por_defecto() -> str:
    return settings.RAG_JUEZ_MODELO or settings.OLLAMA_MODEL


async def _juez_ollama(prompt: str, modelo: str | None = None) -> dict[str, Any] | None:
    """Llamada al juez (Ollama, JSON, temperatura 0); None si no responde o no es JSON."""
    from services import ollama_client

    modelo = modelo or juez_por_defecto()
    # Temperatura 0 no bastaba: qwen2.5:3b dio veredictos distintos a la misma entrada (24 oct). Con la semilla
    # fija, la misma respuesta recibe la misma calificación y las corridas se pueden repetir.
    texto, degradado = await ollama_client.generar_no_stream(prompt, modelo, formato="json", opciones={"temperature": 0, "seed": 42})
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


# Cifras que no cuentan: citas [Fuente 2], IDs (R017, p04, KPI-12, INS-0127) y números dentro de ellos.
_NO_CIFRA = re.compile(r"\[fuente\s*\d+[^\]]*\]|\b(?:ins|kpi)-?\d+\b|\b[rpqaei]-?\d{1,4}\b", re.IGNORECASE)
_CIFRA = re.compile(r"\d+(?:[.,]\d+)?")


_MIN_COINCIDENCIA_LITERAL = 0.75


def _palabras(texto: str) -> set[str]:
    from services.dominio import normalizar

    return {w for w in re.findall(r"[a-z]+", normalizar(texto)) if len(w) > 3}


def sustento_literal(afirmacion: str, contextos: list[str]) -> bool:
    """¿La afirmación está casi copiada de una línea del contexto? Todas sus cifras aparecen en el contexto y al menos
    el 75 % de sus palabras con contenido están en una misma línea (sin juez)."""
    if cifras_sin_sustento(afirmacion, contextos):
        return False
    propias = _palabras(afirmacion)
    if len(propias) < 3:
        return False
    lineas = [l for c in contextos for l in c.split("\n") if l.strip()]
    return any(len(propias & _palabras(l)) / len(propias) >= _MIN_COINCIDENCIA_LITERAL for l in lineas)


def cifras_sin_sustento(respuesta: str, contextos: list[str]) -> list[str]:
    """Cifras de la respuesta que no aparecen en el contexto usado (sin juez, determinista)."""
    def cifras(texto: str) -> dict[float, str]:
        return {float(c.replace(",", ".")): c for c in _CIFRA.findall(_NO_CIFRA.sub(" ", texto))}

    en_contexto = set(cifras("\n".join(contextos)))
    return [original for valor, original in cifras(respuesta).items() if valor not in en_contexto]


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
    marcas: list[int] | None = None
    for _ in range(2):  # el juez de 3B a veces devuelve un veredicto de menos: se le pregunta otra vez
        datos = await juez(_P_VEREDICTOS.format(contexto=contexto, afirmaciones=lista))
        try:
            marcas = veredictos_por_numero((datos or {}).get("veredictos") or [], len(afirmaciones))
            break
        except ValueError as exc:
            logger.warning("Fidelidad: %s", exc)
    modo = "lista"
    if marcas is None:  # si insiste, una afirmación por llamada (más lento, pero ya no queda vacía)
        modo = "una_por_una"
        marcas = []
        for a in afirmaciones:
            datos = await juez(_P_VEREDICTO_UNO.format(contexto=contexto, afirmacion=a))
            marcas.append(1 if str((datos or {}).get("veredicto")).strip() in ("1", "True", "true") else 0)
    # Una afirmación casi copiada del contexto (todas sus cifras están y casi todas sus palabras aparecen en una misma
    # línea) está sustentada aunque el juez diga que no: con la respuesta de un hallazgo copiada del resultado,
    # qwen2.5:3b dio 0 de 2 y llama3.2:3b 1 de 2 (28 oct, Fase 4).
    literales = 0
    for i, a in enumerate(afirmaciones):
        if not marcas[i] and sustento_literal(a, contextos):
            marcas[i], literales = 1, literales + 1
    no_sustentadas = [a for a, m in zip(afirmaciones, marcas) if not m]
    return sum(marcas) / len(marcas), {"afirmaciones": len(afirmaciones), "no_sustentadas": no_sustentadas, "modo": modo,
                                       "sustento_literal": literales}


_FILAS_TABLA_JUEZ = 4


def _tablas_recortadas(respuesta: str) -> str:
    """La respuesta con cada tabla en Markdown recortada a su encabezado y primeras filas.

    Con la tabla completa de las 18 respuestas de R001, el juez marcó la respuesta como evasiva y la relevancia
    quedó en 0 (28 oct, Fase 4); con unas filas entiende de qué trata.
    """
    salida: list[str] = []
    filas = 0
    for linea in respuesta.split("\n"):
        if linea.strip().startswith("|"):
            filas += 1
            if filas <= _FILAS_TABLA_JUEZ + 2:  # encabezado, separador y primeras filas
                salida.append(linea)
            elif filas == _FILAS_TABLA_JUEZ + 3:
                salida.append("| … |")
        else:
            filas = 0
            salida.append(linea)
    return "\n".join(salida)


async def relevancia(pregunta: str, respuesta: str, juez: Juez, embeber: Callable[[list[str]], list[list[float]]],
                     *, puede_evadir: bool = True) -> tuple[float | None, dict[str, Any]]:
    """Coseno medio entre la pregunta y 3 preguntas generadas desde la respuesta (0 si es evasiva).

    `puede_evadir=False` en las respuestas calculadas: son datos, no pueden evadir. El juez tomó como evasiva la
    tabla de R001 porque una de sus respuestas era «No lo sé» (28 oct, Fase 4).
    """
    generadas: list[str] = []
    evasivas: list[bool] = []
    breve = _tablas_recortadas(respuesta)
    for _ in range(_ESTRICTEZ):
        datos = await juez(_P_PREGUNTA.format(respuesta=breve))
        if datos and str(datos.get("pregunta") or "").strip():
            generadas.append(str(datos["pregunta"]).strip())
            evasivas.append(bool(datos.get("evasiva")))
    if not generadas:
        return None, {"preguntas_generadas": []}
    vectores = embeber([pregunta, *generadas])
    media = sum(_coseno(vectores[0], v) for v in vectores[1:]) / len(generadas)
    valor = 0.0 if puede_evadir and all(evasivas) else max(0.0, media)
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
                  embeber: Callable[[list[str]], list[list[float]]] | None = None, *,
                  calculada: bool = False) -> dict[str, Any]:
    """Las tres métricas de una respuesta, con su detalle (lo que se guarda en rag_log.metricas).

    `calculada`: la respuesta es el resultado calculado tal cual; la fidelidad es 1 por construcción y no se le
    pregunta al juez.
    """
    from services import vectores

    juez = juez or _juez_ollama
    embeber = embeber or vectores.embed_texts
    salida: dict[str, Any] = {"estado": CALCULADA if calculada else LISTO, "version": VERSION,
                              "detalle": {"cifras_sin_sustento": cifras_sin_sustento(respuesta, contextos)}}
    calculos = [
        ("relevancia", relevancia(pregunta, respuesta, juez, embeber, puede_evadir=not calculada)),
        ("precision_contexto", precision_contexto(pregunta, respuesta, contextos, juez)),
    ]
    if calculada:
        salida["fidelidad"] = 1.0
        salida["motivo"] = "Respuesta calculada sobre los datos y mostrada tal cual: fiel por construcción."
    else:
        calculos.insert(0, ("fidelidad", fidelidad(pregunta, respuesta, contextos, juez)))
    for nombre, calculo in calculos:
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


def por_construccion() -> dict[str, Any]:
    """Métricas iniciales de una respuesta que ES el resultado calculado (sin redacción del modelo): fidelidad 1
    sin preguntarle al juez; la relevancia y la precisión del contexto se calculan después en segundo plano."""
    return {"estado": CALCULANDO, "calculada": True, "fidelidad": 1.0, "version": VERSION,
            "motivo": "Respuesta calculada sobre los datos y mostrada tal cual: fiel por construcción."}


def pendiente(calculada: bool) -> dict[str, Any]:
    """Métricas de una respuesta que se evaluará solo si la persona lo pide (`RAG_METRICAS_BAJO_DEMANDA`).

    En una respuesta calculada la fidelidad ya se sabe (1 por construcción); el resto espera.
    """
    salida: dict[str, Any] = {"estado": PENDIENTE, "calculada": calculada, "version": VERSION}
    if calculada:
        salida["fidelidad"] = 1.0
        salida["motivo"] = "Respuesta calculada sobre los datos y mostrada tal cual: fiel por construcción."
    return salida


def solicitar(fila: RagLog, sesion: Any, fabrica: Callable[[], Any], modelo_juez: str | None = None) -> None:
    """Pide la evaluación de una respuesta: pasa a «calculando» y entra a la cola en segundo plano.

    Con el juez por defecto solo se evalúa una respuesta pendiente (lo que muestra la interfaz). Con otro juez
    (`modelo_juez`), se evalúa si ese juez aún no tiene una evaluación terminada de esa respuesta; las respuestas
    omitidas (rechazos, mensajes fijos) no se evalúan con ningún juez.
    """
    metricas = fila.metricas or {}
    if not modelo_juez or modelo_juez == juez_por_defecto():
        if metricas.get("estado") != PENDIENTE:
            return
        fila.metricas = {**metricas, "estado": CALCULANDO}
        sesion.commit()
        programar(fila.rag_log_id, fabrica)
        return
    if metricas.get("estado") == OMITIDA or not metricas:
        return
    previa = sesion.query(RagMetricaJuez).filter_by(rag_log_id=fila.rag_log_id, modelo_juez=modelo_juez).one_or_none()
    if previa is not None and (previa.metricas or {}).get("estado") in (LISTO, CALCULADA, CALCULANDO):
        return
    if previa is None:
        previa = RagMetricaJuez(rag_log_id=fila.rag_log_id, modelo_juez=modelo_juez)
        sesion.add(previa)
    previa.metricas, previa.version = {"estado": CALCULANDO}, VERSION
    sesion.commit()
    programar(fila.rag_log_id, fabrica, modelo_juez)


# ── Prioridad del chat ─────────────────────────────────────────────────────────
# El juez usa el mismo Ollama que el chat (un modelo, una GPU, una petición a la vez): las métricas de
# la respuesta anterior hacían esperar a la pregunta siguiente (22 oct). Mientras hay una pregunta en
# curso, el trabajador de métricas espera entre llamada y llamada.
_chats_activos = 0
_ESPERA_MAXIMA = 180.0  # segundos: si un contador quedara colgado, las métricas siguen de todos modos


def chat_empieza() -> None:
    global _chats_activos
    _chats_activos += 1


def chat_termina() -> None:
    global _chats_activos
    _chats_activos = max(0, _chats_activos - 1)


async def _esperar_turno() -> None:
    esperado = 0.0
    while _chats_activos > 0 and esperado < _ESPERA_MAXIMA:
        await asyncio.sleep(0.5)
        esperado += 0.5


async def _juez_en_segundo_plano(prompt: str, modelo: str | None = None) -> dict[str, Any] | None:
    await _esperar_turno()
    return await _juez_ollama(prompt, modelo)


def _guardar_por_juez(sesion: Any, rag_log_id: int, modelo_juez: str, metricas: dict[str, Any]) -> None:
    fila = sesion.query(RagMetricaJuez).filter_by(rag_log_id=rag_log_id, modelo_juez=modelo_juez).one_or_none()
    if fila is None:
        fila = RagMetricaJuez(rag_log_id=rag_log_id, modelo_juez=modelo_juez)
        sesion.add(fila)
    fila.metricas, fila.version = metricas, VERSION
    fila.fecha = datetime.now(timezone.utc).replace(tzinfo=None)


async def _evaluar_consulta(rag_log_id: int, fabrica: Callable[[], Any], modelo_juez: str | None = None) -> None:
    """Calcula y guarda las métricas de una consulta (una a la vez: no compite con el chat).

    Se guardan en `rag_metrica_juez` con el juez que las calculó; las del juez por defecto, además, en
    `rag_log.metricas`.
    """
    modelo = modelo_juez or juez_por_defecto()
    por_defecto = modelo == juez_por_defecto()
    global _cerrojo
    _cerrojo = _cerrojo or asyncio.Lock()
    async with _cerrojo:
        sesion = fabrica()
        try:
            fila = sesion.get(RagLog, rag_log_id)
            if fila is None:
                return
            contextos = [c.get("texto", "") for c in fila.contexto_usado or [] if c.get("texto")]
            previas = fila.metricas or {}
            calculada = bool(previas.get("calculada")) or previas.get("estado") == CALCULADA
            try:
                await _esperar_turno()
                metricas = await evaluar(fila.pregunta, fila.respuesta or "", contextos,
                                         juez=lambda prompt: _juez_en_segundo_plano(prompt, modelo), calculada=calculada)
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudieron calcular las métricas de la consulta %s: %s", rag_log_id, exc)
                metricas = {"estado": ERROR, "motivo": str(exc)[:200], "version": VERSION}
            _guardar_por_juez(sesion, rag_log_id, modelo, metricas)
            if por_defecto:
                fila.metricas = {**metricas, "calculada": True} if calculada else metricas
                fila.modelo_juez = modelo
                fila.fecha_metricas = datetime.now(timezone.utc).replace(tzinfo=None)
            sesion.commit()
        finally:
            sesion.close()


def programar(rag_log_id: int, fabrica: Callable[[], Any], modelo_juez: str | None = None) -> None:
    """Agenda la evaluación de una consulta sin bloquear la respuesta del chat."""
    try:
        tarea = asyncio.get_running_loop().create_task(_evaluar_consulta(rag_log_id, fabrica, modelo_juez))
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
        "noSustentadas": [*(((metricas.get("detalle") or {}).get("fidelidad") or {}).get("no_sustentadas") or []),
                          *(f"Cifra sin respaldo en las fuentes: {c}"
                            for c in (metricas.get("detalle") or {}).get("cifras_sin_sustento") or [])],
        "modeloJuez": fila.modelo_juez,
        "fecha": fila.fecha_metricas,
    }


def jueces_de(sesion: Any, rag_log_id: int) -> list[dict[str, Any]]:
    """Las evaluaciones de una respuesta, una por juez (experimento redactor × juez)."""
    filas = sesion.query(RagMetricaJuez).filter_by(rag_log_id=rag_log_id).order_by(RagMetricaJuez.modelo_juez).all()
    return [{"modeloJuez": f.modelo_juez, "estado": (f.metricas or {}).get("estado", LISTO),
             "fidelidad": (f.metricas or {}).get("fidelidad"), "relevancia": (f.metricas or {}).get("relevancia"),
             "precisionContexto": (f.metricas or {}).get("precision_contexto"), "fecha": f.fecha} for f in filas]
