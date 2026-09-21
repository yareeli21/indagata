# survey_intelligence/facade.py
"""
SurveyIntelligenceService — fachada del SIS (puerto de entrada único).

Orquesta las etapas S1..S9 en una sola llamada `process()`. Aplica degradación
graciosa: S1/S2 son fatales (si fallan -> status=failed con diagnóstico); S3..S9 son
degradables (si fallan, se conserva lo determinístico y se marca degraded).

Nunca lanza excepción al host: todo fallo se reporta en el SurveyIntelligenceResult.

Dependencias inyectadas por puertos (el host provee los adaptadores):
  llm, clock, ids, telemetry.
"""
from __future__ import annotations

import time

from survey_intelligence.contracts.enums import ResultStatus, StageStatus
from survey_intelligence.contracts.kpi import KpiInference
from survey_intelligence.contracts.results import ResultsFinding
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.contracts.result import (
    Diagnostics,
    StageDiagnostic,
    SurveyIntelligenceResult,
)
from survey_intelligence.engine.heuristics.column_proposals import build_column_proposals
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.pipeline.stages.s4_context_sufficiency import assess_context
from survey_intelligence.pipeline.stages.s5_codebook_resolution import resolve_codebook
from survey_intelligence.pipeline.stages.s6_methodology_audit import run_audit
from survey_intelligence.pipeline.stages.s7_semantic_enrichment import run_enrichment
from survey_intelligence.pipeline.stages.s7b_kpi_inference import run_kpi_inference
from survey_intelligence.pipeline.stages.s8_gap_analysis import run_gap_analysis
from survey_intelligence.pipeline.stages.s9_enriched_assembler import assemble_enriched
from survey_intelligence.contracts.interview import InterviewAnalysis
from survey_intelligence.pipelines import PipelineDeps, PipelineError, select_pipeline
from survey_intelligence.ports.clock_port import ClockPort, SystemClock
from survey_intelligence.ports.ids_port import IdGeneratorPort, UuidGenerator
from survey_intelligence.ports.llm_port import LLMPort
from survey_intelligence.ports.telemetry_port import NullTelemetry, TelemetryPort
from survey_intelligence.versioning import PIPELINE_VERSION, SCHEMA_VERSION


class SurveyIntelligenceService:
    """Fachada del SIS. Superficie pública: process()."""

    def __init__(
        self,
        llm: LLMPort | None = None,
        clock: ClockPort | None = None,
        ids: IdGeneratorPort | None = None,
        telemetry: TelemetryPort | None = None,
        kpi_catalog: list[dict] | None = None,
    ) -> None:
        self._llm = llm
        self._clock = clock or SystemClock()
        self._ids = ids or UuidGenerator()
        self._telemetry = telemetry or NullTelemetry()
        self._kpi_catalog = kpi_catalog or []

    def process(self, request: SurveyIngestionRequest) -> SurveyIntelligenceResult:
        """Ejecuta el pipeline completo y devuelve el resultado (nunca lanza al host)."""
        stages: list[StageDiagnostic] = []
        llm_calls = 0
        degraded = False

        def _emit(name: str, status: StageStatus, ms: int, reason: str | None = None) -> None:
            stages.append(StageDiagnostic(stage=name, status=status, ms=ms, reason=reason))
            self._telemetry.event(f"sis.stage.{name}", {
                "request_id": request.request_id, "status": status.value, "ms": ms,
            })

        # Estrategia por instrumento: encapsula las fases que divergen
        # (construcción del canónico y análisis específico). El tronco común
        # (S4..S9) permanece aquí. Un tipo desconocido cae a 'encuesta'.
        pipeline = select_pipeline(request.options.instrument_type)
        deps = PipelineDeps(llm=self._llm, clock=self._clock, ids=self._ids)

        # ── Construcción del canónico (S1/S2/S3 tabular, o S2 documental) ────
        try:
            build = pipeline.build_canonical(request, deps, _emit)
        except PipelineError:
            # La estrategia ya emitió el diagnóstico FAILED de la etapa fatal.
            return self._failed(request, stages)
        canonical = build.canonical
        # La vía tabular degradada en profiling se refleja en el diagnóstico;
        # el flag global se recalcula igual que antes según los estados emitidos.
        if any(s.stage == "profiling" and s.status == StageStatus.DEGRADED for s in stages):
            degraded = True

        # ── S4 Context sufficiency (determinística) ─────────────────────────
        t0 = time.perf_counter()
        verdicts = assess_context(canonical)
        _emit("context_sufficiency", StageStatus.OK, _ms(t0))

        # ── S5 Resolución determinística de Codebook (sin RAG) ──────────────
        t0 = time.perf_counter()
        cb_res = resolve_codebook(canonical, verdicts, request.codebook)
        canonical = cb_res.canonical
        verdicts = cb_res.verdicts
        if cb_res.skipped:
            _emit("codebook_resolution", StageStatus.SKIPPED, _ms(t0), reason=cb_res.reason)
        else:
            _emit("codebook_resolution", StageStatus.OK, _ms(t0))

        # SPSS determinístico (base para el enriquecimiento).
        spss_by_id = {s.variable_id: s for s in build_spss_dictionary(canonical)}

        # ── S6 Auditoría (LLM, degradable) ──────────────────────────────────
        t0 = time.perf_counter()
        if self._llm is not None and request.options.run_methodology_audit:
            audit = run_audit(canonical, self._llm, request.options.llm_temperature)
            llm_calls += audit.llm_calls
            degraded = degraded or audit.degraded
            _emit("methodology_audit",
                  StageStatus.DEGRADED if audit.degraded else StageStatus.OK, _ms(t0))
        else:
            audit = _empty_audit(canonical)
            _emit("methodology_audit", StageStatus.SKIPPED, _ms(t0), reason="no_llm")

        # ── S7 Enriquecimiento (LLM, degradable) ────────────────────────────
        t0 = time.perf_counter()
        if self._llm is not None:
            enrichment = run_enrichment(
                canonical, verdicts, spss_by_id, self._llm,
                request.options.llm_temperature, request.options.language_hint,
            )
            llm_calls += enrichment.llm_calls
            degraded = degraded or enrichment.degraded
            _emit("semantic_enrichment",
                  StageStatus.DEGRADED if enrichment.degraded else StageStatus.OK, _ms(t0))
        else:
            enrichment = run_enrichment(canonical, verdicts, spss_by_id, _NullLLM())
            degraded = True
            _emit("semantic_enrichment", StageStatus.SKIPPED, _ms(t0), reason="no_llm")

        # ── S7-KPI Inferencia de KPIs (LLM, degradable) ─────────────────────
        t0 = time.perf_counter()
        kpi_inferences: list[KpiInference] = []
        if self._llm is not None and self._kpi_catalog:
            purpose = enrichment.survey_summary.purpose_inferred if enrichment.survey_summary else None
            kpi_res = run_kpi_inference(canonical, purpose, self._kpi_catalog, self._llm,
                                        request.options.llm_temperature)
            llm_calls += kpi_res.llm_calls
            kpi_inferences = kpi_res.kpis
            _emit("kpi_inference",
                  StageStatus.DEGRADED if kpi_res.degraded else StageStatus.OK, _ms(t0))
        else:
            _emit("kpi_inference", StageStatus.SKIPPED, _ms(t0),
                  reason="no_llm" if self._llm is None else "no_catalog")

        # ── Análisis ESPECÍFICO del instrumento (delegado a la estrategia) ───
        # Encuesta: S8b (resultados por columna/pregunta). Entrevista: S10.
        # Prueba estandarizada: aún sin análisis propio. Nunca lanza: degrada.
        analysis = pipeline.analyze(request, canonical, build, spss_by_id, deps, _emit)
        llm_calls += analysis.llm_calls
        degraded = degraded or analysis.degraded
        results_findings: list[ResultsFinding] = analysis.results_findings
        interview_analysis: InterviewAnalysis | None = analysis.interview_analysis

        # ── S9 Ensamblado ───────────────────────────────────────────────────
        t0 = time.perf_counter()
        enriched = assemble_enriched(canonical, audit, enrichment)
        _emit("enriched_assembler", StageStatus.OK, _ms(t0))

        # ── S8 Gap analysis + propuestas ────────────────────────────────────
        t0 = time.perf_counter()
        proposals = build_column_proposals(canonical, self._ids)
        improvements = run_gap_analysis(canonical, enriched, self._ids, self._clock)
        _emit("gap_analysis", StageStatus.OK, _ms(t0))

        status = ResultStatus.COMPLETED_DEGRADED if degraded else ResultStatus.COMPLETED
        return SurveyIntelligenceResult(
            request_id=request.request_id,
            schema_version=SCHEMA_VERSION,
            pipeline_version=PIPELINE_VERSION,
            generated_at=self._clock.now().isoformat(),
            status=status,
            canonical_survey_model=canonical,
            enriched_survey_model=enriched,
            proposals=proposals,
            kpi_inferences=kpi_inferences,
            results_findings=results_findings,
            improvement_opportunities=improvements,
            interview_analysis=interview_analysis,
            diagnostics=Diagnostics(stages=stages, llm_calls=llm_calls, degraded=degraded),
        )

    def _failed(self, request: SurveyIngestionRequest, stages: list[StageDiagnostic]) -> SurveyIntelligenceResult:
        return SurveyIntelligenceResult(
            request_id=request.request_id,
            schema_version=SCHEMA_VERSION,
            pipeline_version=PIPELINE_VERSION,
            generated_at=self._clock.now().isoformat(),
            status=ResultStatus.FAILED,
            diagnostics=Diagnostics(stages=stages, llm_calls=0, degraded=True),
        )


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _empty_audit(canonical):
    """Auditoría solo determinística cuando no hay LLM (reusa S6 sin llamada)."""
    from survey_intelligence.pipeline.stages.s6_methodology_audit import run_audit
    return run_audit(canonical, _NullLLM())


class _NullLLM:
    """LLM nulo interno: siempre falla, forzando la ruta determinística/degradada."""

    def complete_json(self, **_kwargs) -> str:
        raise RuntimeError("no_llm")
