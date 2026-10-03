"""Schemas Pydantic: rag_log (bitácora de consultas RAG).

Refleja 1:1 la tabla `tt_rag.rag_log` de 01_schema.sql. La columna de fecha se
llama literalmente `timestamp`.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RagLogBase(BaseModel):
    pregunta: str
    respuesta: str | None = None
    modelo_usado: str | None = None
    chunks_usados: int | None = None
    latencia_ms: int | None = None


class RagLogCreate(RagLogBase):
    pass


class RagLogRead(RagLogBase):
    model_config = ConfigDict(from_attributes=True)

    rag_log_id: int
    timestamp: datetime | None = None
