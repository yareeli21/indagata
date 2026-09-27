# survey_intelligence/tests/test_document_path.py
"""
Tests de la vía documento (Tarea 19): entrevistas / pruebas estandarizadas.

Verifica que el SIS procesa texto narrativo produciendo el mismo modelo de salida
(Canonical + Enriched) sin escalas, reusando S4..S9.

Ejecutar:
    python -m survey_intelligence.tests.test_document_path
"""
from __future__ import annotations

import json

from survey_intelligence import SurveyIngestionRequest, SurveyIntelligenceService
from survey_intelligence.contracts.enums import ColumnClass, ResultStatus
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    IngestionOptions,
    SurveyFile,
)
from survey_intelligence.pipeline.stages.s2_document_builder import build_document_canonical
from survey_intelligence.tests.fakes import FixedClock, ScriptedLLM, SequentialIds

_TRANSCRIPT = """
Entrevista sobre experiencia académica

1. ¿Cómo describirías tu experiencia en la universidad?
Ha sido intensa pero muy enriquecedora, con altibajos.

2. ¿Qué factores han influido más en tu rendimiento?
Principalmente la carga de trabajo y el apoyo de mis profesores.

3. ¿Qué mejorarías de la institución?
Más flexibilidad de horarios y mejores espacios de estudio.
"""


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="Entrevista", dc_creator="c", dc_subject=["experiencia"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="entrevista",
        dc_format="pdf", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def test_document_builder_segments() -> None:
    """El builder documental segmenta el texto en variables free_text."""
    canonical = build_document_canonical(_TRANSCRIPT, "entrevista.pdf", "entrevista")
    assert len(canonical.variables) >= 3
    assert all(v.column_class == ColumnClass.FREE_TEXT for v in canonical.variables)
    assert canonical.source.platform_guess.startswith("documento:")


def test_document_path_end_to_end() -> None:
    """La fachada procesa una entrevista por la vía documento."""
    audit = json.dumps({"ambiguous_questions": [], "double_barreled": [],
                        "wording_bias_suspected": [], "methodology_deficiencies": [],
                        "analysis_risks": []})
    enrich = json.dumps({"survey_summary": {"purpose_inferred": "experiencia académica", "confidence": 0.7},
                        "variables": []})
    svc = SurveyIntelligenceService(
        llm=ScriptedLLM([audit, enrich]), clock=FixedClock(), ids=SequentialIds(),
    )
    req = SurveyIngestionRequest(
        request_id="doc-1",
        survey=SurveyFile(file_name="entrevista.pdf", mime_type="application/pdf",
                          extracted_text=_TRANSCRIPT),
        metadata=_dc(),
        options=IngestionOptions(instrument_type="entrevista"),
    )
    result = svc.process(req)
    assert result.status in (ResultStatus.COMPLETED, ResultStatus.COMPLETED_DEGRADED)
    assert result.canonical_survey_model is not None
    assert result.enriched_survey_model is not None
    # Profiling saltado en vía documento.
    prof = next(s for s in result.diagnostics.stages if s.stage == "profiling")
    assert prof.status.value == "skipped"


def test_document_without_text_fails() -> None:
    """Un documento sin texto extraído da status=failed."""
    svc = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds())
    req = SurveyIngestionRequest(
        request_id="doc-empty",
        survey=SurveyFile(file_name="x.pdf", mime_type="application/pdf", extracted_text=""),
        metadata=_dc(),
        options=IngestionOptions(instrument_type="prueba_estandarizada"),
    )
    result = svc.process(req)
    assert result.status == ResultStatus.FAILED


def _run() -> None:
    test_document_builder_segments()
    test_document_path_end_to_end()
    test_document_without_text_fails()
    print("OK - test_document_path: 3 tests passed")


if __name__ == "__main__":
    _run()
