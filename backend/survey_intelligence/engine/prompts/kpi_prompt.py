# survey_intelligence/engine/prompts/kpi_prompt.py
"""
Prompt de inferencia de KPIs (S7-KPI).

Pide al LLM inferir qué KPIs son relevantes para el instrumento y puntuar su relevancia,
apoyándose en el catálogo del host (nombres + descripciones) para favorecer el matching.
El SIS sugiere nombres y scores; el host mapea al kpi_id real.
"""
from __future__ import annotations

import json

_SYSTEM = """
Eres un analista experto en indicadores (KPIs) de instrumentos educativos. Dado el
propósito del instrumento y sus preguntas, infieres qué KPIs del CATÁLOGO son relevantes
y puntúas su relevancia (0.0 a 1.0). No inventes KPIs fuera del catálogo.

Responde EXCLUSIVAMENTE con un objeto JSON (sin texto adicional):
{
  "kpis": [
    {
      "nombre_sugerido": "<nombre EXACTO del catálogo>",
      "score_relevancia": 0.0-1.0,
      "tipo_relacion": "directa" | "inversa",
      "evidencia_textual": "por qué es relevante",
      "variables_fuente": ["variable_id", ...]
    }
  ]
}
Usa solo nombres presentes en catalog_names. Si ninguno aplica, devuelve {"kpis": []}
Selecciona a lo sumo los 5 KPIs más relevantes.
""".strip()


def build_kpi_prompt(
    purpose: str | None,
    questions: list[dict],
    catalog: list[dict],
) -> tuple[str, str]:
    """
    Construye (system_prompt, user_prompt) para la inferencia de KPIs.

    Args:
        purpose:   propósito inferido del instrumento (de S7), puede ser None.
        questions: [{"variable_id"/"question_id", "text"}].
        catalog:   catálogo del host [{"nombre": str, "descripcion": str}].
    """
    # Compresión para VRAM limitada: solo nombres del catálogo (sin descripciones
    # largas) y los textos de pregunta recortados. El nombre basta para el matching.
    catalog_names = [str(c.get("nombre", "")) for c in catalog if c.get("nombre")]
    questions_compact = [
        {"id": q.get("question_id") or q.get("variable_id"), "text": (q.get("text") or "")[:120]}
        for q in questions
    ]
    payload = json.dumps(
        {
            "purpose": purpose or "(no inferido)",
            "catalog_names": catalog_names,
            "questions": questions_compact,
        },
        ensure_ascii=False,
    )
    user = (
        "Infiere los KPIs relevantes del catálogo (usa el nombre EXACTO) y puntúa su "
        "relevancia. Devuelve el JSON.\n\n"
        f"{payload}"
    )
    return _SYSTEM, user
