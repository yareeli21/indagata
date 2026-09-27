# survey_intelligence/engine/spss/__init__.py
"""Mapeo determinístico a metadatos SPSS y su validación."""
from __future__ import annotations

from survey_intelligence.engine.spss.spss_mapper import (
    build_spss_dictionary,
    map_variable,
)
from survey_intelligence.engine.spss.spss_validator import (
    is_valid_measure,
    is_valid_spss_name,
    sanitize_spss_name,
)

__all__ = [
    "build_spss_dictionary",
    "map_variable",
    "sanitize_spss_name",
    "is_valid_spss_name",
    "is_valid_measure",
]
