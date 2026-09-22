# survey_intelligence/engine/prompts/__init__.py
"""Construcción de prompts para las etapas de LLM (S6, S7)."""
from __future__ import annotations

from survey_intelligence.engine.prompts.audit_prompt import build_audit_prompt
from survey_intelligence.engine.prompts.enrichment_prompt import build_enrichment_prompt
from survey_intelligence.engine.prompts.kpi_prompt import build_kpi_prompt
from survey_intelligence.engine.prompts.results_prompt import build_results_prompt

__all__ = [
    "build_audit_prompt", "build_enrichment_prompt",
    "build_kpi_prompt", "build_results_prompt",
]
