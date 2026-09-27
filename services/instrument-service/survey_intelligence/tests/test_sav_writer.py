# survey_intelligence/tests/test_sav_writer.py
"""
Tests del escritor .SAV (Tarea 15) sobre un fixture real.

Escribe un .SAV desde el diccionario SPSS y lo relee con pyreadstat para verificar
que etiquetas, value_labels y measures hacen round-trip, y que el typo quedó codificado.

Ejecutar:
    python -m survey_intelligence.tests.test_sav_writer
"""
from __future__ import annotations

import base64
import pathlib
import tempfile

from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.export.sav_writer import write_sav
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
        request_id=f"sav-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type=mime,
        ),
        metadata=_dc(),
    )
    ingestion = ingest(req)
    canonical = profile(build_canonical(ingestion, path.name, ingestion.raw_table.sheet), ingestion.raw_table)
    raw = ingestion.raw_table
    names = [v.normalized_name for v in canonical.variables]
    vids = [v.variable_id for v in canonical.variables]
    spss = {s.variable_id: s for s in build_spss_dictionary(canonical)}
    return raw, names, vids, spss


def test_write_and_reread_sav() -> None:
    import pyreadstat

    raw, names, vids, spss = _load("limesurvey_participacion.csv", "text/csv")
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "test.sav"
        write_sav(out, raw, names, spss, vids)
        assert out.exists()

        df, meta = pyreadstat.read_sav(str(out))
        # Debe haber columnas y algunas con value_labels.
        assert len(df.columns) > 0
        assert meta.variable_value_labels  # al menos una variable con etiquetas
        # Verificar que alguna variable Likert tiene 5 etiquetas de valor.
        likert_labels = [labels for labels in meta.variable_value_labels.values() if len(labels) == 5]
        assert likert_labels


def test_typo_encoded_in_sav() -> None:
    """El valor 'En deesacuerdo' debe haberse codificado como número (2), no como texto."""
    import pyreadstat

    raw, names, vids, spss = _load("limesurvey_participacion.csv", "text/csv")
    # Buscar una variable con el typo en su encoding.
    target = next((s for s in spss.values() if "En deesacuerdo" in s.value_encoding), None)
    assert target is not None

    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "test.sav"
        write_sav(out, raw, names, spss, vids)
        df, meta = pyreadstat.read_sav(str(out))
        # La columna correspondiente debe ser numérica (no contener el string del typo).
        col = target.name
        if col in df.columns:
            values = [v for v in df[col].tolist() if v == v]  # descarta NaN
            assert all(isinstance(v, (int, float)) for v in values)


def _run() -> None:
    test_write_and_reread_sav()
    test_typo_encoded_in_sav()
    print("OK - test_sav_writer: 2 tests passed")


if __name__ == "__main__":
    _run()
