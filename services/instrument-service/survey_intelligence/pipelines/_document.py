# survey_intelligence/pipelines/_document.py
"""
Construcción del canónico por vía DOCUMENTAL (compartida por entrevista y prueba
estandarizada). Reusa el stage S2 documental sin cambiar su lógica.

El texto ya viene extraído por el host (request.survey.extracted_text): la vía
documental NO pasa por S1 (ingesta tabular) ni por S3 (profiling de escalas).
"""
from __future__ import annotations

import time

from survey_intelligence.contracts.enums import StageStatus
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.pipeline.stages.s2_document_builder import build_document_canonical
from survey_intelligence.pipelines.base import (
    CanonicalBuild,
    EmitFn,
    PipelineError,
    ms_since,
)


def build_document_canonical_phase(
    request: SurveyIngestionRequest,
    emit: EmitFn,
) -> CanonicalBuild:
    """
    Fase build_canonical común a entrevista y prueba estandarizada.

    Emite las mismas etapas/estados que la implementación previa del facade:
    'ingestion' (OK o FAILED si no hay texto), 'canonical' (OK/FAILED) y
    'profiling' (SKIPPED, vía documento).
    """
    t0 = time.perf_counter()
    text = request.survey.extracted_text or ""
    if not text.strip():
        emit("ingestion", StageStatus.FAILED, ms_since(t0), reason="documento sin texto")
        raise PipelineError("documento sin texto")
    emit("ingestion", StageStatus.OK, ms_since(t0))

    t0 = time.perf_counter()
    try:
        canonical = build_document_canonical(
            text, request.survey.file_name, request.options.instrument_type
        )
        emit("canonical", StageStatus.OK, ms_since(t0))
    except Exception as exc:  # noqa: BLE001
        emit("canonical", StageStatus.FAILED, ms_since(t0), reason=str(exc))
        raise PipelineError(str(exc)) from exc

    # La vía documento no perfila escalas tabulares.
    emit("profiling", StageStatus.SKIPPED, 0, reason="via_documento")

    return CanonicalBuild(canonical=canonical, document_text=text)
