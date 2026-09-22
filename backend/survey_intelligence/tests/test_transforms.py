# survey_intelligence/tests/test_transforms.py
"""
Tests del motor de transformaciones (Tarea 8) sobre fixtures reales.

Cubre: aplicar drop_columns, reversibilidad, normalize_scale del typo real,
regeneración del Canonical, y que sin decisiones no se muta nada.

Ejecutar:
    python -m survey_intelligence.tests.test_transforms
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
from survey_intelligence.engine.transforms.apply_engine import (
    apply_decisions,
    rebuild_canonical_after_apply,
)
from survey_intelligence.engine.transforms.drop_columns import (
    apply_drop_columns,
    undo_drop_columns,
)
from survey_intelligence.engine.transforms.models import TransformDecision
from survey_intelligence.engine.transforms.normalize_scale import apply_normalize_scale
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


def _load(name: str, mime: str):
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
    canonical = profile(build_canonical(ingestion, path.name, ingestion.raw_table.sheet), ingestion.raw_table)
    names = [v.normalized_name for v in canonical.variables]
    return ingestion.raw_table, names, canonical


def test_drop_columns_and_reverse() -> None:
    """drop_columns elimina columnas y undo las restaura idénticas."""
    raw, names, _ = _load("limesurvey_salud_mental.csv", "text/csv")
    original_cols = raw.n_columns

    new_table, applied = apply_drop_columns(raw, names, ["response_id", "seed"])
    assert new_table.n_columns == original_cols - 2
    assert "Response ID" not in new_table.headers
    assert "Seed" not in new_table.headers

    restored = undo_drop_columns(new_table, applied)
    assert restored.headers == raw.headers
    assert restored.rows == raw.rows


def test_no_mutation_without_decisions() -> None:
    """Sin decisiones, el apply_engine no cambia nada."""
    raw, names, _ = _load("limesurvey_salud_mental.csv", "text/csv")
    result = apply_decisions(raw, names, [])
    assert result.raw_table.headers == raw.headers
    assert result.applied == []


def test_normalize_scale_fixes_typo() -> None:
    """normalize_scale corrige 'En deesacuerdo' -> 'En desacuerdo' en una columna."""
    raw, names, canonical = _load("limesurvey_participacion.csv", "text/csv")
    # Buscar una columna que tenga el typo en su escala.
    target = None
    for v in canonical.variables:
        if v.detected_scale and any(a.value == "En deesacuerdo" for a in v.detected_scale.anomalies):
            target = v
            break
    assert target is not None, "no se encontró columna con el typo"

    col = target.normalized_name
    idx = names.index(col)
    before = sum(1 for row in raw.rows if idx < len(row) and row[idx] == "En deesacuerdo")
    assert before >= 1

    new_table, applied = apply_normalize_scale(
        raw, names, col, {"En deesacuerdo": "En desacuerdo"}
    )
    after = sum(1 for row in new_table.rows if idx < len(row) and row[idx] == "En deesacuerdo")
    assert after == 0
    assert len(applied.undo_data["changed_cells"]) == before


def test_apply_engine_drop_then_rebuild_canonical() -> None:
    """El apply_engine aplica drop_columns y regenera un Canonical sin esas columnas."""
    raw, names, canonical = _load("limesurvey_salud_mental.csv", "text/csv")
    platform_names = [
        v.normalized_name for v in canonical.variables
        if v.column_class == ColumnClass.PLATFORM_METADATA
    ]
    assert platform_names

    decision = TransformDecision(
        transform_id="drop_columns",
        params={"columnas": platform_names},
    )
    result = apply_decisions(raw, names, [decision])
    assert result.raw_table.n_columns == raw.n_columns - len(platform_names)

    new_canonical = rebuild_canonical_after_apply(canonical, result)
    # Ya no debe haber columnas de plataforma en el nuevo Canonical.
    remaining_platform = [
        v for v in new_canonical.variables if v.column_class == ColumnClass.PLATFORM_METADATA
    ]
    assert remaining_platform == []


def test_unknown_transform_skipped() -> None:
    """Una transformación no registrada se omite sin romper."""
    raw, names, _ = _load("googleforms_extracurriculares.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    result = apply_decisions(raw, names, [TransformDecision("does_not_exist", {})])
    assert "does_not_exist" in result.skipped
    assert result.raw_table.headers == raw.headers


def _run() -> None:
    test_drop_columns_and_reverse()
    test_no_mutation_without_decisions()
    test_normalize_scale_fixes_typo()
    test_apply_engine_drop_then_rebuild_canonical()
    test_unknown_transform_skipped()
    print("OK - test_transforms: 5 tests passed")


if __name__ == "__main__":
    _run()
