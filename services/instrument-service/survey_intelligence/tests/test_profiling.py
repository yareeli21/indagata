# survey_intelligence/tests/test_profiling.py
"""
Tests de la etapa S3 (Data Profiler) sobre fixtures reales.

Cubre: detección de escala Likert, anomalía de typo (En deesacuerdo),
multi_select, tipos, y que las métricas queden en el Canonical.

Ejecutar:
    python -m survey_intelligence.tests.test_profiling
"""
from __future__ import annotations

import base64
import pathlib

from survey_intelligence.contracts.enums import DataType, ScaleKind
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.profiling.scale_detector import detect_scale
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _profiled(name: str, mime: str):
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
    canonical = build_canonical(ingestion, path.name, ingestion.raw_table.sheet)
    return profile(canonical, ingestion.raw_table)


# ── Tests unitarios del detector de escala ───────────────────────────────────

def test_detect_likert_agreement() -> None:
    vals = ["De acuerdo", "Totalmente de acuerdo", "En desacuerdo",
            "Ni de acuerdo ni en desacuerdo", "Totalmente desacuerdo"]
    scale = detect_scale(vals)
    assert scale is not None and scale.kind == ScaleKind.LIKERT and scale.points == 5


def test_detect_scale_typo_anomaly() -> None:
    """'En deesacuerdo' debe detectarse como variante de 'En desacuerdo'."""
    vals = ["De acuerdo", "En deesacuerdo", "En deesacuerdo", "Totalmente de acuerdo",
            "Ni de acuerdo ni en desacuerdo", "Totalmente desacuerdo"]
    scale = detect_scale(vals)
    assert scale is not None
    assert not scale.consistent
    anomaly_values = {a.value: a for a in scale.anomalies}
    assert "En deesacuerdo" in anomaly_values
    assert anomaly_values["En deesacuerdo"].canonical_guess == "En desacuerdo"
    assert anomaly_values["En deesacuerdo"].occurrences == 2


def test_detect_quality_scale() -> None:
    vals = ["Buena", "Mala", "Regular", "Muy buena", "Muy mala"]
    scale = detect_scale(vals)
    assert scale is not None and scale.points == 5


# ── Tests de S3 sobre fixtures reales ────────────────────────────────────────

def test_participacion_likert_and_typo() -> None:
    """La matriz de participación es Likert 5pts y contiene el typo 'En deesacuerdo'."""
    c = _profiled("limesurvey_participacion.csv", "text/csv")
    likert_vars = [v for v in c.variables if v.detected_scale and v.detected_scale.kind == ScaleKind.LIKERT]
    assert len(likert_vars) >= 25  # la mayoría de los 33 items
    # Debe existir al menos una anomalía de typo en toda la encuesta.
    anomalies = [a for v in c.variables if v.detected_scale for a in v.detected_scale.anomalies]
    assert any(a.value == "En deesacuerdo" and a.canonical_guess == "En desacuerdo" for a in anomalies)
    # Los items Likert son ordinales.
    assert all(v.inferred_data_type == DataType.ORDINAL for v in likert_vars)


def test_msforms_multi_select_detected() -> None:
    """La columna de factores (valores con ';') debe detectarse como multi_select."""
    c = _profiled("msforms_graduacion.csv", "text/csv")
    multi = [v for v in c.variables if v.inferred_data_type == DataType.MULTI_SELECT]
    assert len(multi) >= 1
    # La escala de calidad (.subitem) debe ser Likert.
    likert = [v for v in c.variables if v.detected_scale and v.detected_scale.kind == ScaleKind.LIKERT]
    assert len(likert) >= 5


def test_googleforms_multi_select_comma() -> None:
    """Google Forms usa ', ' como separador multi_select."""
    c = _profiled("googleforms_extracurriculares.xlsx",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    multi = [v for v in c.variables if v.inferred_data_type == DataType.MULTI_SELECT]
    assert len(multi) >= 1


def test_metrics_present_in_canonical() -> None:
    """Cada variable debe tener value_distribution tras el profiling."""
    c = _profiled("limesurvey_salud_mental.csv", "text/csv")
    assert all(v.value_distribution is not None for v in c.variables)
    # canonical_id se preserva tras el profiling (model_copy no lo cambia).
    assert c.canonical_id.startswith("sha256:")


def _run() -> None:
    test_detect_likert_agreement()
    test_detect_scale_typo_anomaly()
    test_detect_quality_scale()
    test_participacion_likert_and_typo()
    test_msforms_multi_select_detected()
    test_googleforms_multi_select_comma()
    test_metrics_present_in_canonical()
    print("OK - test_profiling: 7 tests passed")


if __name__ == "__main__":
    _run()
