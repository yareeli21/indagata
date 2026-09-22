# survey_intelligence/pipeline/stages/s6_methodology_audit.py
"""
Etapa S6 — Auditoría metodológica (LLM, degradable).

Combina hallazgos DETERMINÍSTICOS (que no dependen del LLM: escalas inconsistentes,
columnas eliminables, longitudes) con hallazgos SEMÁNTICOS del LLM (ambigüedad,
doble pregunta, sesgo de redacción).

Si el LLM falla o devuelve JSON inválido (tras 1 reintento), la etapa se degrada:
conserva los hallazgos determinísticos y marca degraded=True.
"""
from __future__ import annotations

from dataclasses import dataclass

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enriched import (
    DroppableColumnsFinding,
    InconsistentScaleFinding,
    SurveyLevelFindings,
    WordingBiasFinding,
)
from survey_intelligence.contracts.enums import ColumnClass
from survey_intelligence.engine.parsing.robust_json import JsonParseError, parse_json_object
from survey_intelligence.engine.prompts.audit_prompt import build_audit_prompt
from survey_intelligence.ports.llm_port import LLMPort

# Umbrales de longitud (en palabras) para preguntas cortas/largas (determinístico).
_TOO_SHORT_WORDS = 3
_TOO_LONG_WORDS = 40


@dataclass
class AuditResult:
    findings: SurveyLevelFindings
    degraded: bool
    llm_calls: int


def _deterministic_findings(canonical: CanonicalSurveyModel) -> dict:
    """Hallazgos que NO dependen del LLM."""
    too_short: list[str] = []
    too_long: list[str] = []
    for q in canonical.questions:
        if q.length_words <= _TOO_SHORT_WORDS:
            too_short.append(q.question_id)
        elif q.length_words >= _TOO_LONG_WORDS:
            too_long.append(q.question_id)

    # Escalas inconsistentes: variables con anomalías de escala (typos).
    inconsistent: list[InconsistentScaleFinding] = []
    for v in canonical.variables:
        if v.detected_scale and v.detected_scale.anomalies:
            detail = ", ".join(
                f"'{a.value}' (x{a.occurrences}) ~ '{a.canonical_guess}'"
                for a in v.detected_scale.anomalies
            )
            inconsistent.append(InconsistentScaleFinding(group=[v.variable_id], detail=detail))

    # Columnas eliminables: metadatos de plataforma.
    droppable: list[DroppableColumnsFinding] = []
    platform_ids = [
        v.variable_id for v in canonical.variables
        if v.column_class == ColumnClass.PLATFORM_METADATA
    ]
    if platform_ids:
        droppable.append(DroppableColumnsFinding(
            variable_ids=platform_ids,
            reason="Metadatos de plataforma, no respuestas a preguntas.",
        ))

    return {
        "too_short_questions": too_short,
        "too_long_questions": too_long,
        "inconsistent_scales": inconsistent,
        "droppable_columns": droppable,
    }


def run_audit(canonical: CanonicalSurveyModel, llm: LLMPort, temperature: float = 0.1) -> AuditResult:
    """Ejecuta S6. Combina determinístico + LLM; degradable ante fallo del LLM."""
    det = _deterministic_findings(canonical)

    # Vista de preguntas para el LLM (solo texto, sin respuestas).
    questions_view = [
        {"question_id": q.question_id, "text": q.text, "n_items": len(q.variable_ids)}
        for q in canonical.questions
    ]

    ambiguous: list[str] = []
    double_barreled: list[str] = []
    wording_bias: list[WordingBiasFinding] = []
    methodology_deficiencies: list[str] = []
    analysis_risks: list[str] = []
    degraded = False
    llm_calls = 0

    system, user = build_audit_prompt(questions_view)
    raw = None
    for _attempt in range(2):  # 1 intento + 1 reintento
        try:
            llm_calls += 1
            raw = llm.complete_json(system_prompt=system, user_prompt=user, temperature=temperature)
            data = parse_json_object(raw)
            break
        except (RuntimeError, JsonParseError):
            data = None
            continue

    if data is None:
        degraded = True
    else:
        valid_qids = {q.question_id for q in canonical.questions}
        ambiguous = [q for q in data.get("ambiguous_questions", []) if q in valid_qids]
        double_barreled = [q for q in data.get("double_barreled", []) if q in valid_qids]
        for wb in data.get("wording_bias_suspected", []):
            if isinstance(wb, dict) and wb.get("question_id") in valid_qids:
                wording_bias.append(WordingBiasFinding(
                    question_id=wb["question_id"], detail=str(wb.get("detail", ""))
                ))
        methodology_deficiencies = [str(x) for x in data.get("methodology_deficiencies", [])]
        analysis_risks = [str(x) for x in data.get("analysis_risks", [])]

    findings = SurveyLevelFindings(
        ambiguous_questions=ambiguous,
        too_short_questions=det["too_short_questions"],
        too_long_questions=det["too_long_questions"],
        double_barreled=double_barreled,
        wording_bias_suspected=wording_bias,
        inconsistent_scales=det["inconsistent_scales"],
        droppable_columns=det["droppable_columns"],
        methodology_deficiencies=methodology_deficiencies,
        analysis_risks=analysis_risks,
    )
    return AuditResult(findings=findings, degraded=degraded, llm_calls=llm_calls)
