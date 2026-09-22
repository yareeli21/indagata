# survey_intelligence/engine/profiling/name_normalizer.py
"""
Normalizador de nombres de variable.

Convierte un texto (encabezado o ítem de matriz) en un nombre corto snake_case,
sin acentos ni signos, apto como base para nombres de variable y para SPSS
(que exige <= 64 chars, sin espacios). Garantiza unicidad dentro de un lote.
"""
from __future__ import annotations

import re
import unicodedata

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_MULTI_US = re.compile(r"_+")

# Palabras vacías frecuentes en español que no aportan al nombre corto.
_STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "y", "o", "que", "en", "a",
    "con", "por", "para", "del", "al", "es", "tu", "tus", "mi", "su", "sus",
    "lo", "se", "te", "me", "the", "of", "to", "in", "on",
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_name(text: str, max_len: int = 40, max_words: int = 6) -> str:
    """
    Deriva un nombre snake_case de un texto libre.

    - Quita acentos y signos.
    - Elimina stopwords comunes (conservando el orden del resto).
    - Une con '_' hasta max_words y recorta a max_len.
    - Si queda vacío, devuelve 'var'.
    """
    ascii_text = _strip_accents(text).lower()
    ascii_text = _NON_WORD.sub(" ", ascii_text)
    tokens = [t for t in ascii_text.split() if t]
    meaningful = [t for t in tokens if t not in _STOPWORDS] or tokens
    name = "_".join(meaningful[:max_words])
    name = _MULTI_US.sub("_", name).strip("_")
    name = name[:max_len].strip("_")
    return name or "var"


def unique_names(base_names: list[str]) -> list[str]:
    """
    Garantiza unicidad añadiendo sufijos _2, _3... a las colisiones,
    preservando el orden de entrada.
    """
    seen: dict[str, int] = {}
    result: list[str] = []
    for name in base_names:
        if name not in seen:
            seen[name] = 1
            result.append(name)
        else:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
    return result
