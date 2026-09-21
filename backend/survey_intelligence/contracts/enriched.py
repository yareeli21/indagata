# survey_intelligence/contracts/enriched.py
"""
Enriched Survey Model (design.md §4.2).

Resultado semántico + metadatos SPSS. Tiene DOS caras:
  - cara semántica (para RAG/embeddings): constructo, rol, suficiencia, chunking.
  - cara SPSS (para .SAV): SpssVariableMetadata.

REGLA DE ORO: este modelo NO contiene métricas, conteos ni datos administrativos
(esos viven solo en el Canonical). Aquí solo va contenido que enriquece el campo
semántico + el diccionario SPSS.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.enums import (
    EnrichmentSuggestionType,
    InterpretabilityStatus,
    Severity,
    SufficiencyLevel,
)
from survey_intelligence.contracts.spss import SpssVariableMetadata

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SurveySummary(BaseModel):
    model_config = _FROZEN

    purpose_inferred: str | None = None
    confidence: float | None = None
    target_population_inferred: str | None = None
    provenance: str | None = None


class ChunkingHint(BaseModel):
    model_config = _FROZEN

    chunk_group: str
    embeddable_text: str


class EnrichmentSuggestion(BaseModel):
    model_config = _FROZEN

    type: EnrichmentSuggestionType
    proposed_item: str
    rationale: str


class AnalyticalSufficiency(BaseModel):
    """Juicio del poder explicativo de una pregunta interpretable (design.md §8)."""
    model_config = _FROZEN

    level: SufficiencyLevel
    reason: str
    what_it_could_reveal: str | None = None
    enrichment_suggestion: EnrichmentSuggestion | None = None


class VariableIssue(BaseModel):
    model_config = _FROZEN

    type: str
    severity: Severity
    detail: str
    recommendation: str | None = None


class SemanticEnrichment(BaseModel):
    """Cara semántica de una variable interpretable."""
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    # 'construct' choca con un atributo interno de Pydantic BaseModel; se declara
    # como 'construct_' con alias para conservar la clave "construct" en el JSON.
    construct_: str | None = Field(default=None, alias="construct")
    semantic_role: str | None = None
    semantic_tags: list[str] = Field(default_factory=list)
    chunking_hint: ChunkingHint | None = None
    evidence: list[str] = Field(default_factory=list)
    analytical_sufficiency: AnalyticalSufficiency | None = None
    issues: list[VariableIssue] = Field(default_factory=list)


class EnrichedVariable(BaseModel):
    """
    Variable enriquecida. Si interpretability_status == INSUFFICIENT_CONTEXT,
    semantic_enrichment queda vacío y se rellenan los campos de explicación.
    """
    model_config = _FROZEN

    variable_id: str
    interpretability_status: InterpretabilityStatus
    spss_metadata: SpssVariableMetadata | None = None
    semantic_enrichment: SemanticEnrichment | None = None

    # Campos exigidos cuando el estado es INSUFFICIENT_CONTEXT (restricción crítica).
    missing_information: list[str] = Field(default_factory=list)
    why_not_interpretable: str | None = None
    required_to_interpret: list[str] = Field(default_factory=list)


class WordingBiasFinding(BaseModel):
    model_config = _FROZEN

    question_id: str
    detail: str


class InconsistentScaleFinding(BaseModel):
    model_config = _FROZEN

    group: list[str]
    detail: str


class RedundantVariablesFinding(BaseModel):
    model_config = _FROZEN

    group: list[str]
    detail: str


class DroppableColumnsFinding(BaseModel):
    model_config = _FROZEN

    variable_ids: list[str]
    reason: str


class SurveyLevelFindings(BaseModel):
    """Hallazgos a nivel de instrumento (design.md §4.2). Puramente semánticos."""
    model_config = _FROZEN

    ambiguous_questions: list[str] = Field(default_factory=list)
    questions_without_context: list[str] = Field(default_factory=list)
    too_short_questions: list[str] = Field(default_factory=list)
    too_long_questions: list[str] = Field(default_factory=list)
    double_barreled: list[str] = Field(default_factory=list)
    wording_bias_suspected: list[WordingBiasFinding] = Field(default_factory=list)
    inconsistent_scales: list[InconsistentScaleFinding] = Field(default_factory=list)
    redundant_variables: list[RedundantVariablesFinding] = Field(default_factory=list)
    low_analytical_value: list[str] = Field(default_factory=list)
    droppable_columns: list[DroppableColumnsFinding] = Field(default_factory=list)
    missing_metadata: list[str] = Field(default_factory=list)
    methodology_deficiencies: list[str] = Field(default_factory=list)
    analysis_risks: list[str] = Field(default_factory=list)
    enrichment_opportunities: list[str] = Field(default_factory=list)


class EnrichedSurveyModel(BaseModel):
    model_config = _FROZEN

    based_on_canonical_id: str
    survey_summary: SurveySummary | None = None
    variables_enriched: list[EnrichedVariable] = Field(default_factory=list)
    survey_level_findings: SurveyLevelFindings = Field(default_factory=SurveyLevelFindings)
