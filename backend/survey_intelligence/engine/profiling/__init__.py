# survey_intelligence/engine/profiling/__init__.py
"""Profiling determinístico: parsing de matrices, normalización, escalas, estadística."""
from __future__ import annotations

from survey_intelligence.engine.profiling.edit_distance import levenshtein
from survey_intelligence.engine.profiling.matrix_parser import MatrixParse, parse_matrix
from survey_intelligence.engine.profiling.name_normalizer import (
    normalize_name,
    unique_names,
)
from survey_intelligence.engine.profiling.scale_detector import detect_scale
from survey_intelligence.engine.profiling.stats import (
    infer_data_type,
    split_multi_select,
    value_distribution,
)

__all__ = [
    "MatrixParse", "parse_matrix",
    "normalize_name", "unique_names",
    "levenshtein",
    "detect_scale",
    "infer_data_type", "value_distribution", "split_multi_select",
]
