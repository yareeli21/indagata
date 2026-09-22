# survey_intelligence/pipeline/stages/s10_interview_analysis.py
"""
Etapa S10 — Análisis de entrevista (solo instrumentos 'entrevista').

Dos capas:
  1. Determinística (siempre): diarización -> participantes + turnos.
  2. Semántica (si hay LLM): temas, hallazgos, patrones, citas, resúmenes.

Produce un `InterviewAnalysis`. Nunca lanza: si el LLM falla o no está disponible,
devuelve la capa determinística con degraded=True. Es aditivo: no interfiere con el
resto del pipeline (que sigue produciendo canonical/enriched como hoy).
"""
from __future__ import annotations

from dataclasses import dataclass

from survey_intelligence.contracts.interview import InterviewAnalysis
from survey_intelligence.engine.nlp.diarization import diarize
from survey_intelligence.engine.nlp.interview_prompt import (
    build_interview_prompt,
    parse_interview_response,
)
from survey_intelligence.engine.parsing.robust_json import JsonParseError


@dataclass(frozen=True)
class InterviewAnalysisResult:
    analysis: InterviewAnalysis
    llm_calls: int
    degraded: bool


def run_interview_analysis(
    text: str,
    canonical_id: str,
    llm=None,
    temperature: float = 0.1,
    language_hint: str = "es",
) -> InterviewAnalysisResult:
    """
    Ejecuta el análisis de entrevista.

    Args:
        text:         texto de la entrevista (ya extraído por el host).
        canonical_id: id del Canonical documental (enlace de trazabilidad).
        llm:          adaptador LLMPort (opcional). Si None, solo capa determinística.
    """
    # 1) Capa determinística.
    participants, turns = diarize(text)

    base = dict(
        based_on_canonical_id=canonical_id,
        participants=participants,
        n_personas=len(participants),
        turns=turns,
    )

    # 2) Capa semántica (LLM), con 1 reintento implícito vía parser robusto.
    if llm is None or not turns:
        return InterviewAnalysisResult(
            analysis=InterviewAnalysis(**base, degraded=True),
            llm_calls=0,
            degraded=True,
        )

    valid_turn_ids = {t.turn_id for t in turns}
    valid_participant_ids = {p.participant_id for p in participants}
    system_prompt, user_prompt = build_interview_prompt(participants, turns, language_hint)

    try:
        raw = llm.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        semantica = parse_interview_response(raw, valid_turn_ids, valid_participant_ids)
        analysis = InterviewAnalysis(
            **base,
            themes=semantica["themes"],
            findings=semantica["findings"],
            patterns=semantica["patterns"],
            quotes=semantica["quotes"],
            participant_summaries=semantica["participant_summaries"],
            general_summary=semantica["general_summary"],
            degraded=False,
        )
        return InterviewAnalysisResult(analysis=analysis, llm_calls=1, degraded=False)
    except (JsonParseError, Exception):  # noqa: BLE001
        # Degradación segura: conservamos la capa determinística.
        return InterviewAnalysisResult(
            analysis=InterviewAnalysis(**base, degraded=True),
            llm_calls=1,
            degraded=True,
        )
