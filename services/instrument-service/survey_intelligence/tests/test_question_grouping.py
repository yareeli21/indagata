# survey_intelligence/tests/test_question_grouping.py
"""
Tests de los motores del rediseño v2 (Fase 2): matrix_parser extendido,
question_typing y question_grouping. Sobre fixtures reales + casos sintéticos
que reproducen los comportamientos de plataformas.md.

Ejecutar:
    python -m survey_intelligence.tests.test_question_grouping
"""
from __future__ import annotations

import csv
import pathlib

import base64

from survey_intelligence.contracts.enums import CanonicalQuestionType as QT
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.profiling.matrix_parser import parse_header, parse_matrix
from survey_intelligence.engine.question_grouping import group_questions
from survey_intelligence.engine.question_typing import (
    is_yes_no_column,
    type_multi_column,
    type_single_column,
)
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read_csv(name: str) -> tuple[list[str], list[list[str]]]:
    with open(_FIXTURES / name, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def _ingestion(name: str, mime: str = "text/csv"):
    path = _FIXTURES / name
    req = SurveyIngestionRequest(
        request_id=f"t-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type=mime,
        ),
        metadata=DublinCoreMetadata(
            dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
            dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
            dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
        ),
    )
    return ingest(req)


# ── matrix_parser extendido (N niveles + Rank/Scale) ─────────────────────────

def test_parse_header_single_bracket() -> None:
    hp = parse_header("¿Cómo te enteraste…? [Página web institucional]")
    assert hp.stem.startswith("¿Cómo te enteraste")
    assert hp.segments == ("Página web institucional",)
    assert hp.n_brackets == 1


def test_parse_header_double_bracket() -> None:
    hp = parse_header("opina de estos temas [recibir info][Scale 1]")
    assert hp.stem == "opina de estos temas"
    assert hp.segments == ("recibir info",)   # 'Scale 1' se extrae como eje
    assert hp.scale == 1


def test_parse_header_rank() -> None:
    hp = parse_header("actividad que mayor estrés te causa [Rank 2]")
    assert hp.rank == 2
    assert hp.segments == ()   # Rank no es un ítem


def test_parse_header_no_bracket_is_stem() -> None:
    hp = parse_header("¿Has considerado abandonar tus estudios?")
    assert hp.n_brackets == 0 and hp.rank is None and hp.scale is None
    assert hp.stem == "¿Has considerado abandonar tus estudios?"


def test_parse_matrix_still_works() -> None:
    # El parser v1 no cambió (compatibilidad).
    p = parse_matrix("Evalúa los aspectos. [Confidencialidad]")
    assert p.is_matrix and p.item == "Confidencialidad"


# ── question_typing (señales de valores) ─────────────────────────────────────

def test_yes_no_column_detection() -> None:
    assert is_yes_no_column(["yes", "no", "no", "yes", ""])
    assert not is_yes_no_column(["Buena", "Mala", "Regular"])


def test_type_single_numeric_low_card_is_likert() -> None:
    v = type_single_column("califica del 1 al 5", ["1", "2", "3", "4", "5", "3", "2"])
    assert v.type in (QT.LIKERT, QT.NUMERICA)


def test_type_single_long_text() -> None:
    largo = ["Considero que la institución debería mejorar sus horarios y contratar más personal de apoyo psicológico disponible."] * 3
    v = type_single_column("¿Qué mejoras propones?", largo)
    assert v.type == QT.TEXTO_LARGO


def test_type_multi_yes_no_is_opcion_multiple() -> None:
    cols = [["yes", "no", "yes"], ["no", "no", "yes"], ["yes", "yes", "no"]]
    v = type_multi_column("¿Cómo te enteraste?", cols)
    assert v.type == QT.OPCION_MULTIPLE and v.confidence >= 0.8


def test_type_multi_scale_is_likert_or_matriz() -> None:
    cols = [["Buena", "Mala", "Regular"], ["Regular", "Buena", "Buena"]]
    v = type_multi_column("Evalúa aspectos", cols)
    assert v.type in (QT.LIKERT, QT.MATRIZ)


# ── FUERA DE ALCANCE: ranking, archivo y doble corchete degradan a tipo genérico ──

def test_ranking_out_of_scope_falls_back() -> None:
    """[Rank k] no es un tipo dedicado; degrada a opción múltiple con confidence baja."""
    cols = [["Apoyo docente", ""], ["", "Carga académica"]]
    v = type_multi_column("Ordena los factores", cols, has_rank=True)
    assert v.type == QT.OPCION_MULTIPLE
    assert v.confidence <= 0.5 and "out_of_scope" in v.reason


def test_dual_scale_out_of_scope_falls_back() -> None:
    """Doble corchete [Scale k] degrada a matriz genérica con confidence baja."""
    cols = [["apruebo", "rechazo"], ["neutral", "apruebo"]]
    v = type_multi_column("opina de estos temas", cols, has_scale_axis=True)
    assert v.type == QT.MATRIZ
    assert v.confidence <= 0.5 and "out_of_scope" in v.reason


def test_file_out_of_scope_is_text() -> None:
    """Carga de archivo (JSON en celda) degrada a texto, sin tipo dedicado."""
    v = type_single_column("sube tu credencial", ['[{"filename":"fu_x","name":"cred.png","ext":"png"}]'])
    assert v.type == QT.TEXTO_CORTO and "out_of_scope" in v.reason


# ── question_grouping sobre fixture LimeSurvey (el caso reportado) ───────────

def test_grouping_reconstructs_multiple_choice() -> None:
    """
    El caso reportado: '¿Cómo te enteraste…? [Página web]', '[Redes sociales]', ...
    debe reconstruirse como UNA pregunta de opción múltiple, no N preguntas.
    """
    headers, rows = _read_csv("limesurvey_salud_mental.csv")
    admin = {
        "Response ID", "Date submitted", "Last page", "Start language",
        "Seed", "Date started", "Date last action",
    }
    grupos = group_questions(headers, rows, admin_headers=admin)

    # Buscar la pregunta "¿Cómo te enteraste…?"
    enterarse = [g for g in grupos if g.stem.startswith("¿Cómo te enteraste")]
    assert len(enterarse) == 1, "la opción múltiple debe ser UNA sola pregunta"
    g = enterarse[0]
    assert g.type == QT.OPCION_MULTIPLE, f"esperado opcion_multiple, got {g.type}"
    assert g.is_multi_column
    # Las opciones (labels) deben venir de los corchetes.
    assert "Página web institucional" in g.labels
    assert "Profesores" in g.labels
    # Trazabilidad: varias columnas de origen.
    assert len(g.source_columns) >= 6


def test_grouping_preserves_simple_questions() -> None:
    """Una pregunta simple (1 columna, sin corchetes) sigue siendo una pregunta."""
    headers, rows = _read_csv("limesurvey_salud_mental.csv")
    admin = {"Response ID", "Date submitted", "Last page", "Start language",
             "Seed", "Date started", "Date last action"}
    grupos = group_questions(headers, rows, admin_headers=admin)
    simples = [g for g in grupos if g.stem.startswith("¿Sabías que la institución")]
    assert len(simples) == 1 and not simples[0].is_multi_column


def test_grouping_array_is_grouped() -> None:
    """El array 'Evalúa los siguientes aspectos… [x]' se agrupa en una pregunta."""
    headers, rows = _read_csv("limesurvey_salud_mental.csv")
    admin = {"Response ID", "Date submitted", "Last page", "Start language",
             "Seed", "Date started", "Date last action"}
    grupos = group_questions(headers, rows, admin_headers=admin)
    evalua = [g for g in grupos if g.stem.startswith("Evalúa los siguientes aspectos del servicio")]
    assert len(evalua) == 1 and evalua[0].is_multi_column
    assert len(evalua[0].source_columns) >= 5


# ── Fase 3: build_canonical con la bandera question_grouping ─────────────────

def test_flag_off_is_v1_behavior() -> None:
    """Con la bandera OFF, el canónico es idéntico al actual (v1): sin campos v2."""
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "limesurvey_salud_mental.csv", ing.raw_table.sheet)  # default off
    assert c.canonical_id.startswith("sha256:") and not c.canonical_id.startswith("sha256:v2:")
    assert c.respondents_index == []
    # En v1, las questions no llevan type v2.
    assert all(q.type is None for q in c.questions)


def test_flag_on_reconstructs_multiple_choice() -> None:
    """Con la bandera ON, la opción múltiple se reconstruye como UNA pregunta v2."""
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "limesurvey_salud_mental.csv", ing.raw_table.sheet, question_grouping=True)

    assert c.canonical_id.startswith("sha256:v2:")
    assert len(c.respondents_index) == c.dimensions.n_rows

    enterarse = [q for q in c.questions if q.text.startswith("¿Cómo te enteraste")]
    assert len(enterarse) == 1, "la opción múltiple debe ser UNA pregunta"
    q = enterarse[0]
    assert q.type == QT.OPCION_MULTIPLE
    assert len(q.options) >= 6                      # opciones reconstruidas
    assert len(q.source_columns) >= 6               # trazabilidad a columnas
    assert q.text == "¿Cómo te enteraste de los servicios de salud mental de la institución?"


def test_flag_on_keeps_compat_variables() -> None:
    """Con la bandera ON, variables[] (compatibilidad para S3..S9/SAV) se conserva intacta."""
    ing = _ingestion("limesurvey_salud_mental.csv")
    c_off = build_canonical(ing, "x.csv", ing.raw_table.sheet)
    c_on = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    # Mismas variables (columna) en ambos modos: la capa de compat no cambia.
    assert [v.variable_id for v in c_on.variables] == [v.variable_id for v in c_off.variables]
    assert [v.normalized_name for v in c_on.variables] == [v.normalized_name for v in c_off.variables]
    # Y las variable_ids de una pregunta v2 apuntan a variables reales.
    all_vids = {v.variable_id for v in c_on.variables}
    for q in c_on.questions:
        for vid in q.variable_ids:
            assert vid in all_vids


# ── Fase 4: profiling por pregunta (S3 sobre canónico v2) ────────────────────

def test_v2_profiling_multiple_choice_distribution() -> None:
    """Con la bandera on, S3 puebla metrics/distribution por opción en la opción múltiple."""
    from survey_intelligence.pipeline.stages.s3_data_profiler import profile
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    c = profile(c, ing.raw_table)

    q = next(q for q in c.questions if q.text.startswith("¿Cómo te enteraste"))
    assert q.metrics.get("n_respuestas") is not None
    # Una barra de distribución por opción, con option_id enlazado.
    assert len(q.distribution) == len(q.options) >= 6
    assert all(b.option_id is not None for b in q.distribution)
    assert all(0 <= b.percentage <= 100 for b in q.distribution)


def test_v2_profiling_keeps_variables_distribution() -> None:
    """El profiling v2 NO altera variables[].value_distribution (compatibilidad S3..S9/SAV)."""
    from survey_intelligence.pipeline.stages.s3_data_profiler import profile
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    c = profile(c, ing.raw_table)
    # Todas las variables mantienen su value_distribution como en el flujo actual.
    assert all(v.value_distribution is not None for v in c.variables)


# ── Fase 6: por_pregunta (S8b v2) con LLM y degradación ──────────────────────

class _FakeResultsLLM:
    """LLM fake: devuelve interpretación por pregunta para el batch de S8b v2."""
    def __init__(self, qids):
        self._qids = qids
    def complete_json(self, **kwargs) -> str:
        import json
        return json.dumps({
            "findings": [
                {"variable_id": qid, "interpretation": "interp",
                 "insights": ["insight"], "numeric_evidence": "ev", "semantic_text": "st"}
                for qid in self._qids
            ]
        })


def _v2_profiled():
    from survey_intelligence.pipeline.stages.s3_data_profiler import profile
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    return profile(c, ing.raw_table)


def test_results_v2_with_llm_produces_findings_per_question() -> None:
    from survey_intelligence.pipeline.stages.s8b_results_analysis import run_results_analysis_v2
    c = _v2_profiled()
    qids = [q.question_id for q in c.questions if q.type is not None and q.type.value != "no_dato"]
    res = run_results_analysis_v2(c, _FakeResultsLLM(qids))
    assert not res.degraded and res.llm_calls == 1
    # Un finding por pregunta con datos; el id es el question_id.
    assert len(res.findings) == len(qids)
    assert all(f.variable_id in qids for f in res.findings)
    assert any(f.interpretation == "interp" for f in res.findings)


def test_results_v2_degrades_without_llm() -> None:
    from survey_intelligence.pipeline.stages.s8b_results_analysis import run_results_analysis_v2
    c = _v2_profiled()
    res = run_results_analysis_v2(c, None)   # sin LLM
    assert res.degraded and res.llm_calls == 0
    # Conserva métricas/distribución + texto semántico determinístico de respaldo.
    assert res.findings and all(f.semantic_text for f in res.findings)
    assert all(f.interpretation is None for f in res.findings)


# ── Fase 5: responses[] pobladas + perfilador determinista de respondentes ───

def test_v2_responses_populated_multiple_choice() -> None:
    """S2 v2 puebla responses[] por respondente en la opción múltiple."""
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    q = next(q for q in c.questions if q.text.startswith("¿Cómo te enteraste"))
    # Debe haber respuestas y ser listas de labels (opción múltiple).
    assert len(q.responses) >= 1
    r = q.responses[0]
    assert isinstance(r.labels, list)


def test_respondent_profiles_deterministic_and_open_preserved() -> None:
    """Perfiles deterministas (sin LLM): resumen reproducible + abiertas íntegras."""
    from survey_intelligence.pipeline.stages.s3_data_profiler import profile
    from survey_intelligence.pipeline.stages.respondent_profiler import build_respondent_profiles
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    c = profile(c, ing.raw_table)

    p1 = build_respondent_profiles(c)
    p2 = build_respondent_profiles(c)
    # Reproducible: mismo input → mismos resúmenes exactos.
    assert [x.resumen for x in p1] == [x.resumen for x in p2]
    # Un perfil por respondente del índice.
    assert len(p1) == len(c.respondents_index)
    # Al menos un perfil tiene resumen no vacío empezando por la plantilla fija.
    assert any(x.resumen and x.resumen.startswith("El respondente") for x in p1)

    # Preguntas abiertas preservadas íntegras (texto largo del fixture).
    con_abiertas = [x for x in p1 if x.respuestas_abiertas]
    if con_abiertas:  # el fixture tiene preguntas de texto largo
        oa = con_abiertas[0].respuestas_abiertas[0]
        assert oa.texto and oa.pregunta and oa.question_id


def test_respondent_profile_salient_selection() -> None:
    """La selección híbrida respeta salient_question_ids cuando se provee."""
    from survey_intelligence.pipeline.stages.respondent_profiler import build_respondent_profiles
    ing = _ingestion("limesurvey_salud_mental.csv")
    c = build_canonical(ing, "x.csv", ing.raw_table.sheet, question_grouping=True)
    # Elegir una pregunta estructurada como salient.
    estructurada = next(
        q for q in c.questions
        if q.type is not None and q.type.value in ("opcion_unica", "likert", "opcion_multiple")
    )
    perfiles = build_respondent_profiles(c, salient_question_ids=[estructurada.question_id])
    # No lanza y devuelve un perfil por respondente.
    assert len(perfiles) == len(c.respondents_index)


def _run() -> None:
    test_parse_header_single_bracket()
    test_parse_header_double_bracket()
    test_parse_header_rank()
    test_parse_header_no_bracket_is_stem()
    test_parse_matrix_still_works()
    test_yes_no_column_detection()
    test_type_single_numeric_low_card_is_likert()
    test_type_single_long_text()
    test_type_multi_yes_no_is_opcion_multiple()
    test_type_multi_scale_is_likert_or_matriz()
    test_ranking_out_of_scope_falls_back()
    test_dual_scale_out_of_scope_falls_back()
    test_file_out_of_scope_is_text()
    test_grouping_reconstructs_multiple_choice()
    test_grouping_preserves_simple_questions()
    test_grouping_array_is_grouped()
    test_flag_off_is_v1_behavior()
    test_flag_on_reconstructs_multiple_choice()
    test_flag_on_keeps_compat_variables()
    test_v2_profiling_multiple_choice_distribution()
    test_v2_profiling_keeps_variables_distribution()
    test_v2_responses_populated_multiple_choice()
    test_respondent_profiles_deterministic_and_open_preserved()
    test_respondent_profile_salient_selection()
    test_results_v2_with_llm_produces_findings_per_question()
    test_results_v2_degrades_without_llm()
    print("OK - test_question_grouping: 26 tests passed")


if __name__ == "__main__":
    _run()
