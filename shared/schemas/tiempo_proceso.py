"""Schemas Pydantic: tiempo_proceso (tiempo de cómputo de cada paso de un instrumento).

Refleja 1:1 la tabla `tt_rag.tiempo_proceso` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TiempoProcesoBase(BaseModel):
    id_crudo: int
    servicio: str
    paso: str
    inicio: datetime
    fin: datetime
    duracion_ms: int
    detalle: dict[str, Any] = Field(default_factory=dict)


class TiempoProcesoCreate(TiempoProcesoBase):
    pass


class TiempoProcesoRead(TiempoProcesoBase):
    model_config = ConfigDict(from_attributes=True)

    tiempo_proceso_id: int
