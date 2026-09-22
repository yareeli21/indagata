# survey_intelligence/contracts/results.py
"""
Contrato de hallazgos analíticos derivados de las RESPUESTAS del instrumento.

A diferencia del enriquecimiento semántico (que describe QUÉ mide una pregunta),
esto describe QUÉ respondió la población y QUÉ SIGNIFICA, con evidencia numérica.

Es el insumo más valioso para los chunks del RAG: cada ResultsFinding se convierte
en un chunk con texto semántico + evidencia observada.

Reparto:
  - Determinístico (sin LLM): metrics, distribution, numeric_evidence.
  - LLM (solo datos observados, sin inventar): interpretation, insights, semantic_text.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class DistributionBin(BaseModel):
    """Una categoría de respuesta con su frecuencia y porcentaje."""
    model_config = _FROZEN

    value: str
    frequency: int
    percentage: float


class ResultMetrics(BaseModel):
    """Métricas agregadas de las respuestas de una pregunta (determinístico)."""
    model_config = _FROZEN

    n_respuestas: int
    n_nulos: int
    moda: str | None = None
    media_codificada: float | None = None   # solo ordinales con value_encoding


class ResultsFinding(BaseModel):
    """Hallazgo analítico de una pregunta (una fila -> un chunk del RAG)."""
    model_config = _FROZEN

    variable_id: str
    pregunta: str
    tipo: str
    metrics: ResultMetrics
    distribution: list[DistributionBin] = Field(default_factory=list)

    # Generados por LLM sobre los datos observados (nunca inventados).
    interpretation: str | None = None
    insights: list[str] = Field(default_factory=list)
    numeric_evidence: str | None = None
    semantic_text: str | None = None
