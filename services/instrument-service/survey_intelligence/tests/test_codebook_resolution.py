# survey_intelligence/tests/test_codebook_resolution.py
"""
Tests del módulo de lectura y resolución determinística de Codebooks (S5).

Verifica:
  1. Lectura de codebooks en CSV (valores en línea y multi-fila).
  2. Lectura de codebooks en JSON y formato de texto.
  3. Búsqueda tolerante por identificador ($O(1)$).
  4. Resolución de variables insuficientes (actualización a interpretable).
  5. Enriquecimiento de DetectedScale y texto de preguntas con datos del codebook.
  6. Comportamiento 'skipped' sin codebook.

Ejecutar:
    python -m survey_intelligence.tests.test_codebook_resolution
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import (
    CanonicalQuestion,
    CanonicalSurveyModel,
    CanonicalVariable,
    Dimensions,
    SourceInfo,
)
from survey_intelligence.contracts.codebook import CodebookEntry, CodebookModel
from survey_intelligence.contracts.enums import ColumnClass, DataType, ScaleKind
from survey_intelligence.engine.heuristics.context_sufficiency import SufficiencyVerdict
from survey_intelligence.engine.readers.codebook_reader import read_codebook
from survey_intelligence.pipeline.stages.s5_codebook_resolution import resolve_codebook


def _canonical_with_codebook_candidate() -> CanonicalSurveyModel:
    var1 = CanonicalVariable(
        variable_id="v_001", raw_header="P01_1", normalized_name="p01_1", position=1,
        column_class=ColumnClass.QUESTION, inferred_data_type=DataType.NUMERIC,
    )
    var2 = CanonicalVariable(
        variable_id="v_002", raw_header="EDAD", normalized_name="edad", position=2,
        column_class=ColumnClass.QUESTION, inferred_data_type=DataType.NUMERIC,
    )
    q1 = CanonicalQuestion(
        question_id="q_001", variable_ids=["v_001"], text="P01_1",
        length_chars=5, length_words=1,
    )
    q2 = CanonicalQuestion(
        question_id="q_002", variable_ids=["v_002"], text="EDAD",
        length_chars=4, length_words=1,
    )
    return CanonicalSurveyModel(
        canonical_id="sha256:test",
        source=SourceInfo(platform_guess=None, file_name="microdatos.csv"),
        dimensions=Dimensions(n_rows=10, n_columns=2),
        variables=[var1, var2],
        questions=[q1, q2],
    )


def _verdicts_initial() -> dict[str, SufficiencyVerdict]:
    return {
        "v_001": SufficiencyVerdict(
            variable_id="v_001", is_interpretable=False,
            missing_information=["codebook"], why_not_interpretable="sin contexto",
            required_to_interpret=["codebook"],
        ),
        "v_002": SufficiencyVerdict(
            variable_id="v_002", is_interpretable=False,
            missing_information=["codebook"], why_not_interpretable="sin contexto",
            required_to_interpret=["codebook"],
        ),
    }


def test_read_codebook_csv_inline() -> None:
    csv_content = (
        "variable,etiqueta,valores\n"
        "P01_1,¿Parentesco con el jefe del hogar?,1=Jefe; 2=Cónyuge; 3=Hijo\n"
        "EDAD,Edad en años cumplidos,\n"
    )
    model = read_codebook(csv_content, file_name="diccionario.csv")
    assert len(model.entries) == 2
    p01 = model.lookup("P01_1")
    assert p01 is not None
    assert p01.label == "¿Parentesco con el jefe del hogar?"
    assert p01.value_labels == {"1": "Jefe", "2": "Cónyuge", "3": "Hijo"}

    edad = model.lookup("edad")
    assert edad is not None
    assert edad.label == "Edad en años cumplidos"
    assert edad.value_labels == {}


def test_read_codebook_csv_multi_row() -> None:
    csv_content = (
        "campo,descripcion,codigo,significado\n"
        "SEXO,Sexo del encuestado,1,Hombre\n"
        "SEXO,Sexo del encuestado,2,Mujer\n"
    )
    model = read_codebook(csv_content, file_name="diccionario.csv")
    assert len(model.entries) == 1
    sexo = model.lookup("SEXO")
    assert sexo is not None
    assert sexo.label == "Sexo del encuestado"
    assert sexo.value_labels == {"1": "Hombre", "2": "Mujer"}


def test_read_codebook_json() -> None:
    json_content = """
    {
      "P01_1": {
        "label": "Parentesco",
        "values": {"1": "Jefe", "2": "Hijo"}
      }
    }
    """
    model = read_codebook(json_content, file_name="diccionario.json")
    p01 = model.lookup("p01_1")
    assert p01 is not None
    assert p01.label == "Parentesco"
    assert p01.value_labels == {"1": "Jefe", "2": "Hijo"}


def test_read_codebook_text_syntax() -> None:
    text_content = (
        "P01_1 = Parentesco con el jefe del hogar [1=Jefe, 2=Cónyuge]\n"
        "EDAD: Edad del informante\n"
    )
    model = read_codebook(text_content, file_name="diccionario.txt")
    p01 = model.lookup("p01_1")
    assert p01 is not None
    assert p01.label == "Parentesco con el jefe del hogar"
    assert p01.value_labels == {"1": "Jefe", "2": "Cónyuge"}


def test_lookup_tolerance() -> None:
    entry = CodebookEntry(name="P01_1", label="Pregunta 1")
    model = CodebookModel(entries={"P01_1": entry})
    assert model.lookup("P01_1") is not None
    assert model.lookup("p01_1") is not None
    assert model.lookup("p01-1") is not None
    assert model.lookup("P01_1 ") is not None
    assert model.lookup("INEXISTENTE") is None


def test_resolve_codebook_skipped_without_codebook() -> None:
    canonical = _canonical_with_codebook_candidate()
    verdicts = _verdicts_initial()
    res = resolve_codebook(canonical, verdicts, codebook=None)
    assert res.skipped
    assert res.reason == "no_codebook"
    assert res.verdicts["v_001"].is_interpretable is False


def test_resolve_codebook_upgrades_variables() -> None:
    canonical = _canonical_with_codebook_candidate()
    verdicts = _verdicts_initial()

    codebook = CodebookModel(entries={
        "P01_1": CodebookEntry(
            name="P01_1",
            label="¿Cuál es su parentesco con el jefe del hogar?",
            value_labels={"1": "Jefe", "2": "Cónyuge", "3": "Hijo"},
        ),
        "EDAD": CodebookEntry(
            name="EDAD",
            label="Edad cumplida en años",
            value_labels={},
        ),
    })

    res = resolve_codebook(canonical, verdicts, codebook=codebook)
    assert not res.skipped
    assert len(res.resolutions) == 2
    assert res.resolutions["v_001"].resolved
    assert res.resolutions["v_002"].resolved

    # Las variables pasaron a ser interpretables
    assert res.verdicts["v_001"].is_interpretable is True
    assert res.verdicts["v_002"].is_interpretable is True

    # Se actualizó el texto de la pregunta para el LLM y visualización
    assert res.canonical.questions[0].text == "¿Cuál es su parentesco con el jefe del hogar?"
    assert res.canonical.questions[1].text == "Edad cumplida en años"

    # Se actualizó DetectedScale con las categorías de valores
    scale = res.canonical.variables[0].detected_scale
    assert scale is not None
    assert scale.kind == ScaleKind.CATEGORICAL
    assert scale.labels == ["Jefe", "Cónyuge", "Hijo"]


def _run() -> None:
    test_read_codebook_csv_inline()
    test_read_codebook_csv_multi_row()
    test_read_codebook_json()
    test_read_codebook_text_syntax()
    test_lookup_tolerance()
    test_resolve_codebook_skipped_without_codebook()
    test_resolve_codebook_upgrades_variables()
    print("OK - test_codebook_resolution: 7 tests passed")


if __name__ == "__main__":
    _run()
