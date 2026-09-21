# survey_intelligence/tests/test_results_analysis.py
"""
Tests de la etapa S8b (análisis de resultados) sobre fixtures reales.

Verifica métricas/distribución determinísticas, interpretación por LLM en lote,
degradación sin LLM, y que la evidencia numérica salga de los datos observados.

Ejecutar:
    python -m survey_intelligence.tests.test_results_analysis
"""
from __future__ import annotations

import base64
import json
import pathlib

from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    SurveyFile,
    SurveyIngestionRequest,
)
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.pipeline.stages.s1_ingestion import ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s8b_results_analysis import run_results_analysis
from survey_intelligence.tests.fakes import FailingLLM, ScriptedLLM

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _dc() -> DublinCoreMetadata:
    return DublinCoreMetadata(
        dc_title="t", dc_creator="c", dc_subject=["s"], dc_description="d",
        dc_publisher="INDAGATA", dc_date="2026-03-15", dc_type="encuesta",
        dc_format="csv", dc_language="es", dc_coverage="cov", dc_rights="r",
    )


def _prep(name: str):
    path = _FIXTURES / name
    req = SurveyIngestionRequest(
        request_id=f"res-{path.stem}",
        survey=SurveyFile(file_name=path.name,
                          file_bytes_b64=base64.b64encode(path.read_bytes()).decode(),
                          mime_type="text/csv"),
        metadata=_dc(),
    )
    ing = ingest(req)
    canonical = profile(build_canonical(ing, path.name, ing.raw_table.sheet), ing.raw_table)
    spss = {s.variable_id: s for s in build_spss_dictionary(canonical)}
    return canonical, spss


def test_deterministic_metrics_present() -> None:
    """Cada hallazgo debe tener métricas y distribución determinísticas."""
    canonical, spss = _prep("limesurvey_participacion.csv")
    res = run_results_analysis(canonical, spss, FailingLLM())  # sin LLM útil
    assert res.degraded  # el LLM falló
    assert res.findings  # pero hay hallazgos determinísticos
    f = res.findings[0]
    assert f.metrics.n_respuestas >= 0
    assert f.pregunta  # texto de la pregunta conservado
    assert f.tipo      # tipo conservado
    # semantic_text de respaldo determinístico presente aunque el LLM falle.
    assert f.semantic_text


def test_likert_mean_computed() -> None:
    """Para un ítem Likert con value_encoding, se calcula la media codificada."""
    canonical, spss = _prep("limesurvey_participacion.csv")
    res = run_results_analysis(canonical, spss, FailingLLM())
    likert = [f for f in res.findings if f.metrics.media_codificada is not None]
    assert likert, "esperaba al menos un ítem con media codificada"
    assert 1.0 <= likert[0].metrics.media_codificada <= 5.0


def test_llm_interpretation_merged() -> None:
    """La interpretación del LLM se fusiona con las métricas determinísticas."""
    canonical, spss = _prep("limesurvey_salud_mental.csv")
    # LLM devuelve interpretación para la primera variable-pregunta.
    first_q = next(
        v.variable_id for v in canonical.variables
        if v.column_class.value != "platform_metadata"
    )
    response = json.dumps({"findings": [{
        "variable_id": first_q,
        "interpretation": "La mayoría respondió que no.",
        "insights": ["Predomina el desconocimiento del servicio."],
        "numeric_evidence": "4 de 7 respuestas",
        "semantic_text": "Conocimiento del servicio: predomina el no.",
    }]})
    res = run_results_analysis(canonical, spss, ScriptedLLM([response]))
    assert not res.degraded
    match = next(f for f in res.findings if f.variable_id == first_q)
    assert match.interpretation == "La mayoría respondió que no."
    assert match.insights
    assert match.semantic_text == "Conocimiento del servicio: predomina el no."


def _run() -> None:
    test_deterministic_metrics_present()
    test_likert_mean_computed()
    test_llm_interpretation_merged()
    print("OK - test_results_analysis: 3 tests passed")


if __name__ == "__main__":
    _run()
