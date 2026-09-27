# survey_intelligence/engine/nlp/interview_prompt.py
"""
Prompt de análisis de entrevista + parseo robusto de la respuesta del LLM.

El LLM recibe los turnos ya diarizados (quién dice qué) y devuelve la capa semántica:
temas, hallazgos, patrones, citas y resúmenes. REGLA anti-invención: solo puede usar
lo que aparece en los turnos; cada tema/hallazgo/cita debe referenciar turn_ids reales.
"""
from __future__ import annotations

from survey_intelligence.contracts.interview import (
    DialogueTurn,
    Finding,
    Participant,
    ParticipantSummary,
    Pattern,
    Quote,
    Theme,
)
from survey_intelligence.engine.parsing.robust_json import JsonParseError, parse_json_object

_SYSTEM_PROMPT = (
    "Eres un analista cualitativo experto en entrevistas de investigación educativa. "
    "Analizas SOLO lo que aparece en los turnos provistos; no inventas información. "
    "Cada tema, hallazgo y cita debe referenciar turn_ids reales de la lista. "
    "Respondes EXCLUSIVAMENTE con un objeto JSON válido, sin texto adicional."
)

_ESQUEMA = """
Devuelve un objeto JSON con esta forma exacta:
{
  "temas": [
    {"titulo": "...", "descripcion": "...", "turn_ids": [1,2], "participant_ids": ["entrevistado_01"]}
  ],
  "hallazgos": [
    {"enunciado": "...", "evidence_turn_ids": [2], "participant_ids": ["entrevistado_01"], "confidence": 0.7}
  ],
  "patrones": [
    {"descripcion": "...", "evidence_turn_ids": [2,3]}
  ],
  "citas_relevantes": [
    {"text": "cita textual breve", "speaker_id": "entrevistado_01", "turn_id": 2, "theme_titulo": "..."}
  ],
  "resumen_por_participante": [
    {"participant_id": "entrevistado_01", "resumen": "...", "themes": ["..."]}
  ],
  "resumen_general": "..."
}
Reglas: usa turn_ids y participant_ids que existan en los datos. Si un campo no aplica, usa lista vacía.
"""


def build_interview_prompt(
    participants: list[Participant],
    turns: list[DialogueTurn],
    language_hint: str = "es",
) -> tuple[str, str]:
    """
    Construye (system_prompt, user_prompt) para el análisis de entrevista.

    El user_prompt incluye los participantes y los turnos numerados, para que el LLM
    ancle su análisis en evidencia trazable.
    """
    lineas_part = [f"- {p.participant_id} ({p.role})" for p in participants]
    lineas_turnos = [
        f"[{t.turn_id}] {t.speaker_id} ({t.turn_type}): {t.text}" for t in turns
    ]
    user_prompt = (
        f"Idioma: {language_hint}\n\n"
        f"PARTICIPANTES:\n" + "\n".join(lineas_part) + "\n\n"
        f"TURNOS DE DIÁLOGO:\n" + "\n".join(lineas_turnos) + "\n\n"
        f"{_ESQUEMA}"
    )
    return _SYSTEM_PROMPT, user_prompt


def system_prompt() -> str:
    return _SYSTEM_PROMPT


def parse_interview_response(
    raw: str,
    valid_turn_ids: set[int],
    valid_participant_ids: set[str],
) -> dict:
    """
    Parsea la respuesta del LLM y la mapea a los modelos semánticos de entrevista.

    Filtra referencias inválidas (turn_ids/participant_ids que no existan) para
    reforzar la trazabilidad y el anti-invención. Devuelve un dict con listas de
    modelos Pydantic listos para InterviewAnalysis.

    Raises:
        JsonParseError: si no se puede extraer JSON del texto.
    """
    obj = parse_json_object(raw)  # puede lanzar JsonParseError

    def _turns(ids) -> list[int]:
        if not isinstance(ids, list):
            return []
        return [int(i) for i in ids if isinstance(i, (int, float)) and int(i) in valid_turn_ids]

    def _parts(ids) -> list[str]:
        if not isinstance(ids, list):
            return []
        return [str(p) for p in ids if str(p) in valid_participant_ids]

    # Temas.
    themes: list[Theme] = []
    tema_titulo_to_id: dict[str, str] = {}
    for i, t in enumerate(obj.get("temas", []) or []):
        if not isinstance(t, dict):
            continue
        tid = f"t{i + 1}"
        titulo = str(t.get("titulo") or f"Tema {i + 1}")
        tema_titulo_to_id[titulo] = tid
        themes.append(Theme(
            theme_id=tid,
            titulo=titulo,
            descripcion=t.get("descripcion"),
            turn_ids=_turns(t.get("turn_ids")),
            participant_ids=_parts(t.get("participant_ids")),
        ))

    # Hallazgos.
    findings: list[Finding] = []
    for i, f in enumerate(obj.get("hallazgos", []) or []):
        if not isinstance(f, dict):
            continue
        conf = f.get("confidence")
        findings.append(Finding(
            finding_id=f"h{i + 1}",
            enunciado=str(f.get("enunciado") or ""),
            evidence_turn_ids=_turns(f.get("evidence_turn_ids")),
            participant_ids=_parts(f.get("participant_ids")),
            confidence=float(conf) if isinstance(conf, (int, float)) else None,
        ))

    # Patrones.
    patterns: list[Pattern] = []
    for i, p in enumerate(obj.get("patrones", []) or []):
        if not isinstance(p, dict):
            continue
        patterns.append(Pattern(
            pattern_id=f"p{i + 1}",
            descripcion=str(p.get("descripcion") or ""),
            evidence_turn_ids=_turns(p.get("evidence_turn_ids")),
        ))

    # Citas (solo si turno y hablante son válidos).
    quotes: list[Quote] = []
    for i, q in enumerate(obj.get("citas_relevantes", []) or []):
        if not isinstance(q, dict):
            continue
        tid = q.get("turn_id")
        sid = str(q.get("speaker_id") or "")
        if not isinstance(tid, (int, float)) or int(tid) not in valid_turn_ids:
            continue
        if sid not in valid_participant_ids:
            continue
        theme_id = tema_titulo_to_id.get(str(q.get("theme_titulo") or ""))
        quotes.append(Quote(
            quote_id=f"q{i + 1}",
            text=str(q.get("text") or ""),
            speaker_id=sid,
            turn_id=int(tid),
            theme_id=theme_id,
        ))

    # Resúmenes por participante.
    part_summaries: list[ParticipantSummary] = []
    for s in obj.get("resumen_por_participante", []) or []:
        if not isinstance(s, dict):
            continue
        pid = str(s.get("participant_id") or "")
        if pid not in valid_participant_ids:
            continue
        themes_list = s.get("themes") or []
        part_summaries.append(ParticipantSummary(
            participant_id=pid,
            resumen=str(s.get("resumen") or ""),
            themes=[str(x) for x in themes_list] if isinstance(themes_list, list) else [],
        ))

    return {
        "themes": themes,
        "findings": findings,
        "patterns": patterns,
        "quotes": quotes,
        "participant_summaries": part_summaries,
        "general_summary": obj.get("resumen_general"),
    }


__all__ = ["build_interview_prompt", "parse_interview_response", "system_prompt", "JsonParseError"]
