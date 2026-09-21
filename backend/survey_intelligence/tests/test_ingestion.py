# survey_intelligence/tests/test_ingestion.py
"""
Tests de la etapa S1 (ingesta) y los readers, sobre fixtures reales de las 3 plataformas.

Ejecutar:
    python -m survey_intelligence.tests.test_ingestion
"""
from __future__ import annotations

import base64
import pathlib

from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.pipeline.stages.s1_ingestion import IngestionError, ingest

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _request_for(path: pathlib.Path, mime: str, fmt_name: str) -> SurveyIngestionRequest:
    data = path.read_bytes()
    return SurveyIngestionRequest(
        request_id=f"test-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(data).decode(),
            mime_type=mime,
        ),
        metadata=_dc(),
    )


def test_limesurvey_participacion_csv() -> None:
    """LimeSurvey Likert: BOM UTF-8, 40 columnas, 7 admin, fila vacía manejada."""
    req = _request_for(_FIXTURES / "limesurvey_participacion.csv", "text/csv", "csv")
    result = ingest(req)

    assert result.raw_table.n_columns == 40
    assert result.platform.platform_guess == "limesurvey"
    # Las 7 columnas de plataforma deben estar marcadas como administrativas.
    admin_lower = {h.lower() for h in result.platform.admin_headers}
    assert "response id" in admin_lower
    assert "seed" in admin_lower
    assert "date submitted" in admin_lower
    # La codificación detectada debe ser UTF-8 (con BOM consumido).
    assert result.raw_table.encoding in ("utf-8-sig", "utf-8")


def test_limesurvey_salud_mental_csv() -> None:
    """LimeSurvey tipos mixtos: 40 columnas, plataforma detectada."""
    req = _request_for(_FIXTURES / "limesurvey_salud_mental.csv", "text/csv", "csv")
    result = ingest(req)
    assert result.raw_table.n_columns == 40
    assert result.platform.platform_guess == "limesurvey"


def test_msforms_graduacion_csv() -> None:
    """Microsoft Forms: 17 columnas, admin propias, newlines en headers normalizados."""
    req = _request_for(_FIXTURES / "msforms_graduacion.csv", "text/csv", "csv")
    result = ingest(req)

    assert result.raw_table.n_columns == 17
    assert result.platform.platform_guess == "microsoft_forms"
    admin_lower = {h.lower() for h in result.platform.admin_headers}
    assert "hora de inicio" in admin_lower
    assert "correo electrónico" in admin_lower
    # Los encabezados de matriz (.subitem) NO deben tener saltos de línea.
    assert all("\n" not in h for h in result.raw_table.headers)
    # La escala de la col 7 quedó como pregunta (contiene '?'), no como admin.
    assert any("probable" in h.lower() for h in result.raw_table.headers)


def test_googleforms_extracurriculares_xlsx() -> None:
    """Google Forms XLSX: openpyxl, datetime nativo, firma mínima 'Marca temporal'."""
    path = _FIXTURES / "googleforms_extracurriculares.xlsx"
    req = _request_for(
        path,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    )
    result = ingest(req)

    assert result.raw_table.n_columns == 8
    assert result.platform.platform_guess == "google_forms"
    admin_lower = {h.lower() for h in result.platform.admin_headers}
    assert "marca temporal" in admin_lower
    # La marca temporal (datetime) se serializó a ISO string en la primera fila.
    ts = result.raw_table.rows[0][0]
    assert ts.startswith("2026-"), f"timestamp inesperado: {ts!r}"


def test_corrupt_input_raises() -> None:
    """Un archivo no parseable debe lanzar IngestionError (fatal)."""
    req = SurveyIngestionRequest(
        request_id="test-corrupt",
        survey=SurveyFile(
            file_name="broken.xlsx",
            file_bytes_b64=base64.b64encode(b"not really a zip").decode(),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        metadata=_dc(),
    )
    try:
        ingest(req)
        raise AssertionError("Se esperaba IngestionError")
    except IngestionError:
        pass


def test_unsupported_format_raises() -> None:
    """Un formato no soportado debe lanzar IngestionError."""
    req = SurveyIngestionRequest(
        request_id="test-pdf",
        survey=SurveyFile(
            file_name="doc.pdf",
            file_bytes_b64=base64.b64encode(b"%PDF-1.4").decode(),
            mime_type="application/pdf",
        ),
        metadata=_dc(),
    )
    try:
        ingest(req)
        raise AssertionError("Se esperaba IngestionError")
    except IngestionError:
        pass


def _run() -> None:
    test_limesurvey_participacion_csv()
    test_limesurvey_salud_mental_csv()
    test_msforms_graduacion_csv()
    test_googleforms_extracurriculares_xlsx()
    test_corrupt_input_raises()
    test_unsupported_format_raises()
    print("OK - test_ingestion: 6 tests passed")


if __name__ == "__main__":
    _run()
