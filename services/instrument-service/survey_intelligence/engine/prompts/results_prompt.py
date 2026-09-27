# survey_intelligence/engine/prompts/results_prompt.py
"""
Prompt de análisis de resultados (etapa S8b).

Recibe métricas y distribuciones YA CALCULADAS (determinísticas) y pide al LLM una
interpretación textual, insights y un texto semántico para chunking. Regla dura:
interpretar EXCLUSIVAMENTE los datos observados; no inventar causas ni datos externos.
"""
from __future__ import annotations

import json

_SYSTEM = """
Eres un analista de datos de encuestas. Recibes métricas y distribuciones YA calculadas
de cada pregunta. Interpretas EXCLUSIVAMENTE lo que muestran los números; NO inventas
causas, contexto externo ni datos que no estén presentes.

Responde EXCLUSIVAMENTE con un objeto JSON (sin texto adicional):
{
  "findings": [
    {
      "variable_id": "...",
      "interpretation": "qué respondió la población, en 1-2 frases basadas en los números",
      "insights": ["patrón o implicación derivada SOLO de los datos"],
      "numeric_evidence": "cita numérica que respalda (p. ej. '5 de 6 = 83%')",
      "semantic_text": "resumen autocontenido optimizado para búsqueda semántica: incluye el tema de la pregunta y el hallazgo principal con su evidencia"
    }
  ]
}
Usa solo los variable_id proporcionados. Si una pregunta no tiene datos suficientes,
di que no hay datos suficientes en interpretation y deja insights vacío.
""".strip()


def build_results_prompt(findings_input: list[dict], language_hint: str = "es") -> tuple[str, str]:
    """
    Construye (system_prompt, user_prompt) para el análisis de resultados.

    Args:
        findings_input: lista de {"variable_id", "pregunta", "tipo", "metrics",
                        "distribution"} ya calculados de forma determinística.
    """
    payload = json.dumps(
        {"language": language_hint, "preguntas": findings_input},
        ensure_ascii=False,
    )
    user = (
        "Analiza estos resultados y devuelve el JSON. Interpreta solo los datos "
        "observados, sin inventar.\n\n"
        f"{payload}"
    )
    return _SYSTEM, user
