"""Schemas Pydantic: limpieza_ejecucion (cleaning-service).

Refleja 1:1 la tabla `tt_rag.limpieza_ejecucion` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict

from shared.models.limpieza_ejecucion import ESTADOS_LIMPIEZA

EstadoLimpieza = Literal["esperando_decisiones", "confirmada", "fallida"]

# El Literal y el CHECK del modelo deben coincidir (falla al importar si divergen).
assert set(get_args(EstadoLimpieza)) == set(ESTADOS_LIMPIEZA), "EstadoLimpieza ≠ CHECK de la tabla"


class LimpiezaEjecucionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_limpieza: int
    id_crudo: int
    version: int
    estado: EstadoLimpieza
    id_investigador: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None
    fecha_confirmacion: datetime | None = None
    ruta_csv_limpio: str | None = None
    reporte: dict[str, Any] = {}
    error: str | None = None
