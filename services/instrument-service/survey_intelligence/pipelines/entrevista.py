# survey_intelligence/pipelines/entrevista.py
"""
Estrategia de ENTREVISTAS (vía documental + análisis de entrevista).

  build_canonical -> canónico documental compartido (texto -> segmentos free_text)
  analyze         -> S10 análisis de entrevista (diarización + temas/hallazgos LLM)

El resto (S4..S9) lo ejecuta el tronco común del facade. S10 es aditivo: no toca
el canónico ni el enriquecimiento, solo añade la cara de conocimiento de entrevista.
"""
from __future__ import annotations

import time

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enums import StageStatus
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.pipeline.stages.s10_interview_analysis import (
    run_interview_analysis,
)
from survey_intelligence.pipelines._document import build_document_canonical_phase
from survey_intelligence.pipelines.base import (
    CanonicalBuild,
    EmitFn,
    InstrumentAnalysis,
    InstrumentPipeline,
    PipelineDeps,
    ms_since,
)


class EntrevistaPipeline(InstrumentPipeline):
    """Estrategia documental para entrevistas."""

    instrument_type = "entrevista"

    def build_canonical(
        self,
        request: SurveyIngestionRequest,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> CanonicalBuild:
        return build_document_canonical_phase(request, emit)

    def analyze(
        self,
        request: SurveyIngestionRequest,
        canonical: CanonicalSurveyModel,
        build: CanonicalBuild,
        spss_by_id: dict,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> InstrumentAnalysis:
        # S10 Análisis de entrevista (aditivo; degradación segura interna).
        t0 = time.perf_counter()
        ia = run_interview_analysis(
            build.document_text, canonical.canonical_id, deps.llm,
            request.options.llm_temperature, request.options.language_hint,
        )
        emit("interview_analysis",
             StageStatus.DEGRADED if ia.degraded else StageStatus.OK, ms_since(t0))
        return InstrumentAnalysis(
            interview_analysis=ia.analysis, llm_calls=ia.llm_calls, degraded=ia.degraded,
        )
