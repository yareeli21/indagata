# survey_intelligence/tests/test_spss_mapper.py
"""
Tests del spss_mapper determinístico (Tarea 9) sobre fixtures reales.

Verifica value_labels/value_encoding de escalas, el mapeo del typo al código
canónico, niveles de medición, nombres saneados y provenance auto_deterministic.

Ejecutar:
    python -m survey_intelligence.tests.test_spss_mapper
"""
from __future__ import annotations

import base64
import pathlib

from survey_intelligence.contracts.enums import (
    DataType,
    EnrichmentProvenance,
    Measure,
    SpssType,
)
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.engine.spss.spss_validator import is_valid_spss_name
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


def _dict_of(name: str, mime: str):
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
    return canonical, build_spss_dictionary(canonical)


def test_likert_value_labels_and_measure() -> None:
    """Un ítem Likert debe tener 5 value_labels, measure ordinal y tipo numeric."""
    canonical, spss = _dict_of("limesurvey_participacion.csv", "text/csv")
    by_id = {s.variable_id: s for s in spss}
    likert_ids = [
        v.variable_id for v in canonical.variables
        if v.inferred_data_type == DataType.ORDINAL
    ]
    assert likert_ids
    sample = by_id[likert_ids[0]]
    assert sample.measure == Measure.ORDINAL
    assert sample.type == SpssType.NUMERIC
    assert len(sample.value_labels) == 5
    # El código 1 corresponde al extremo bajo canónico.
    assert sample.value_labels["1"] == "Totalmente desacuerdo"
    assert sample.value_labels["5"] == "Totalmente de acuerdo"


def test_typo_maps_to_canonical_code() -> None:
    """'En deesacuerdo' debe codificarse al MISMO código que 'En desacuerdo' (=2)."""
    canonical, spss = _dict_of("limesurvey_participacion.csv", "text/csv")
    by_id = {s.variable_id: s for s in spss}
    # Buscar una variable cuyo encoding incluya el typo.
    target = None
    for s in spss:
        if "En deesacuerdo" in s.value_encoding:
            target = s
            break
    assert target is not None, "ninguna variable mapeó el typo"
    assert target.value_encoding["En deesacuerdo"] == target.value_encoding["En desacuerdo"]
    assert target.value_encoding["En desacuerdo"] == 2


def test_names_are_valid_spss() -> None:
    """Todos los nombres SPSS deben ser válidos (<=64, sin espacios, inicio alfabético)."""
    _, spss = _dict_of("msforms_graduacion.csv", "text/csv")
    for s in spss:
        assert s.name is not None and is_valid_spss_name(s.name), f"nombre inválido: {s.name!r}"


def test_provenance_is_deterministic_for_known_types() -> None:
    """Variables con tipo conocido llevan provenance auto_deterministic."""
    canonical, spss = _dict_of("limesurvey_salud_mental.csv", "text/csv")
    by_id = {s.variable_id: s for s in spss}
    for v in canonical.variables:
        if v.inferred_data_type != DataType.UNKNOWN:
            assert by_id[v.variable_id].enrichment_provenance == EnrichmentProvenance.AUTO_DETERMINISTIC


def test_matrix_label_is_item() -> None:
    """El variable_label de un ítem de matriz es el ítem, no el tronco completo."""
    canonical, spss = _dict_of("msforms_graduacion.csv", "text/csv")
    by_id = {s.variable_id: s for s in spss}
    matrix_vars = [v for v in canonical.variables if v.matrix_group is not None]
    assert matrix_vars
    v = matrix_vars[0]
    assert by_id[v.variable_id].variable_label == v.matrix_group.item


def _run() -> None:
    test_likert_value_labels_and_measure()
    test_typo_maps_to_canonical_code()
    test_names_are_valid_spss()
    test_provenance_is_deterministic_for_known_types()
    test_matrix_label_is_item()
    print("OK - test_spss_mapper: 5 tests passed")


if __name__ == "__main__":
    _run()
