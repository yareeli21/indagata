# survey_intelligence/__init__.py
"""
Survey Intelligence Service (SIS).

Componente de dominio reutilizable y desacoplado. Superficie pública mínima:
solo el facade (SurveyIntelligenceService) y los contratos de entrada/salida.

El host NO debe importar nada fuera de lo exportado aquí.

Ejemplo de uso:
    from survey_intelligence import (
        SurveyIntelligenceService,
        SurveyIngestionRequest,
        SurveyIntelligenceResult,
    )
"""
from __future__ import annotations

from survey_intelligence.contracts import (
    CanonicalSurveyModel,
    CodebookEntry,
    CodebookModel,
    Diagnostics,
    DublinCoreMetadata,
    EnrichedSurveyModel,
    ImprovementOpportunity,
    IngestionOptions,
    SpssVariableMetadata,
    StageDiagnostic,
    SurveyFile,
    SurveyIngestionRequest,
    SurveyIntelligenceResult,
    TransformProposal,
)
from survey_intelligence.facade import SurveyIntelligenceService
from survey_intelligence.versioning import PIPELINE_VERSION, SCHEMA_VERSION

__all__ = [
    "SurveyIntelligenceService",
    "SCHEMA_VERSION",
    "PIPELINE_VERSION",
    "SurveyIngestionRequest",
    "SurveyFile",
    "CodebookEntry",
    "CodebookModel",
    "DublinCoreMetadata",
    "IngestionOptions",
    "SurveyIntelligenceResult",
    "TransformProposal",
    "Diagnostics",
    "StageDiagnostic",
    "CanonicalSurveyModel",
    "EnrichedSurveyModel",
    "SpssVariableMetadata",
    "ImprovementOpportunity",
]
