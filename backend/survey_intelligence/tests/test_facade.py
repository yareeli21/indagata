# survey_intelligence/tests/test_facade.py
"""
Tests end-to-end de la fachada SurveyIntelligenceService (Tarea 13).

Ejecuta el pipeline completo S1..S9 sobre fixtures reales con LLM falso, verifica el
resultado completo, la degradación sin LLM, y el status=failed ante archivo corrupto.

Ejecutar:
    python -m survey_intelligence.tests.test_facade
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence import (
    SurveyIngestionRequest,
    SurveyIntelligenceService,
)
from survey_intelligence.contracts.enums import ResultStatus
from survey_intelligence.contracts.request import DublinCoreMetadata, SurveyFile
from survey_intelligence.tests.fakes import FixedClock, ScriptedLLM, SequentialIds

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _request(name: str, mime: str) -> SurveyIngestionRequest:
    path = _FIXTURES / name
    return SurveyIngestionRequest(
        request_id=f"e2e-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type=mime,
        ),
        metadata=_dc(),
    )


def _audit_and_enrich_responses():
    """Respuestas del LLM para auditoría, enriquecimiento y KPIs."""
    audit = json.dumps({"ambiguous_questions": [], "double_barreled": [],
                        "wording_bias_suspected": [], "methodology_deficiencies": [],
                        "analysis_risks": []})
    enrich = json.dumps({"survey_summary": {"purpose_inferred": "compromiso escolar", "confidence": 0.8},
                        "variables": []})
    kpis = json.dumps({"kpis": []})
    return [audit, enrich, kpis]


def test_full_pipeline_with_llm() -> None:
    svc = SurveyIntelligenceService(
        llm=ScriptedLLM(_audit_and_enrich_responses()),
        clock=FixedClock(), ids=SequentialIds(),
        kpi_catalog=[{"nombre": "Compromiso escolar", "descripcion": "engagement"}],
    )
    result = svc.process(_request("limesurvey_participacion.csv", "text/csv"))

    assert result.status in (ResultStatus.COMPLETED, ResultStatus.COMPLETED_DEGRADED)
    assert result.canonical_survey_model is not None
    assert result.enriched_survey_model is not None
    assert len(result.canonical_survey_model.variables) == 40
    # Propuestas de columnas de plataforma presentes.
    assert result.proposals
    # Improvement opportunities (incluida la regla del typo).
    assert result.improvement_opportunities
    # Diagnósticos autoexplicativos.
    stage_names = {s.stage for s in result.diagnostics.stages}
    assert "ingestion" in stage_names and "gap_analysis" in stage_names
    # Resolución determinística de codebook saltada cuando no se aporta codebook
    # (reemplazó a la antigua etapa RAG "rag_retrieval").
    cb = next(s for s in result.diagnostics.stages if s.stage == "codebook_resolution")
    assert cb.status.value == "skipped"


def test_pipeline_without_llm_degrades_but_completes() -> None:
    """Sin LLM, el pipeline entrega Canonical + determinístico y marca degraded."""
    svc = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds())
    result = svc.process(_request("msforms_graduacion.csv", "text/csv"))
    assert result.status == ResultStatus.COMPLETED_DEGRADED
    assert result.canonical_survey_model is not None
    assert result.diagnostics.degraded
    # Sin LLM no hay llamadas.
    assert result.diagnostics.llm_calls == 0


def test_corrupt_file_fails_gracefully() -> None:
    """Archivo corrupto -> status=failed, sin excepción al host."""
    svc = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds())
    req = SurveyIngestionRequest(
        request_id="e2e-corrupt",
        survey=SurveyFile(
            file_name="broken.xlsx",
            file_bytes_b64=base64.b64encode(b"not a zip").decode(),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        metadata=_dc(),
    )
    result = svc.process(req)
    assert result.status == ResultStatus.FAILED
    assert result.canonical_survey_model is None


def test_versions_present() -> None:
    svc = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds())
    result = svc.process(_request("googleforms_extracurriculares.xlsx",
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
    assert result.schema_version.startswith("sis-")
    assert result.pipeline_version.startswith("pipeline-")
    assert result.canonical_survey_model.canonical_id.startswith("sha256:")


def _run() -> None:
    test_full_pipeline_with_llm()
    test_pipeline_without_llm_degrades_but_completes()
    test_corrupt_file_fails_gracefully()
    test_versions_present()
    print("OK - test_facade: 4 tests passed")


if __name__ == "__main__":
    _run()
