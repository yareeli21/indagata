# survey_intelligence/contracts/kpi.py
"""
Contrato de inferencia de KPIs (design.md — KPI inference against the host catalog).

El SIS infiere KPIs relevantes y puntúa su relevancia, pero NO posee un catálogo.
Emite KpiInference con nombre sugerido + score + evidencia; el HOST hace el matching
contra su catálogo tt_rag.kpi y crea el KpiInferido. Proponer KPIs nuevos (fuera del
catálogo) se emite como ImprovementOpportunity, no como KPI directo.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class KpiInference(BaseModel):
    """Un KPI inferido por el SIS, para que el host lo mapee a su catálogo."""
    model_config = _FROZEN

    nombre_sugerido: str
    score_relevancia: float = Field(..., ge=0.0, le=1.0)
    tipo_relacion: str | None = None       # p. ej. "directa" | "inversa"
    evidencia_textual: str | None = None
    variables_fuente: list[str] = Field(default_factory=list)  # variable_ids
