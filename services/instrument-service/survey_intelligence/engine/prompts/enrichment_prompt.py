# survey_intelligence/engine/prompts/enrichment_prompt.py
"""
Prompt de enriquecimiento semántico (S7).

Pide al LLM, por variable interpretable: constructo, rol semántico, tags, y la
suficiencia analítica con su sugerencia de enriquecimiento. Regla dura de no-invención:
si una variable no tiene evidencia suficiente, debe devolverla como INSUFFICIENT_CONTEXT.
"""
from __future__ import annotations

import json

_SYSTEM = """
Eres un experto en metodología de encuestas y análisis semántico. Para cada variable
propones enriquecimiento SOLO si hay evidencia (texto de pregunta, ítem de matriz o
etiquetas). Si no hay evidencia suficiente para interpretar una variable, la marcas
como INSUFFICIENT_CONTEXT y NO inventas su significado.

Responde EXCLUSIVAMENTE con un objeto JSON (sin texto adicional):
{
  "survey_summary": {"purpose_inferred": "...", "confidence": 0.0-1.0},
  "variables": [
    {
      "variable_id": "...",
      "interpretability_status": "INTERPRETABLE" | "INSUFFICIENT_CONTEXT",
      "construct": "...",
      "semantic_role": "predictor" | "outcome" | "descriptor" | "control",
      "semantic_tags": ["..."],
      "analytical_sufficiency": {
        "level": "rica" | "adecuada" | "limitada" | "pobre",
        "reason": "...",
        "what_it_could_reveal": "...",
        "enrichment_suggestion": {
          "type": "add_followup_open_ended" | "add_reason_field" | "split_double_barreled" | "clarify_scope" | "add_missing_dimension",
          "proposed_item": "...",
          "rationale": "..."
        }
      }
    }
  ]
}
Para variables INSUFFICIENT_CONTEXT, omite construct/semantic_role y no propongas
enriquecimiento. Usa solo los variable_id proporcionados.
""".strip()


def build_enrichment_prompt(
    variables: list[dict], insufficient_ids: list[str], language_hint: str = "es"
) -> tuple[str, str]:
    """
    Construye (system_prompt, user_prompt) para el enriquecimiento.

    Args:
        variables: lista de {"variable_id", "text", "scale_labels", "data_type"}.
        insufficient_ids: IDs ya marcados INSUFFICIENT_CONTEXT por S4 (el LLM debe
                          respetarlos; el validador lo hará cumplir de todos modos).
        language_hint: idioma para las respuestas del LLM.
    """
    # Compresión para VRAM limitada: recortar el texto de cada variable y NO repetir
    # las etiquetas de escala en cada ítem (se listan una sola vez como escalas comunes).
    scale_sets: list[list[str]] = []
    def _scale_ref(labels: list[str]) -> int | None:
        if not labels:
            return None
        for i, s in enumerate(scale_sets):
            if s == labels:
                return i
        scale_sets.append(labels)
        return len(scale_sets) - 1

    variables_compact = [
        {
            "variable_id": v.get("variable_id"),
            "text": (v.get("text") or "")[:140],
            "scale": _scale_ref(v.get("scale_labels") or []),
            "type": v.get("data_type"),
        }
        for v in variables
    ]
    payload = json.dumps(
        {
            "language": language_hint,
            "insufficient_context_ids": insufficient_ids,
            "escalas_comunes": {str(i): s for i, s in enumerate(scale_sets)},
            "variables": variables_compact,
        },
        ensure_ascii=False,
    )
    user = (
        "Enriquece estas variables y devuelve el JSON. 'scale' referencia una escala de "
        "escalas_comunes. Respeta la no-invención para insufficient_context_ids.\n\n"
        f"{payload}"
    )
    return _SYSTEM, user
