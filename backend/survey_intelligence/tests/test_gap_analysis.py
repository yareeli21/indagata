# survey_intelligence/tests/test_gap_analysis.py
"""
Tests de la etapa S8 (gap analysis + improvement opportunities).

Verifica: la regla candidata del typo de escala, cobertura de scopes, status=proposed,
y que nada se persiste (el SIS solo emite).

Ejecutar:
    python -m survey_intelligence.tests.test_gap_analysis
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence.contracts.enriched import EnrichedSurveyModel
from survey_intelligence.contracts.enums import ImprovementScope, ImprovementStatus
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s4_context_sufficiency import assess_context
from survey_intelligence.pipeline.stages.s7_semantic_enrichment import run_enrichment
from survey_intelligence.pipeline.stages.s8_gap_analysis import run_gap_analysis
from survey_intelligence.tests.fakes import FixedClock, ScriptedLLM, SequentialIds

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _canonical_and_enriched():
    path = _FIXTURES / "limesurvey_participacion.csv"
    req = SurveyIngestionRequest(
        request_id="test-gap",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type="text/csv",
        ),
        metadata=_dc(),
    )
    ingestion = ingest(req)
    canonical = profile(build_canonical(ingestion, path.name, ingestion.raw_table.sheet), ingestion.raw_table)
    verdicts = assess_context(canonical)
    spss = {s.variable_id: s for s in build_spss_dictionary(canonical)}
    # LLM que marca una pregunta como suficiencia limitada, para forzar future_analysis.
    likert = next(v for v in canonical.variables if v.matrix_group)
    llm_resp = json.dumps({
        "survey_summary": {"purpose_inferred": "compromiso escolar", "confidence": 0.8},
        "variables": [{
            "variable_id": likert.variable_id, "interpretability_status": "INTERPRETABLE",
            "construct": "interés", "semantic_role": "predictor",
            "analytical_sufficiency": {"level": "limitada", "reason": "mide poco"},
        }],
    })
    enrich = run_enrichment(canonical, verdicts, spss, ScriptedLLM([llm_resp]))
    enriched = EnrichedSurveyModel(
        based_on_canonical_id=canonical.canonical_id,
        survey_summary=enrich.survey_summary,
        variables_enriched=enrich.variables,
    )
    return canonical, enriched


def test_typo_rule_candidate_present() -> None:
    """El typo 'En deesacuerdo' debe producir una validation_rule candidata."""
    canonical, enriched = _canonical_and_enriched()
    opps = run_gap_analysis(canonical, enriched, SequentialIds(), FixedClock())
    rules = [o for o in opps if o.scope == ImprovementScope.VALIDATION_RULE]
    assert rules
    assert rules[0].proposed_rule is not None
    assert rules[0].proposed_rule.rule_id_candidate == "scale_typo_normalization"


def test_all_proposed_status() -> None:
    """El SIS solo emite status=proposed."""
    canonical, enriched = _canonical_and_enriched()
    opps = run_gap_analysis(canonical, enriched, SequentialIds(), FixedClock())
    assert opps
    assert all(o.status == ImprovementStatus.PROPOSED for o in opps)


def test_multiple_scopes_covered() -> None:
    """Se cubren varios scopes (al menos validation_rule, future_analysis, pipeline)."""
    canonical, enriched = _canonical_and_enriched()
    opps = run_gap_analysis(canonical, enriched, SequentialIds(), FixedClock())
    scopes = {o.scope for o in opps}
    assert ImprovementScope.VALIDATION_RULE in scopes
    assert ImprovementScope.FUTURE_ANALYSIS in scopes
    assert ImprovementScope.PIPELINE in scopes


def test_ids_unique() -> None:
    canonical, enriched = _canonical_and_enriched()
    opps = run_gap_analysis(canonical, enriched, SequentialIds(), FixedClock())
    ids = [o.opportunity_id for o in opps]
    assert len(ids) == len(set(ids))


def _run() -> None:
    test_typo_rule_candidate_present()
    test_all_proposed_status()
    test_multiple_scopes_covered()
    test_ids_unique()
    print("OK - test_gap_analysis: 4 tests passed")


if __name__ == "__main__":
    _run()
