# survey_intelligence/tests/test_kpi_inference.py
"""
Tests de la inferencia de KPIs contra catálogo (Tarea 18).

Verifica: matching contra catálogo, rechazo de KPIs inventados, clamp del score,
catálogo vacío -> [], y degradación ante fallo del LLM.

Ejecutar:
    python -m survey_intelligence.tests.test_kpi_inference
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s7b_kpi_inference import run_kpi_inference
from survey_intelligence.tests.fakes import FailingLLM, ScriptedLLM

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

_CATALOG = [
    {"nombre": "Compromiso escolar", "descripcion": "Nivel de engagement del estudiante"},
    {"nombre": "Bienestar emocional", "descripcion": "Estado emocional autopercibido"},
]


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _canonical(name: str, mime: str):
    path = _FIXTURES / name
    req = SurveyIngestionRequest(
        request_id=f"test-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type=mime,
        ),
        metadata=_dc(),
    )
    ingestion = ingest(req)
    return profile(build_canonical(ingestion, path.name, ingestion.raw_table.sheet), ingestion.raw_table)


def test_kpi_matches_catalog() -> None:
    canonical = _canonical("limesurvey_participacion.csv", "text/csv")
    response = json.dumps({"kpis": [
        {"nombre_sugerido": "Compromiso escolar", "score_relevancia": 0.9,
         "tipo_relacion": "directa", "evidencia_textual": "batería de engagement",
         "variables_fuente": []},
    ]})
    result = run_kpi_inference(canonical, "compromiso escolar", _CATALOG, ScriptedLLM([response]))
    assert not result.degraded
    assert len(result.kpis) == 1
    assert result.kpis[0].nombre_sugerido == "Compromiso escolar"
    assert result.kpis[0].score_relevancia == 0.9


def test_invented_kpi_rejected() -> None:
    """Un KPI que no está en el catálogo se descarta (no se inventa)."""
    canonical = _canonical("limesurvey_participacion.csv", "text/csv")
    response = json.dumps({"kpis": [
        {"nombre_sugerido": "KPI Inventado", "score_relevancia": 0.95},
        {"nombre_sugerido": "Bienestar emocional", "score_relevancia": 0.7},
    ]})
    result = run_kpi_inference(canonical, None, _CATALOG, ScriptedLLM([response]))
    names = [k.nombre_sugerido for k in result.kpis]
    assert "KPI Inventado" not in names
    assert "Bienestar emocional" in names


def test_score_clamped() -> None:
    """Un score fuera de [0,1] se recorta."""
    canonical = _canonical("limesurvey_participacion.csv", "text/csv")
    response = json.dumps({"kpis": [
        {"nombre_sugerido": "Compromiso escolar", "score_relevancia": 5.0},
    ]})
    result = run_kpi_inference(canonical, None, _CATALOG, ScriptedLLM([response]))
    assert result.kpis[0].score_relevancia == 1.0


def test_empty_catalog_returns_empty() -> None:
    """Sin catálogo no hay matching posible; devuelve [] sin llamar al LLM."""
    canonical = _canonical("limesurvey_participacion.csv", "text/csv")
    result = run_kpi_inference(canonical, None, [], ScriptedLLM(["{}"]))
    assert result.kpis == []
    assert result.llm_calls == 0


def test_degrades_on_llm_failure() -> None:
    canonical = _canonical("limesurvey_participacion.csv", "text/csv")
    result = run_kpi_inference(canonical, None, _CATALOG, FailingLLM())
    assert result.degraded
    assert result.kpis == []


def _run() -> None:
    test_kpi_matches_catalog()
    test_invented_kpi_rejected()
    test_score_clamped()
    test_empty_catalog_returns_empty()
    test_degrades_on_llm_failure()
    print("OK - test_kpi_inference: 5 tests passed")


if __name__ == "__main__":
    _run()
