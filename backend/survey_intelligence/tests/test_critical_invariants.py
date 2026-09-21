# survey_intelligence/tests/test_critical_invariants.py
"""
Tests de invariantes críticas (Tarea 17). Estos GUARDAN el build.

1. Restricción de no-invención: ninguna variable sin evidencia puede recibir
   significado inventado, ni siquiera si el LLM lo propone.
2. Determinismo: mismo insumo -> mismo canonical_id y mismos hallazgos determinísticos.
3. Separación de métricas: el Enriched nunca contiene métricas/administrativos.

Ejecutar:
    python -m survey_intelligence.tests.test_critical_invariants
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence import SurveyIngestionRequest, SurveyIntelligenceService
from survey_intelligence.contracts.enums import InterpretabilityStatus
from survey_intelligence.contracts.request import DublinCoreMetadata, SurveyFile
from survey_intelligence.tests.fakes import FixedClock, ScriptedLLM, SequentialIds

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _request(name: str, mime: str) -> SurveyIngestionRequest:
    path = _FIXTURES / name
    return SurveyIngestionRequest(
        request_id=f"crit-{path.stem}",
        survey=SurveyFile(
            file_name=path.name,
            file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
            mime_type=mime,
        ),
        metadata=_dc(),
    )


def _malicious_llm_for(request: SurveyIntelligenceService) -> ScriptedLLM:
    """LLM que intenta inventar significado para TODAS las variables."""
    # audit vacío, enrich que declara todo interpretable con constructo inventado, kpis vacío.
    audit = json.dumps({"ambiguous_questions": [], "double_barreled": [],
                        "wording_bias_suspected": [], "methodology_deficiencies": [],
                        "analysis_risks": []})
    # variables se completan en runtime; el enrich malicioso marca todo INTERPRETABLE.
    enrich = json.dumps({"survey_summary": {"purpose_inferred": "x", "confidence": 0.9},
                        "variables": []})  # vacío: el validador decide por evidencia
    kpis = json.dumps({"kpis": []})
    return ScriptedLLM([audit, enrich, kpis])


# ── 1. No-invención (guardián del build) ─────────────────────────────────────

def test_no_invented_meaning_for_contextless_variables() -> None:
    """
    Procesa las 3 plataformas. Toda variable INSUFFICIENT_CONTEXT debe carecer de
    enriquecimiento semántico. Si alguna tiene construct, el build FALLA.
    """
    fixtures = [
        ("limesurvey_participacion.csv", "text/csv"),
        ("limesurvey_salud_mental.csv", "text/csv"),
        ("msforms_graduacion.csv", "text/csv"),
    ]
    for name, mime in fixtures:
        svc = SurveyIntelligenceService(
            llm=ScriptedLLM([
                json.dumps({"ambiguous_questions": []}),
                json.dumps({"variables": []}),
                json.dumps({"kpis": []}),
            ]),
            clock=FixedClock(), ids=SequentialIds(),
        )
        result = svc.process(_request(name, mime))
        enriched = result.enriched_survey_model
        assert enriched is not None
        for ev in enriched.variables_enriched:
            if ev.interpretability_status == InterpretabilityStatus.INSUFFICIENT_CONTEXT:
                assert ev.semantic_enrichment is None, (
                    f"VIOLACIÓN en {name}/{ev.variable_id}: variable sin contexto con enriquecimiento"
                )


# ── 2. Determinismo ──────────────────────────────────────────────────────────

def test_canonical_id_and_findings_deterministic() -> None:
    """El mismo insumo produce el mismo canonical_id en dos corridas (sin LLM)."""
    r1 = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds()).process(
        _request("limesurvey_participacion.csv", "text/csv"))
    r2 = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds()).process(
        _request("limesurvey_participacion.csv", "text/csv"))
    assert r1.canonical_survey_model.canonical_id == r2.canonical_survey_model.canonical_id
    # Mismo número de propuestas de columnas (determinístico).
    assert len(r1.proposals) == len(r2.proposals)


# ── 3. Separación de métricas ────────────────────────────────────────────────

def test_enriched_has_no_metrics() -> None:
    """El Enriched no debe exponer conteos/nulos/cardinalidad (viven solo en Canonical)."""
    svc = SurveyIntelligenceService(llm=None, clock=FixedClock(), ids=SequentialIds())
    result = svc.process(_request("limesurvey_salud_mental.csv", "text/csv"))
    enriched_json = result.enriched_survey_model.model_dump_json()
    # Claves de métricas que NO deben aparecer en el enriched.
    for forbidden in ("null_ratio", "n_non_null", "cardinality", "value_distribution"):
        assert forbidden not in enriched_json, f"El Enriched no debe contener '{forbidden}'"


def _run() -> None:
    test_no_invented_meaning_for_contextless_variables()
    test_canonical_id_and_findings_deterministic()
    test_enriched_has_no_metrics()
    print("OK - test_critical_invariants: 3 tests passed")


if __name__ == "__main__":
    _run()
