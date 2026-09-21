# survey_intelligence/engine/spss/spss_validator.py
"""
Validador de metadatos SPSS.

SPSS impone restricciones sobre los nombres de variable (<= 64 chars, sin espacios,
inicio alfabético) y sobre el nivel de medición. Este módulo sanea nombres y valida
los campos antes de escribir el .SAV.
"""
from __future__ import annotations

import re

from survey_intelligence.contracts.enums import Measure

_INVALID_CHARS = re.compile(r"[^A-Za-z0-9_]")
_MAX_NAME_LEN = 64


def sanitize_spss_name(name: str, fallback: str = "var") -> str:
    """
    Sanea un nombre para SPSS:
      - reemplaza caracteres inválidos por '_'.
      - garantiza inicio alfabético (prefija 'v_' si empieza por dígito).
      - recorta a 64 chars.
    """
    cleaned = _INVALID_CHARS.sub("_", name).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"v_{cleaned}"
    return cleaned[:_MAX_NAME_LEN]


def is_valid_spss_name(name: str) -> bool:
    if not name or len(name) > _MAX_NAME_LEN:
        return False
    if name[0].isdigit():
        return False
    return _INVALID_CHARS.search(name) is None


def is_valid_measure(measure: Measure | None) -> bool:
    return measure in (Measure.NOMINAL, Measure.ORDINAL, Measure.SCALE)
