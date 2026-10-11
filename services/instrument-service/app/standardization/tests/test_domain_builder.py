"""Snapshot del domain_builder contra el esquema reducido del seed (diseño §1.4)."""
from __future__ import annotations

from app.parsing.raw_table import RawTable
from app.standardization import domain_builder as db


def _tabla() -> RawTable:
    return RawTable(
        headers=["edad", "claridad", "tamanio"],
        rows=[
            ["18", "4", "15-29"],
            ["22", "2", "30-49"],
            ["", "5", "15-29"],
        ],
    )


def _preguntas() -> list[db.PreguntaDominio]:
    return [
        db.PreguntaDominio(
            question_id="q1", text="edad", type="numerica_continua",
            es_demografica=True, columna=0,
        ),
        db.PreguntaDominio(
            question_id="q2", text="claridad", type="likert",
            es_demografica=False, columna=1,
            options=["1", "2", "3", "4", "5"], scale_min=1, scale_max=5,
        ),
        db.PreguntaDominio(
            question_id="q3", text="tamanio", type="opcion_multiple",
            es_demografica=False, columna=2, options=["15-29", "30-49"],
        ),
    ]


def test_claves_del_esquema_del_seed():
    out = db.construir_tabular(
        id_crudo=5, titulo="archivo.csv", tabla=_tabla(), preguntas=_preguntas()
    )
    assert out["instrument_id"] == "upload_5"
    assert out["schema_version"] == "1.0"
    assert set(out["instrument"].keys()) == {
        "title", "objective", "dimensions_explored", "sections"
    }
    assert set(out["metadata"].keys()) == {"dublin_core", "survey_specific"}
    assert out["metadata"]["dublin_core"] == {}
    assert out["metadata"]["survey_specific"] == {}
    assert set(out["design_reference"].keys()) == {"kpi_hints", "note"}
    assert "respondents" in out
    seccion = out["instrument"]["sections"][0]
    assert seccion["name"] == "Reactivos del módulo"


def test_omite_synthetic_profiles_y_profile_id():
    out = db.construir_tabular(
        id_crudo=5, titulo="archivo.csv", tabla=_tabla(), preguntas=_preguntas()
    )
    assert "synthetic_profiles" not in out
    for r in out["respondents"]:
        assert "profile_id" not in r


def test_preguntas_excluyen_demograficas():
    out = db.construir_tabular(
        id_crudo=5, titulo="archivo.csv", tabla=_tabla(), preguntas=_preguntas()
    )
    questions = out["instrument"]["sections"][0]["questions"]
    ids = [q["question_id"] for q in questions]
    # q1 (edad) es demográfica -> NO es pregunta del instrumento.
    assert ids == ["q2", "q3"]
    likert = questions[0]
    assert likert["type"] == "likert"
    assert likert["scale_min"] == 1 and likert["scale_max"] == 5
    assert "options" in likert
    mc = questions[1]
    assert mc["type"] == "opcion_multiple"
    assert "options" in mc
    assert "scale_min" not in mc


def test_respondents_demographics_y_answers():
    out = db.construir_tabular(
        id_crudo=5, titulo="archivo.csv", tabla=_tabla(), preguntas=_preguntas()
    )
    respondents = out["respondents"]
    assert len(respondents) == 3
    assert respondents[0]["respondent_id"] == "r_0001"
    assert respondents[0]["demographics"] == {"edad": 18}
    assert respondents[0]["answers"]["q2"] == 4  # likert coaccionado a int
    assert respondents[0]["answers"]["q3"] == "15-29"
    # Celda vacía -> None.
    assert respondents[2]["demographics"]["edad"] is None


def test_documento_una_pregunta_abierta_sin_respondents():
    out = db.construir_documento(
        id_crudo=7, titulo="entrevista.txt", texto="Texto completo del documento."
    )
    assert out["instrument_id"] == "upload_7"
    assert out["respondents"] == []
    questions = out["instrument"]["sections"][0]["questions"]
    assert len(questions) == 1
    assert questions[0]["type"] == "abierta"
    assert questions[0]["text"] == "Texto completo del documento."
