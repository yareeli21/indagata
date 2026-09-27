# survey_intelligence/tests/test_llm_stages.py
"""
Tests de las etapas LLM (S6 auditoría, S7 enriquecimiento) y el parser JSON robusto.

Usa LLMPort falsos (ScriptedLLM, FailingLLM) para reproducibilidad total, sin Ollama.
Cubre el validador anti-invención y la degradación graciosa.

Ejecutar:
    python -m survey_intelligence.tests.test_llm_stages
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence.contracts.enums import InterpretabilityStatus
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.parsing.robust_json import (
    JsonParseError,
    parse_json_array,
    parse_json_object,
)
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s4_context_sufficiency import assess_context
from survey_intelligence.pipeline.stages.s6_methodology_audit import run_audit
from survey_intelligence.pipeline.stages.s7_semantic_enrichment import run_enrichment
from survey_intelligence.tests.fakes import FailingLLM, ScriptedLLM

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _pipeline_to_canonical(name: str, mime: str):
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
    return canonical


# ── Parser JSON robusto ──────────────────────────────────────────────────────

def test_parse_direct_object() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_markdown_fenced() -> None:
    raw = 'Aquí tienes:\n```json\n{"a": [1,2]}\n```\ngracias'
    assert parse_json_object(raw) == {"a": [1, 2]}


def test_parse_trailing_comma_and_semicolon() -> None:
    raw = '[{"tipo": "x", "n": 1;}, {"tipo": "y", "n": 2},]'
    data = parse_json_array(raw)
    assert len(data) == 2 and data[0]["n"] == 1


def test_parse_empty_raises() -> None:
    try:
        parse_json_object("")
        raise AssertionError("esperaba JsonParseError")
    except JsonParseError:
        pass


# ── S6 auditoría ─────────────────────────────────────────────────────────────

def test_audit_combines_deterministic_and_llm() -> None:
    """S6 debe incluir escalas inconsistentes (determinístico) + ambiguas (LLM)."""
    canonical = _pipeline_to_canonical("limesurvey_participacion.csv", "text/csv")
    q_ids = [q.question_id for q in canonical.questions]
    llm_response = json.dumps({
        "ambiguous_questions": [q_ids[0]],
        "double_barreled": [],
        "wording_bias_suspected": [],
        "methodology_deficiencies": ["falta ítem de control de aquiescencia"],
        "analysis_risks": [],
    })
    result = run_audit(canonical, ScriptedLLM([llm_response]))
    assert not result.degraded
    # Determinístico: el typo produce inconsistent_scales.
    assert len(result.findings.inconsistent_scales) >= 1
    # LLM: la pregunta ambigua.
    assert q_ids[0] in result.findings.ambiguous_questions
    assert result.findings.methodology_deficiencies


def test_audit_degrades_on_llm_failure() -> None:
    """Si el LLM falla, S6 conserva lo determinístico y marca degraded."""
    canonical = _pipeline_to_canonical("limesurvey_participacion.csv", "text/csv")
    result = run_audit(canonical, FailingLLM())
    assert result.degraded
    # Lo determinístico sigue presente pese al fallo del LLM.
    assert len(result.findings.inconsistent_scales) >= 1
    assert result.findings.ambiguous_questions == []


# ── S7 enriquecimiento + validador anti-invención ────────────────────────────

def _enrich(canonical, llm):
    verdicts = assess_context(canonical)
    spss = {s.variable_id: s for s in build_spss_dictionary(canonical)}
    return run_enrichment(canonical, verdicts, spss, llm)


def test_enrichment_interpretable_variable() -> None:
    """Una variable con evidencia recibe constructo y suficiencia analítica."""
    canonical = _pipeline_to_canonical("limesurvey_participacion.csv", "text/csv")
    # Tomar un id de variable interpretable (ítem Likert).
    likert = next(v for v in canonical.variables if v.matrix_group)
    llm_response = json.dumps({
        "survey_summary": {"purpose_inferred": "compromiso escolar", "confidence": 0.8},
        "variables": [{
            "variable_id": likert.variable_id,
            "interpretability_status": "INTERPRETABLE",
            "construct": "interés por el aprendizaje",
            "semantic_role": "predictor",
            "semantic_tags": ["interés"],
            "analytical_sufficiency": {
                "level": "adecuada", "reason": "ítem claro",
                "enrichment_suggestion": {"type": "clarify_scope",
                                          "proposed_item": "precisar alcance", "rationale": "más valor"}
            }
        }]
    })
    result = _enrich(canonical, ScriptedLLM([llm_response]))
    by_id = {e.variable_id: e for e in result.variables}
    e = by_id[likert.variable_id]
    assert e.interpretability_status == InterpretabilityStatus.INTERPRETABLE
    assert e.semantic_enrichment is not None
    assert e.semantic_enrichment.construct_ == "interés por el aprendizaje"
    assert e.semantic_enrichment.analytical_sufficiency.level.value == "adecuada"
    assert result.survey_summary.purpose_inferred == "compromiso escolar"


def test_validator_downgrades_invented_meaning() -> None:
    """
    Si el LLM inventa significado para una variable SIN evidencia, el validador la
    degrada a INSUFFICIENT_CONTEXT. Se simula con una variable canónica sin evidencia.
    """
    from survey_intelligence.contracts.canonical import (
        CanonicalSurveyModel, CanonicalVariable, Dimensions, SourceInfo,
    )
    from survey_intelligence.contracts.enums import ColumnClass, DataType

    var = CanonicalVariable(
        variable_id="v_001", raw_header="q17", normalized_name="q17", position=1,
        column_class=ColumnClass.QUESTION, inferred_data_type=DataType.NUMERIC,
    )
    canonical = CanonicalSurveyModel(
        canonical_id="sha256:test",
        source=SourceInfo(platform_guess=None, file_name="x.csv"),
        dimensions=Dimensions(n_rows=5, n_columns=1),
        variables=[var],
    )
    # El LLM MIENTE: dice que q17 es interpretable con un constructo inventado.
    llm_response = json.dumps({
        "variables": [{
            "variable_id": "v_001",
            "interpretability_status": "INTERPRETABLE",
            "construct": "satisfacción inventada",
            "semantic_role": "outcome",
        }]
    })
    result = _enrich(canonical, ScriptedLLM([llm_response]))
    e = result.variables[0]
    # El validador debe imponer INSUFFICIENT_CONTEXT pese a la invención del LLM.
    assert e.interpretability_status == InterpretabilityStatus.INSUFFICIENT_CONTEXT
    assert e.semantic_enrichment is None
    assert e.why_not_interpretable is not None


def test_enrichment_degrades_on_llm_failure() -> None:
    """Si el LLM falla, las variables quedan con SPSS pero sin cara semántica."""
    canonical = _pipeline_to_canonical("limesurvey_salud_mental.csv", "text/csv")
    result = _enrich(canonical, FailingLLM())
    assert result.degraded
    # Las interpretables no tienen enriquecimiento semántico, pero sí SPSS.
    interpretable = [e for e in result.variables
                     if e.interpretability_status == InterpretabilityStatus.INTERPRETABLE]
    assert interpretable
    assert all(e.spss_metadata is not None for e in interpretable)


def _run() -> None:
    test_parse_direct_object()
    test_parse_markdown_fenced()
    test_parse_trailing_comma_and_semicolon()
    test_parse_empty_raises()
    test_audit_combines_deterministic_and_llm()
    test_audit_degrades_on_llm_failure()
    test_enrichment_interpretable_variable()
    test_validator_downgrades_invented_meaning()
    test_enrichment_degrades_on_llm_failure()
    print("OK - test_llm_stages: 9 tests passed")


if __name__ == "__main__":
    _run()
