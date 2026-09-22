# survey_intelligence/contracts/__init__.py
"""Contratos públicos del SIS."""
from __future__ import annotations

from survey_intelligence.contracts.canonical import (
    CanonicalSurveyModel,
    OpenAnswer,
    QuestionItem,
    QuestionOption,
    QuestionResponse,
    QuestionScale,
    RespondentProfile,
    SourceColumn,
)
from survey_intelligence.contracts.codebook import CodebookEntry, CodebookModel
from survey_intelligence.contracts.enriched import EnrichedSurveyModel
from survey_intelligence.contracts.improvement import ImprovementOpportunity
from survey_intelligence.contracts.interview import (
    DialogueTurn,
    Finding,
    InterviewAnalysis,
    Participant,
    ParticipantSummary,
    Pattern,
    Quote,
    Theme,
)
from survey_intelligence.contracts.kpi import KpiInference
from survey_intelligence.contracts.results import ResultsFinding
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    IngestionOptions,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.contracts.result import (
    Diagnostics,
    StageDiagnostic,
    SurveyIntelligenceResult,
    TransformProposal,
)
from survey_intelligence.contracts.spss import SpssVariableMetadata

__all__ = [
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
    "KpiInference",
    "ResultsFinding",
    "InterviewAnalysis",
    "Participant",
    "DialogueTurn",
    "Theme",
    "Finding",
    "Pattern",
    "Quote",
    "ParticipantSummary",
    # Rediseño v2 del canónico de encuestas (aditivo)
    "QuestionOption",
    "QuestionItem",
    "QuestionScale",
    "SourceColumn",
    "QuestionResponse",
    "RespondentProfile",
    "OpenAnswer",
]
