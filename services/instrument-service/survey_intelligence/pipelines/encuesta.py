# survey_intelligence/pipelines/encuesta.py
"""
Estrategia de ENCUESTAS (vía tabular).

Encapsula lo que hoy diverge para encuestas dentro del facade, reusando los stages
existentes sin cambiar su lógica:

  build_canonical -> S1 ingesta (fatal) + S2 canonical (fatal) + S3 profiling (degradable)
  analyze         -> S8b análisis de resultados (v1 por columna / v2 por pregunta)

El resto (S4..S9) lo ejecuta el tronco común del facade.
"""
from __future__ import annotations

import time

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enums import StageStatus
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.pipeline.stages.s1_ingestion import IngestionError, ingest
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile
from survey_intelligence.pipeline.stages.s8b_results_analysis import (
    run_results_analysis,
    run_results_analysis_v2,
)
from survey_intelligence.pipelines.base import (
    CanonicalBuild,
    EmitFn,
    InstrumentAnalysis,
    InstrumentPipeline,
    PipelineDeps,
    PipelineError,
    ms_since,
)


class EncuestaPipeline(InstrumentPipeline):
    """Estrategia tabular para encuestas."""

    instrument_type = "encuesta"

    def build_canonical(
        self,
        request: SurveyIngestionRequest,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> CanonicalBuild:
        # S1 Ingesta (FATAL)
        t0 = time.perf_counter()
        try:
            ingestion = ingest(request)
            emit("ingestion", StageStatus.OK, ms_since(t0))
        except IngestionError as exc:
            emit("ingestion", StageStatus.FAILED, ms_since(t0), reason=str(exc))
            raise PipelineError(str(exc)) from exc

        # S2 Canonical (FATAL)
        t0 = time.perf_counter()
        try:
            canonical = build_canonical(
                ingestion, request.survey.file_name, ingestion.raw_table.sheet,
                question_grouping=request.options.question_grouping,
            )
            emit("canonical", StageStatus.OK, ms_since(t0))
        except Exception as exc:  # noqa: BLE001
            emit("canonical", StageStatus.FAILED, ms_since(t0), reason=str(exc))
            raise PipelineError(str(exc)) from exc

        # S3 Profiling (degradable)
        t0 = time.perf_counter()
        try:
            canonical = profile(canonical, ingestion.raw_table)
            emit("profiling", StageStatus.OK, ms_since(t0))
        except Exception as exc:  # noqa: BLE001
            emit("profiling", StageStatus.DEGRADED, ms_since(t0), reason=str(exc))

        return CanonicalBuild(canonical=canonical, ingestion=ingestion)

    def analyze(
        self,
        request: SurveyIngestionRequest,
        canonical: CanonicalSurveyModel,
        build: CanonicalBuild,
        spss_by_id: dict,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> InstrumentAnalysis:
        # S8b Análisis de resultados (LLM en lote, degradable)
        t0 = time.perf_counter()
        if request.options.question_grouping:
            # Vía v2: hallazgos por PREGUNTA (usa metrics/distribution de S3 v2).
            # Degradable: run_results_analysis_v2 maneja llm=None internamente.
            res_an = run_results_analysis_v2(
                canonical, deps.llm, request.options.llm_temperature,
                request.options.language_hint,
            )
            emit("results_analysis",
                 StageStatus.DEGRADED if res_an.degraded else StageStatus.OK, ms_since(t0))
            return InstrumentAnalysis(
                results_findings=res_an.findings, llm_calls=res_an.llm_calls,
            )
        if deps.llm is not None:
            # Vía v1 (actual): hallazgos por variable/columna.
            res_an = run_results_analysis(
                canonical, spss_by_id, deps.llm, request.options.llm_temperature,
                request.options.language_hint,
            )
            emit("results_analysis",
                 StageStatus.DEGRADED if res_an.degraded else StageStatus.OK, ms_since(t0))
            return InstrumentAnalysis(
                results_findings=res_an.findings, llm_calls=res_an.llm_calls,
            )
        emit("results_analysis", StageStatus.SKIPPED, ms_since(t0), reason="no_llm")
        return InstrumentAnalysis()
