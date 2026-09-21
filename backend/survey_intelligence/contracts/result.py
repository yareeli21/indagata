# survey_intelligence/contracts/result.py
"""
Contrato de SALIDA del SIS: SurveyIntelligenceResult (design.md §5.2).

Autoexplicativo: incluye ambos modelos, propuestas ejecutables, oportunidades de
mejora y diagnósticos por etapa. Nunca se lanza excepción al host: los fallos se
reportan como status='failed' con diagnóstico.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enriched import EnrichedSurveyModel
from survey_intelligence.contracts.enums import (
    ProposalType,
    ResultStatus,
    StageStatus,
)
from survey_intelligence.contracts.improvement import ImprovementOpportunity
from survey_intelligence.contracts.interview import InterviewAnalysis
from survey_intelligence.contracts.kpi import KpiInference
from survey_intelligence.contracts.results import ResultsFinding

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class TransformProposal(BaseModel):
    """
    Propuesta ejecutable (patrón propose -> decide -> apply, design.md §7).

    Estructura compatible con EtlPropuesta del host. `valor_propuesto` es un JSON
    string que codifica {transform_id, params} para el apply_engine.
    """
    model_config = _FROZEN

    proposal_id: str
    tipo: ProposalType = ProposalType.TRANSFORMACION
    descripcion: str
    accion_sugerida: str
    justificacion: str
    impacto_esperado: str | None = None
    valor_original: str | None = None
    valor_propuesto: str | None = None


class StageDiagnostic(BaseModel):
    model_config = _FROZEN

    stage: str
    status: StageStatus
    ms: int | None = None
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class Diagnostics(BaseModel):
    model_config = _FROZEN

    stages: list[StageDiagnostic] = Field(default_factory=list)
    llm_calls: int = 0
    warnings: list[str] = Field(default_factory=list)
    degraded: bool = False


class SurveyIntelligenceResult(BaseModel):
    """Resultado completo devuelto por SurveyIntelligenceService.process()."""
    model_config = _FROZEN

    request_id: str
    schema_version: str
    pipeline_version: str
    generated_at: str
    status: ResultStatus

    canonical_survey_model: CanonicalSurveyModel | None = None
    enriched_survey_model: EnrichedSurveyModel | None = None
    proposals: list[TransformProposal] = Field(default_factory=list)
    kpi_inferences: list[KpiInference] = Field(default_factory=list)
    results_findings: list[ResultsFinding] = Field(default_factory=list)
    improvement_opportunities: list[ImprovementOpportunity] = Field(default_factory=list)
    # Solo para instrumentos 'entrevista'; queda None en encuestas/pruebas.
    interview_analysis: InterviewAnalysis | None = None
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
