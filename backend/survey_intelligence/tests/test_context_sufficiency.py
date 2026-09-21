# survey_intelligence/tests/test_context_sufficiency.py
"""
Tests de la etapa S4 (Context Sufficiency) sobre fixtures reales.

Verifica el paso 1 de la restricción crítica: 'Seed' se marca INSUFFICIENT_CONTEXT,
los ítems con encabezado descriptivo NO, y las columnas de plataforma tampoco.

Ejecutar:
    python -m survey_intelligence.tests.test_context_sufficiency
"""
from __future__ import annotations

import base64
import pathlib

from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s4_context_sufficiency import (
    assess_context,
    insufficient_variable_ids,
)

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _assess(name: str, mime: str):
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
    canonical = profile(canonical, ingestion.raw_table)
    return canonical, assess_context(canonical)


def test_descriptive_items_are_interpretable() -> None:
    """Los ítems Likert con encabezado descriptivo NO son insuficientes."""
    canonical, verdicts = _assess("limesurvey_participacion.csv", "text/csv")
    # Todos los ítems de la matriz Likert deben ser interpretables.
    likert = [v for v in canonical.variables if v.detected_scale and v.matrix_group]
    assert likert
    assert all(verdicts[v.variable_id].is_interpretable for v in likert)


def test_platform_columns_not_insufficient() -> None:
    """Las columnas de plataforma no son candidatas a INSUFFICIENT_CONTEXT."""
    canonical, verdicts = _assess("limesurvey_salud_mental.csv", "text/csv")
    from survey_intelligence.contracts.enums import ColumnClass
    platform = [v for v in canonical.variables if v.column_class == ColumnClass.PLATFORM_METADATA]
    assert platform
    assert all(verdicts[v.variable_id].is_interpretable for v in platform)


def test_free_text_is_interpretable() -> None:
    """El texto libre es interpretable (el texto es su propia evidencia)."""
    canonical, verdicts = _assess("msforms_graduacion.csv", "text/csv")
    from survey_intelligence.contracts.enums import ColumnClass
    free_text = [v for v in canonical.variables if v.column_class == ColumnClass.FREE_TEXT]
    assert free_text
    assert all(verdicts[v.variable_id].is_interpretable for v in free_text)


def test_synthetic_seed_like_column_is_insufficient() -> None:
    """
    Una columna tipo 'Seed' (numérica, sin pregunta, sin escala, sin matriz) que NO
    sea clasificada como plataforma debe caer en INSUFFICIENT_CONTEXT con diagnóstico.
    """
    from survey_intelligence.contracts.canonical import CanonicalVariable
    from survey_intelligence.contracts.enums import ColumnClass, DataType
    from survey_intelligence.engine.heuristics.context_sufficiency import evaluate_variable

    var = CanonicalVariable(
        variable_id="v_x",
        raw_header="q17",
        normalized_name="q17",
        position=17,
        column_class=ColumnClass.QUESTION,
        inferred_data_type=DataType.NUMERIC,
        detected_scale=None,
        matrix_group=None,
        value_distribution=None,
    )
    verdict = evaluate_variable(var)
    assert not verdict.is_interpretable
    assert verdict.why_not_interpretable is not None
    assert verdict.missing_information
    assert verdict.required_to_interpret
    # No inventa significado: solo dice qué falta.
    assert any("codebook" in m for m in verdict.missing_information)


def test_insufficient_ids_helper() -> None:
    """El helper de IDs insuficientes es coherente con los veredictos."""
    _, verdicts = _assess("limesurvey_participacion.csv", "text/csv")
    ids = insufficient_variable_ids(verdicts)
    # En estos fixtures, con encabezados autodescriptivos, la mayoría es interpretable.
    for vid in ids:
        assert not verdicts[vid].is_interpretable


def _run() -> None:
    test_descriptive_items_are_interpretable()
    test_platform_columns_not_insufficient()
    test_free_text_is_interpretable()
    test_synthetic_seed_like_column_is_insufficient()
    test_insufficient_ids_helper()
    print("OK - test_context_sufficiency: 5 tests passed")


if __name__ == "__main__":
    _run()
