# survey_intelligence/pipeline/stages/respondent_profiler.py
"""
Perfilador de respondentes (rediseño v2) — DETERMINISTA, SIN LLM.

Construye un RespondentProfile por respondente a partir de questions[].responses:
  - `respuestas`: relación pregunta→respuesta completa (todas).
  - `resumen`: frase por plantillas, SOLO desde preguntas estructuradas (§5.3).
  - `respuestas_abiertas`: texto íntegro de preguntas abiertas (§5.4), NO se resumen.
  - selección híbrida: automática por defecto; `salient_question_ids` opcional por encuesta.

Coste O(preguntas × respondentes), lineal → escala a decenas de miles. Cero LLM.
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import (
    CanonicalSurveyModel,
    OpenAnswer,
    RespondentProfile,
)
from survey_intelligence.contracts.enums import CanonicalQuestionType as QT
from survey_intelligence.engine.respondent_templates import (
    OPEN_TYPES,
    STRUCTURED_TYPES,
    assemble_summary,
    fragment_for,
)

# Cuántas preguntas estructuradas entran al resumen automático por defecto.
_AUTO_MAX_FRAGMENTS = 3


def build_respondent_profiles(
    canonical: CanonicalSurveyModel,
    salient_question_ids: list[str] | None = None,
) -> list[RespondentProfile]:
    """
    Genera los perfiles de respondente (determinista, sin LLM).

    Args:
        canonical: modelo canónico v2 (con questions[].responses pobladas).
        salient_question_ids: opción HÍBRIDA. Si se pasa, el resumen prioriza esas
            preguntas; si es None, selección automática (primeras N estructuradas).

    Returns:
        Lista de RespondentProfile, uno por respondent_id de respondents_index.
    """
    # Índice: respondent_id -> lista de (question, value, labels)
    por_respondente: dict[str, list[tuple]] = {rid: [] for rid in canonical.respondents_index}
    for q in canonical.questions:
        if q.type is None:
            continue
        for r in q.responses:
            if r.respondent_id in por_respondente:
                por_respondente[r.respondent_id].append((q, r.value, r.labels))

    # Orden de preguntas para el resumen (selección híbrida).
    q_order = {q.question_id: idx for idx, q in enumerate(canonical.questions)}
    salient = set(salient_question_ids or [])

    perfiles: list[RespondentProfile] = []
    for rid in canonical.respondents_index:
        items = por_respondente.get(rid, [])

        respuestas: list[dict] = []
        abiertas: list[OpenAnswer] = []
        # Candidatos a fragmentos del resumen: (prioridad, orden, fragmento)
        candidatos: list[tuple] = []

        for (q, value, labels) in items:
            # Registro completo de la respuesta (todas las preguntas).
            respuestas.append({
                "question_id": q.question_id,
                "pregunta": q.text,
                "value_labels": labels,
            })

            if q.type in OPEN_TYPES:
                # Abierta: texto íntegro, NO se resume.
                texto = labels if isinstance(labels, str) else (value if isinstance(value, str) else "")
                if texto:
                    abiertas.append(OpenAnswer(question_id=q.question_id, pregunta=q.text, texto=texto))
            elif q.type in STRUCTURED_TYPES:
                frag = fragment_for(q.type, q.text, labels)
                if frag:
                    # Prioridad 0 si es salient, 1 si no. Orden secundario = posición.
                    prioridad = 0 if q.question_id in salient else 1
                    candidatos.append((prioridad, q_order.get(q.question_id, 9999), frag))

        # Selección híbrida del resumen.
        candidatos.sort(key=lambda t: (t[0], t[1]))
        if salient:
            # Con config: usar todas las salient presentes (y nada más).
            fragmentos = [f for (p, _o, f) in candidatos if p == 0]
        else:
            # Automático: primeras N estructuradas por orden de aparición.
            fragmentos = [f for (_p, _o, f) in candidatos[:_AUTO_MAX_FRAGMENTS]]

        resumen = assemble_summary(fragmentos)

        # n_respondidas / n_omitidas respecto al total de preguntas v2.
        total_preguntas = sum(1 for q in canonical.questions if q.type is not None)
        n_resp = len(respuestas)
        fila_origen = int(rid[1:]) if rid.startswith("R") and rid[1:].isdigit() else None

        perfiles.append(RespondentProfile(
            respondent_id=rid,
            n_respondidas=n_resp,
            n_omitidas=max(0, total_preguntas - n_resp),
            respuestas=respuestas,
            resumen=resumen,
            respuestas_abiertas=abiertas,
            trazabilidad={"fila_origen": fila_origen} if fila_origen is not None else {},
        ))

    return perfiles
