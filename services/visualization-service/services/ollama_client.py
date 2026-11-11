"""Cliente HTTP a Ollama para generación de texto (diseño §4.9, §4.10).

`generar(prompt, modelo, stream)` llama a `settings.OLLAMA_HOST + /api/generate`
con `{model, prompt, stream}` y `httpx.Timeout(connect=5, read=120)`.

- `stream=True`: async generator que produce los trozos de texto (`response`) a
  medida que Ollama emite su NDJSON (un JSON por línea con `response`/`done`).
- `stream=False`: devuelve el texto completo (`str`).

Degradación grácil (§4.10): ante `httpx.ConnectError`/timeout (o error del
modelo) NO lanza; produce/retorna un mensaje en español explicando que el modelo
local no está disponible. El flag de degradación se decide en el router a partir
de ese mensaje; aquí `generar_no_stream` devuelve `(texto, degradado)`.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)

# Opciones de rendimiento para GPUs con poca VRAM (p. ej. GTX 1650, 4 GiB).
# - keep_alive=-1: mantiene el modelo cargado en VRAM mientras viva el contenedor,
#   eliminando el recargado (~20 s) que Ollama hace tras OLLAMA_KEEP_ALIVE (5 min).
#   Va como NÚMERO: Ollama rechaza el texto "-1" con 400 ("missing unit in duration").
# - num_ctx=4096: cabe el prompt del RAG con hasta 8 fuentes (~1.5 k tokens) y
#   sobra espacio para la respuesta. Con 2048 el prompt + la respuesta rebasaban
#   la ventana y Ollama recortaba el inicio del prompt, que es la instrucción de
#   responder solo con el contexto.
# - temperature: la de la redacción, `RAG_TEMPERATURA_REDACCION` (0.2 por defecto: respuestas apegadas al
#   contexto). La interpretación, los clasificadores y el juez la sobrescriben con 0 en `opciones`.
_KEEP_ALIVE = -1
_NUM_CTX = 4096

# Freno a las respuestas que se repiten (8 nov: «¿Qué es la escala RAU?» se quedó repitiendo el mismo párrafo
# hasta que la usuaria lo detuvo; 35 s de generación contra 5–15 s de una respuesta normal). La penalización de
# repetición de Ollama solo mira los últimos 64 tokens y no frena un párrafo entero repetido. Solo en la
# redacción (texto libre): la interpretación, los clasificadores y el juez piden JSON y no se tocan.
# - num_predict: tope de tokens; la respuesta más larga registrada mide ~1 500 caracteres (~400 tokens).
# - _VENTANA_REPETICION: si los últimos N caracteres ya se habían escrito, el modelo está copiándose: se corta
#   donde empezó la copia. En streaming se retienen esos N caracteres para no mostrar la repetición.
_MAX_TOKENS_REDACCION = 1024
_VENTANA_REPETICION = 200


def corte_repeticion(texto: str, desde: int = 0) -> int | None:
    """Posición donde el texto empieza a repetir un tramo largo que ya había escrito; None si no se repite.

    Revisa cada final de texto a partir de `desde`: si sus últimos `_VENTANA_REPETICION` caracteres
    aparecen antes, retrocede mientras la copia coincida con el original para hallar dónde empezó.
    """
    ventana = _VENTANA_REPETICION
    for fin in range(max(2 * ventana, desde), len(texto) + 1):
        cola = texto[fin - ventana:fin]
        if not cola.strip():
            continue
        previo = texto.find(cola, 0, fin - 1)
        if previo == -1 or previo >= fin - ventana:
            continue
        i, j = previo, fin - ventana
        while i > 0 and texto[i - 1] == texto[j - 1]:
            i, j = i - 1, j - 1
        return j
    return None


# Frase completa repetida: el bucle del 8 nov alternaba frases casi iguales («La Escala RAU es un instrumento…»,
# «La Escala RAU es una encuesta…») y la ventana de 200 caracteres tardaba varias líneas en cortarlo. Una frase de
# 50+ caracteres que ya se había escrito (sin contar citas ni espacios) corta la respuesta donde empieza.
_MIN_FRASE_REPETIDA = 50
_RE_FRASE = re.compile(r"[^.!?\n]+(?:[.!?]+|\n|$)")
_RE_CITA_FRASE = re.compile(r"[\[(]\s*Fuentes?\s+[\d\s,y]+[\])]", re.IGNORECASE)


def corte_frase_repetida(texto: str) -> int | None:
    """Posición donde empieza una frase completa que ya estaba antes en el texto; None si no hay."""
    vistas: set[str] = set()
    for m in _RE_FRASE.finditer(texto):
        if not m.group(0).rstrip().endswith((".", "!", "?")) and m.end() == len(texto):
            break  # la última frase aún no termina
        frase = " ".join(_RE_CITA_FRASE.sub(" ", m.group(0)).lower().split()).strip(" .!?")
        if len(frase) < _MIN_FRASE_REPETIDA:
            continue
        if frase in vistas:
            return m.start() + (len(m.group(0)) - len(m.group(0).lstrip()))
        vistas.add(frase)
    return None


def sin_repeticion(texto: str) -> str:
    """El texto hasta antes de que empezara a copiarse a sí mismo."""
    candidatos = [c for c in (corte_repeticion(texto), corte_frase_repetida(texto)) if c is not None]
    corte = min(candidatos) if candidatos else None
    if corte is None:
        return texto
    logger.warning("Redacción repetida: se corta en %d de %d caracteres.", corte, len(texto))
    return texto[:corte].rstrip()


def _payload(
    modelo: str,
    prompt: str,
    *,
    stream: bool,
    sistema: str | None = None,
    formato: str | dict | None = None,
    opciones: dict | None = None,
) -> dict:
    """Arma el cuerpo de /api/generate con las opciones de rendimiento.

    `opciones` se suma a las de rendimiento (p. ej. temperature 0 para el
    clasificador de dominio) y `formato="json"` obliga a Ollama a devolver JSON; con un JSON Schema
    (dict), Ollama restringe la salida a ese esquema (plan de la interpretación).
    """
    cuerpo = {
        "model": modelo,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": _KEEP_ALIVE,
        "options": {
            "num_ctx": _NUM_CTX,
            "temperature": settings.RAG_TEMPERATURA_REDACCION,
            # Solo la redacción (texto libre) lleva tope de tokens; las salidas JSON no se tocan.
            **({} if formato else {"num_predict": _MAX_TOKENS_REDACCION}),
            **(opciones or {}),
        },
    }
    if sistema:
        cuerpo["system"] = sistema
    if formato:
        cuerpo["format"] = formato
    return cuerpo

MENSAJE_DEGRADADO = (
    "No se pudo contactar al modelo local (Ollama). Se muestran las fuentes "
    "recuperadas de tus instrumentos; reintenta cuando el modelo esté disponible."
)


def _url() -> str:
    return f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate"


async def generar_stream(prompt: str, modelo: str, sistema: str | None = None) -> AsyncIterator[str]:
    """Genera texto en streaming; produce trozos de `response` (§4.9).

    Ante error de conexión/timeout produce un único trozo con el mensaje de
    degradación y termina (no lanza).

    Retiene los últimos `_VENTANA_REPETICION` caracteres antes de emitirlos: si el modelo empieza a
    copiarse a sí mismo, se deja de generar y la copia no llega a la pantalla.
    """
    payload = _payload(modelo, prompt, stream=True, sistema=sistema)
    generado, enviados, revisado = "", 0, 0
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cliente:
            async with cliente.stream("POST", _url(), json=payload) as resp:
                if resp.status_code != 200:
                    await resp.aread()
                    logger.warning("Ollama respondió %s", resp.status_code)
                    yield MENSAJE_DEGRADADO
                    return
                async for linea in resp.aiter_lines():
                    if not linea.strip():
                        continue
                    try:
                        dato = json.loads(linea)
                    except json.JSONDecodeError:
                        continue
                    trozo = dato.get("response")
                    if trozo:
                        generado += trozo
                        cortes = [c for c in (corte_repeticion(generado, desde=revisado),
                                              corte_frase_repetida(generado)) if c is not None]
                        corte = min(cortes) if cortes else None
                        revisado = len(generado) + 1
                        if corte is not None:
                            logger.warning("Redacción repetida (stream): se corta en %d caracteres.", corte)
                            generado = generado[:max(corte, enviados)].rstrip()
                            break  # al salir del `with` se cierra la conexión y Ollama deja de generar
                        hasta = len(generado) - _VENTANA_REPETICION
                        if hasta > enviados:
                            yield generado[enviados:hasta]
                            enviados = hasta
                    if dato.get("done"):
                        break
        if len(generado) > enviados:
            yield generado[enviados:]
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Ollama no disponible (stream): %s", exc)
        if len(generado) > enviados:
            yield generado[enviados:]
        yield MENSAJE_DEGRADADO


async def generar_no_stream(
    prompt: str,
    modelo: str,
    sistema: str | None = None,
    *,
    formato: str | dict | None = None,
    opciones: dict | None = None,
) -> tuple[str, bool]:
    """Genera texto completo. Devuelve `(texto, degradado)` (§4.10).

    `degradado=True` si Ollama no estuvo disponible o devolvió error.
    """
    payload = _payload(modelo, prompt, stream=False, sistema=sistema, formato=formato, opciones=opciones)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cliente:
            resp = await cliente.post(_url(), json=payload)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Ollama no disponible: %s", exc)
        return MENSAJE_DEGRADADO, True

    if resp.status_code != 200:
        logger.warning("Ollama respondió %s: %s", resp.status_code, resp.text[:200])
        return MENSAJE_DEGRADADO, True

    try:
        dato = resp.json()
    except ValueError:
        return MENSAJE_DEGRADADO, True

    texto = dato.get("response")
    if not isinstance(texto, str) or not texto:
        return MENSAJE_DEGRADADO, True
    return (texto if formato else sin_repeticion(texto)), False
