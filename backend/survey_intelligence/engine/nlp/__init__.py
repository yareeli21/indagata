# survey_intelligence/engine/nlp/__init__.py
"""
Motor NLP del SIS para instrumentos narrativos (entrevistas).

Piezas:
  - diarization: reconstrucción determinística de participantes y turnos de diálogo
    a partir de etiquetas de hablante en el texto (sin LLM).
  - interview_prompt: construcción del prompt de análisis + parseo robusto de la
    respuesta del LLM (temas, hallazgos, patrones, citas, resúmenes).
"""
from __future__ import annotations

from survey_intelligence.engine.nlp.diarization import diarize
from survey_intelligence.engine.nlp.interview_prompt import (
    build_interview_prompt,
    parse_interview_response,
)

__all__ = ["diarize", "build_interview_prompt", "parse_interview_response"]
