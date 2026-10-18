"""Schemas Pydantic: rag_log (bitácora de consultas RAG).

Refleja 1:1 la tabla `tt_rag.rag_log` de 01_schema.sql. La columna de fecha se
llama literalmente `timestamp`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RagLogBase(BaseModel):
    pregunta: str
    respuesta: str | None = None
    modelo_usado: str | None = None
    chunks_usados: int | None = None
    latencia_ms: int | None = None
    decision_dominio: str | None = None
    motivo: str | None = None
    score_max: float | None = None
    ruta: str | None = None
    instrumentos: list[str] = []
    contexto_usado: list[dict[str, Any]] = []
    metricas: dict[str, Any] | None = None
    modelo_juez: str | None = None
    fecha_metricas: datetime | None = None
    clave_cache: str | None = None
    salida: dict[str, Any] | None = None


class RagLogCreate(RagLogBase):
    pass


class RagLogRead(RagLogBase):
    model_config = ConfigDict(from_attributes=True)

    rag_log_id: int
    timestamp: datetime | None = None
