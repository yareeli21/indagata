# survey_intelligence/pipeline/stages/s4_context_sufficiency.py
"""
Etapa S4 — Context Sufficiency (determinística, previa al LLM).

Aplica la evaluación de suficiencia de contexto a cada variable del Canonical y
devuelve el mapa de veredictos. Es el paso 1 de la restricción crítica:
marca los candidatos a INSUFFICIENT_CONTEXT ANTES de que intervenga el LLM.

Los veredictos se usan luego en:
  - S5 (RAG): intenta resolver los insuficientes con fuentes documentales.
  - S7 (LLM): respeta el veredicto; el validador degrada cualquier invención.
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.engine.heuristics.context_sufficiency import (
    SufficiencyVerdict,
    evaluate_variable,
)


def assess_context(canonical: CanonicalSurveyModel) -> dict[str, SufficiencyVerdict]:
    """
    Evalúa la suficiencia de contexto de todas las variables.

    Returns:
        dict variable_id -> SufficiencyVerdict.
    """
    return {var.variable_id: evaluate_variable(var) for var in canonical.variables}


def insufficient_variable_ids(
    verdicts: dict[str, SufficiencyVerdict]
) -> list[str]:
    """IDs de variables marcadas como no interpretables (candidatas a resolver por RAG)."""
    return [vid for vid, v in verdicts.items() if not v.is_interpretable]
