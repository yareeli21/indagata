# survey_intelligence/engine/heuristics/platform_columns.py
"""
Registro de firmas de columnas administrativas por plataforma (extensible).

La detección NO está hardcodeada a una plataforma: una columna es administrativa
porque su encabezado coincide con un patrón administrativo conocido (IDs, fechas,
idioma, semilla, correo, nombre, progreso) Y no tiene forma de pregunta. Aunque la
plataforma no se reconozca, las columnas administrativas se detectan por forma.

Añadir una plataforma = añadir una entrada a _PLATFORM_SIGNATURES.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Firmas por plataforma ────────────────────────────────────────────────────
# Cada firma es un conjunto de encabezados administrativos (en minúsculas) que,
# si aparecen, identifican la plataforma y marcan esas columnas como metadata.

_PLATFORM_SIGNATURES: dict[str, set[str]] = {
    "limesurvey": {
        "response id", "date submitted", "last page", "start language",
        "seed", "date started", "date last action",
    },
    "microsoft_forms": {
        "id", "hora de inicio", "hora de finalización", "correo electrónico",
        "nombre",
        # equivalentes en inglés
        "start time", "completion time", "email", "name",
    },
    "google_forms": {
        "marca temporal", "timestamp",
        "dirección de correo electrónico", "email address",
    },
}

# ── Detección genérica por forma (para plataformas desconocidas) ─────────────
# Patrones de encabezado que son administrativos por naturaleza, sin pregunta.
_GENERIC_ADMIN_PATTERNS = [
    re.compile(r"^\s*id\s*$", re.IGNORECASE),
    re.compile(r"response\s*id", re.IGNORECASE),
    re.compile(r"\b(marca temporal|timestamp)\b", re.IGNORECASE),
    re.compile(r"\b(seed|semilla)\b", re.IGNORECASE),
    re.compile(r"\b(start|end|date|hora|time|fecha)\b.*\b(start|end|action|inicio|finaliza|submitted|started)\b", re.IGNORECASE),
    re.compile(r"\b(last page|última página)\b", re.IGNORECASE),
    re.compile(r"\b(start language|idioma)\b", re.IGNORECASE),
    re.compile(r"\b(correo|email|e-mail)\b", re.IGNORECASE),
    re.compile(r"^\s*(nombre|name)\s*$", re.IGNORECASE),
]

# Señales de que un encabezado ES una pregunta (evita falsos positivos).
_QUESTION_SIGNALS = ("?", "¿", "[", "indica", "evalúa", "evalua", "selecciona", "ordena")


@dataclass(frozen=True)
class PlatformDetection:
    """Resultado de la detección de plataforma sobre un conjunto de encabezados."""
    platform_guess: str | None
    admin_headers: set[str]  # encabezados (originales) clasificados como administrativos


def _looks_like_question(header: str) -> bool:
    low = header.lower()
    return any(sig in low for sig in _QUESTION_SIGNALS)


def _is_generic_admin(header: str) -> bool:
    if _looks_like_question(header):
        return False
    return any(p.search(header) for p in _GENERIC_ADMIN_PATTERNS)


def detect_platform(headers: list[str]) -> PlatformDetection:
    """
    Detecta la plataforma y el conjunto de columnas administrativas.

    Estrategia:
      1. Compara los encabezados (en minúsculas) con cada firma de plataforma.
         Gana la plataforma con más coincidencias (y al menos 2).
      2. Marca como administrativas las columnas que están en la firma ganadora.
      3. Añade cualquier columna que sea administrativa por forma genérica.

    Devuelve platform_guess=None si ninguna firma coincide suficientemente, pero
    aún así detecta columnas administrativas por forma.
    """
    lower_map = {h.lower(): h for h in headers}
    lower_set = set(lower_map.keys())

    best_platform: str | None = None
    best_hits: set[str] = set()
    for platform, signature in _PLATFORM_SIGNATURES.items():
        hits = lower_set.intersection(signature)
        if len(hits) > len(best_hits):
            best_hits = hits
            best_platform = platform

    # Requiere al menos 2 coincidencias para nombrar la plataforma, salvo Google
    # Forms cuya firma mínima puede ser una sola columna ('marca temporal').
    platform_guess: str | None = None
    admin_headers: set[str] = set()
    if best_platform is not None:
        min_hits = 1 if best_platform == "google_forms" else 2
        if len(best_hits) >= min_hits:
            platform_guess = best_platform
            admin_headers = {lower_map[h] for h in best_hits}

    # Detección genérica por forma (siempre se aplica).
    for header in headers:
        if _is_generic_admin(header):
            admin_headers.add(header)

    return PlatformDetection(platform_guess=platform_guess, admin_headers=admin_headers)
