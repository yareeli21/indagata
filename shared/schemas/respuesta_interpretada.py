"""Schemas Pydantic: respuesta_interpretada (respuestas del documento final en formato largo).

Refleja 1:1 la tabla `tt_rag.respuesta_interpretada` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RespuestaInterpretadaBase(BaseModel):
    id_crudo: int
    version: int
    respondente_id: str
    pregunta_id: str
    valor: str | None = None
    significado: str | None = None
    nivel: str | None = None
    estado: str
    contexto: dict[str, Any] = {}


class RespuestaInterpretadaCreate(RespuestaInterpretadaBase):
    pass


class RespuestaInterpretadaRead(RespuestaInterpretadaBase):
    model_config = ConfigDict(from_attributes=True)

    id_respuesta: int
    fecha_creacion: datetime | None = None
