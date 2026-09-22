# survey_intelligence/engine/heuristics/__init__.py
"""Heurísticas determinísticas: detección de plataforma, columnas, reglas de calidad."""
from __future__ import annotations

from survey_intelligence.engine.heuristics.column_proposals import (
    build_column_proposals,
)
from survey_intelligence.engine.heuristics.context_sufficiency import (
    SufficiencyVerdict,
    evaluate_variable,
)
from survey_intelligence.engine.heuristics.platform_columns import (
    PlatformDetection,
    detect_platform,
)

__all__ = [
    "PlatformDetection",
    "detect_platform",
    "SufficiencyVerdict",
    "evaluate_variable",
    "build_column_proposals",
]
