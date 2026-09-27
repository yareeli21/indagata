# survey_intelligence/pipeline/stages/s9_enriched_assembler.py
"""
Etapa S9 — Ensamblado del Enriched Survey Model.

Combina los resultados de S6 (auditoría) y S7 (enriquecimiento por variable) en el
EnrichedSurveyModel final. No añade lógica nueva: solo estructura.
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enriched import (
    EnrichedSurveyModel,
    SurveyLevelFindings,
)
from survey_intelligence.pipeline.stages.s6_methodology_audit import AuditResult
from survey_intelligence.pipeline.stages.s7_semantic_enrichment import EnrichmentResult


def assemble_enriched(
    canonical: CanonicalSurveyModel,
    audit: AuditResult,
    enrichment: EnrichmentResult,
) -> EnrichedSurveyModel:
    """Ensambla el EnrichedSurveyModel a partir de S6 y S7."""
    findings: SurveyLevelFindings = audit.findings
    return EnrichedSurveyModel(
        based_on_canonical_id=canonical.canonical_id,
        survey_summary=enrichment.survey_summary,
        variables_enriched=enrichment.variables,
        survey_level_findings=findings,
    )
