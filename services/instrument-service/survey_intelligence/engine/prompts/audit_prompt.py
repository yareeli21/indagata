# survey_intelligence/engine/prompts/audit_prompt.py
"""
Prompt de auditoría metodológica (S6).

Pide al LLM detectar problemas a nivel de instrumento a partir de las PREGUNTAS
(no de las respuestas de encuestados). Contrato JSON estricto y regla de no-invención.
"""
from __future__ import annotations

import json

_SYSTEM = """
Eres un metodólogo experto en encuestas. Analizas SOLO el texto de las preguntas de
un instrumento y detectas problemas metodológicos. No inventas: si no hay evidencia
de un problema, no lo reportes.

Responde EXCLUSIVAMENTE con un objeto JSON con esta forma (sin texto adicional):
{
  "ambiguous_questions": ["question_id", ...],
  "too_short_questions": ["question_id", ...],
  "too_long_questions": ["question_id", ...],
  "double_barreled": ["question_id", ...],
  "wording_bias_suspected": [{"question_id": "...", "detail": "..."}],
  "methodology_deficiencies": ["texto breve", ...],
  "analysis_risks": ["texto breve", ...]
}
Usa únicamente los question_id proporcionados. Si una categoría no aplica, deja []
""".strip()


def build_audit_prompt(questions: list[dict]) -> tuple[str, str]:
    """
    Construye (system_prompt, user_prompt) para la auditoría.

    Args:
        questions: lista de {"question_id", "text", "n_items"} (sin respuestas).

    Returns:
        (system_prompt, user_prompt).
    """
    payload = json.dumps({"questions": questions}, ensure_ascii=False, indent=2)
    user = (
        "Analiza estas preguntas y devuelve el JSON de hallazgos.\n\n"
        f"{payload}"
    )
    return _SYSTEM, user
