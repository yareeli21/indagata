# survey_intelligence/engine/parsing/robust_json.py
"""
Parser JSON robusto para respuestas de LLM.

Generalizado desde la lógica probada de _parsear_respuesta_json del host, pero sin
las claves específicas de EtlPropuesta: aquí solo se extrae y limpia el JSON; la
validación de esquema la hace cada etapa con Pydantic.

Los LLM devuelven JSON sucio: con texto alrededor, en bloque markdown, con comas
finales, o con ';' en vez de ','. Estas estrategias lo recuperan en orden.
"""
from __future__ import annotations

import json
import re
from typing import Any


class JsonParseError(Exception):
    """No se pudo extraer JSON válido de la respuesta del LLM."""


def _clean_common_errors(text: str) -> str:
    """Corrige errores frecuentes de LLM en el JSON."""
    # '0;' -> '0,'  |  'null;' -> 'null,'  |  '";' -> '",'
    text = re.sub(r"(\d+)\s*;", r"\1,", text)
    text = re.sub(r"(null|true|false)\s*;", r"\1,", text)
    text = re.sub(r'"\s*;', r'",', text)
    # Comas finales antes de } o ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _try_direct(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _try_markdown(text: str) -> Any | None:
    if "```" not in text:
        return None
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _try_bracketed(text: str, open_ch: str, close_ch: str) -> Any | None:
    start = text.find(open_ch)
    end = text.rfind(close_ch)
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = _clean_common_errors(text[start:end + 1])
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def parse_json(raw: str) -> Any:
    """
    Extrae un objeto/array JSON de la respuesta cruda del LLM.

    Estrategias en orden:
      1. parseo directo,
      2. bloque markdown ```json ... ```,
      3. primer '[' .. último ']' (array raíz),
      4. primer '{' .. último '}' (objeto raíz).

    Raises:
        JsonParseError: si ninguna estrategia recupera JSON válido.
    """
    text = (raw or "").strip()
    if not text:
        raise JsonParseError("Respuesta del LLM vacía.")

    for strategy in (
        lambda: _try_direct(text),
        lambda: _try_markdown(text),
        lambda: _try_bracketed(text, "[", "]"),
        lambda: _try_bracketed(text, "{", "}"),
    ):
        result = strategy()
        if result is not None:
            return result

    raise JsonParseError(
        f"No se pudo extraer JSON válido (primeros 300 chars): {text[:300]}"
    )


def parse_json_object(raw: str) -> dict:
    """Como parse_json pero exige un objeto (dict). Envuelve listas de 1 elemento."""
    data = parse_json(raw)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        return data[0]
    raise JsonParseError(f"Se esperaba un objeto JSON, se obtuvo {type(data).__name__}.")


def parse_json_array(raw: str) -> list:
    """Como parse_json pero exige un array (list). Envuelve un objeto suelto."""
    data = parse_json(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise JsonParseError(f"Se esperaba un array JSON, se obtuvo {type(data).__name__}.")
