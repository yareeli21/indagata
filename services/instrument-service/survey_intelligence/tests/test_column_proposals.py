# survey_intelligence/tests/test_column_proposals.py
"""
Tests de las propuestas de eliminación de columnas (Tarea 7) sobre fixtures reales.

Verifica: propuesta AGRUPADA (no una por columna), propuesta separada para
timestamps con la salvedad de tiempo de respuesta, y estructura del valor_propuesto.

Ejecutar:
    python -m survey_intelligence.tests.test_column_proposals
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence.contracts.enums import ProposalType, TransformId
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.heuristics.column_proposals import build_column_proposals
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.tests.fakes import SequentialIds

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _proposals(name: str, mime: str):
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
    return build_column_proposals(canonical, SequentialIds())


def test_limesurvey_grouped_and_timestamp_split() -> None:
    """
    LimeSurvey tiene 7 columnas admin: 3 no-temporales (Response ID, Last page,
    Start language, Seed) y varias de fecha. Debe producir 2 propuestas:
    una agrupada de no-temporales y otra de timestamps.
    """
    props = _proposals("limesurvey_salud_mental.csv", "text/csv")
    assert len(props) == 2, f"esperaba 2 propuestas, hubo {len(props)}"

    # Ambas son transformaciones drop_columns.
    for p in props:
        assert p.tipo == ProposalType.TRANSFORMACION
        payload = json.loads(p.valor_propuesto)
        assert payload["transform_id"] == TransformId.DROP_COLUMNS.value
        assert isinstance(payload["columnas"], list) and payload["columnas"]

    # Una de las propuestas debe mencionar el tiempo de respuesta.
    assert any("tiempo de respuesta" in p.justificacion for p in props)


def test_grouped_not_one_per_column() -> None:
    """La propuesta de no-temporales agrupa varias columnas en UNA sola."""
    props = _proposals("limesurvey_salud_mental.csv", "text/csv")
    non_ts = [p for p in props if "tiempo de respuesta" not in p.justificacion]
    assert len(non_ts) == 1
    payload = json.loads(non_ts[0].valor_propuesto)
    # Response ID, Last page, Start language, Seed -> al menos 3 columnas agrupadas.
    assert len(payload["columnas"]) >= 3


def test_msforms_proposals() -> None:
    """Microsoft Forms: Id/Nombre/Correo agrupadas; Hora inicio/fin como timestamps."""
    props = _proposals("msforms_graduacion.csv", "text/csv")
    assert len(props) == 2
    ts_prop = [p for p in props if "tiempo de respuesta" in p.justificacion]
    assert len(ts_prop) == 1
    payload = json.loads(ts_prop[0].valor_propuesto)
    # Hora de inicio + Hora de finalización.
    assert len(payload["columnas"]) >= 2


def test_googleforms_single_timestamp() -> None:
    """Google Forms: solo 'Marca temporal' -> una única propuesta (de timestamp)."""
    props = _proposals(
        "googleforms_extracurriculares.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert len(props) == 1
    assert "tiempo de respuesta" in props[0].justificacion


def test_proposal_ids_unique() -> None:
    """Los proposal_id son únicos dentro de un lote."""
    props = _proposals("limesurvey_salud_mental.csv", "text/csv")
    ids = [p.proposal_id for p in props]
    assert len(ids) == len(set(ids))


def _run() -> None:
    test_limesurvey_grouped_and_timestamp_split()
    test_grouped_not_one_per_column()
    test_msforms_proposals()
    test_googleforms_single_timestamp()
    test_proposal_ids_unique()
    print("OK - test_column_proposals: 5 tests passed")


if __name__ == "__main__":
    _run()
