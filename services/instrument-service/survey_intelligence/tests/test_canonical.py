# survey_intelligence/tests/test_canonical.py
"""
Tests de la etapa S2 (Canonical Survey Model builder) sobre fixtures reales.

Ejecutar:
    python -m survey_intelligence.tests.test_canonical
"""
from __future__ import annotations

import base64
import pathlib

from survey_intelligence.contracts.enums import ColumnClass
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.profiling.matrix_parser import parse_matrix
from survey_intelligence.engine.profiling.name_normalizer import (
    normalize_name,
    unique_names,
)
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _canonical_of(name: str, mime: str) -> object:
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
    return build_canonical(ingestion, path.name, ingestion.raw_table.sheet)


# ── Tests unitarios de los parsers ───────────────────────────────────────────

def test_matrix_bracket_notation() -> None:
    p = parse_matrix("Evalúa los aspectos del servicio. [Confidencialidad]")
    assert p.is_matrix and p.item == "Confidencialidad"
    assert p.stem.startswith("Evalúa")


def test_matrix_dot_notation() -> None:
    p = parse_matrix("Evalúa los siguientes aspectos de tu experiencia académica .Calidad de la enseñanza")
    assert p.is_matrix and p.item == "Calidad de la enseñanza"


def test_simple_question_not_matrix() -> None:
    p = parse_matrix("¿Has considerado abandonar tus estudios en algún momento?")
    assert not p.is_matrix


def test_name_normalizer() -> None:
    assert normalize_name("Estoy muy interesado/a en aprender.") == "estoy_muy_interesado_aprender"
    assert unique_names(["a", "a", "b", "a"]) == ["a", "a_2", "b", "a_3"]


# ── Tests de S2 sobre fixtures reales ────────────────────────────────────────

def test_limesurvey_participacion_matrix_grouping() -> None:
    """La matriz Likert de 33 ítems debe agruparse bajo varias preguntas matriz."""
    c = _canonical_of("limesurvey_participacion.csv", "text/csv")
    # 7 admin + 33 items = 40 variables
    assert len(c.variables) == 40
    admin = [v for v in c.variables if v.column_class == ColumnClass.PLATFORM_METADATA]
    assert len(admin) == 7
    # Todas las variables con matrix_group deben tener stem+item.
    matrix_vars = [v for v in c.variables if v.matrix_group is not None]
    assert len(matrix_vars) == 33
    # Debe haber varias preguntas matriz (distintos troncos), no 33 preguntas sueltas.
    matrix_questions = [q for q in c.questions if len(q.variable_ids) > 1]
    assert len(matrix_questions) >= 4


def test_msforms_dot_matrix_and_freetext() -> None:
    """Microsoft Forms: matriz .subitem agrupada y columnas de texto libre detectadas."""
    c = _canonical_of("msforms_graduacion.csv", "text/csv")
    matrix_vars = [v for v in c.variables if v.matrix_group is not None]
    # Las 5 columnas 'Evalúa ... .subitem' deben agruparse.
    assert len(matrix_vars) >= 5
    free_text = [v for v in c.variables if v.column_class == ColumnClass.FREE_TEXT]
    # Las columnas de opinión abierta (mejoras, otro factor) son texto libre.
    assert len(free_text) >= 1


def test_googleforms_no_matrix_freetext_absent() -> None:
    """Google Forms: preguntas simples, sin matriz."""
    c = _canonical_of("googleforms_extracurriculares.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    matrix_vars = [v for v in c.variables if v.matrix_group is not None]
    assert len(matrix_vars) == 0
    assert c.source.platform_guess == "google_forms"


def test_canonical_id_deterministic() -> None:
    """El mismo archivo produce el mismo canonical_id en dos corridas."""
    c1 = _canonical_of("limesurvey_salud_mental.csv", "text/csv")
    c2 = _canonical_of("limesurvey_salud_mental.csv", "text/csv")
    assert c1.canonical_id == c2.canonical_id
    assert c1.canonical_id.startswith("sha256:")


def test_canonical_id_differs_between_surveys() -> None:
    """Dos encuestas distintas producen canonical_id distintos."""
    c1 = _canonical_of("limesurvey_salud_mental.csv", "text/csv")
    c2 = _canonical_of("limesurvey_participacion.csv", "text/csv")
    assert c1.canonical_id != c2.canonical_id


def _run() -> None:
    test_matrix_bracket_notation()
    test_matrix_dot_notation()
    test_simple_question_not_matrix()
    test_name_normalizer()
    test_limesurvey_participacion_matrix_grouping()
    test_msforms_dot_matrix_and_freetext()
    test_googleforms_no_matrix_freetext_absent()
    test_canonical_id_deterministic()
    test_canonical_id_differs_between_surveys()
    print("OK - test_canonical: 9 tests passed")


if __name__ == "__main__":
    _run()
