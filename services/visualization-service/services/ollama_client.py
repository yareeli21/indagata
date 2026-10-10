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
from collections.abc import AsyncIterator

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)

# Opciones de rendimiento para GPUs con poca VRAM (p. ej. GTX 1650, 4 GiB).
# - keep_alive=-1: mantiene el modelo cargado en VRAM mientras viva el contenedor,
#   eliminando el recargado (~20 s) que Ollama hace tras OLLAMA_KEEP_ALIVE (5 min).
# - num_ctx=2048: ventana de contexto suficiente para el prompt del RAG (hasta ~5
#   fuentes + pregunta); reduce el KV-cache y deja más VRAM para los pesos, evitando
#   el offload parcial a CPU que ralentiza la generación.
_KEEP_ALIVE = "-1"
_OPTIONS = {"num_ctx": 2048}


def _payload(modelo: str, prompt: str, *, stream: bool) -> dict:
    """Arma el cuerpo de /api/generate con las opciones de rendimiento."""
    return {
        "model": modelo,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": _KEEP_ALIVE,
        "options": _OPTIONS,
    }

MENSAJE_DEGRADADO = (
    "No se pudo contactar al modelo local (Ollama). Se muestran las fuentes "
    "recuperadas de tus instrumentos; reintenta cuando el modelo esté disponible."
)


def _url() -> str:
    return f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate"


async def generar_stream(prompt: str, modelo: str) -> AsyncIterator[str]:
    """Genera texto en streaming; produce trozos de `response` (§4.9).

    Ante error de conexión/timeout produce un único trozo con el mensaje de
    degradación y termina (no lanza).
    """
    payload = _payload(modelo, prompt, stream=True)
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
                        yield trozo
                    if dato.get("done"):
                        break
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Ollama no disponible (stream): %s", exc)
        yield MENSAJE_DEGRADADO


async def generar_no_stream(prompt: str, modelo: str) -> tuple[str, bool]:
    """Genera texto completo. Devuelve `(texto, degradado)` (§4.10).

    `degradado=True` si Ollama no estuvo disponible o devolvió error.
    """
    payload = _payload(modelo, prompt, stream=False)
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
    return texto, False
