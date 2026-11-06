"""Schemas Pydantic: rag_metrica_juez y rag_calificacion (evaluación de las respuestas del chat).

Reflejan 1:1 las tablas de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RagMetricaJuezRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rag_metrica_juez_id: int
    rag_log_id: int
    modelo_juez: str
    metricas: dict[str, Any] = {}
    version: str | None = None
    fecha: datetime | None = None


class RagCalificacionBase(BaseModel):
    calificacion: int = Field(ge=0, le=2)
    entendio: bool | None = None
    fundamenta: bool | None = None
    comentario: str | None = None


class RagCalificacionRead(RagCalificacionBase):
    model_config = ConfigDict(from_attributes=True)

    rag_log_id: int
    usuario_id: int | None = None
    fecha: datetime | None = None
