"""Schemas Pydantic: instrumento_procesado (entidad central del pipeline).

Refleja 1:1 la tabla `tt_rag.instrumento_procesado` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Vocabulario cerrado del CHECK de la columna `estado`.
EstadoInstrumento = Literal[
    "recibido",
    "limpieza_en_proceso",
    "limpio",
    "metadatos_registrados",
    "estandarizado",
    "vectorizado",
    "error",
]


class InstrumentoProcesadoBase(BaseModel):
    id_crudo: int
    ruta_de_archivo_limpio: str | None = None
    ruta_json: str | None = None
    estado: EstadoInstrumento = "recibido"


class InstrumentoProcesadoCreate(InstrumentoProcesadoBase):
    pass


class InstrumentoProcesadoUpdate(BaseModel):
    ruta_de_archivo_limpio: str | None = None
    ruta_json: str | None = None
    estado: EstadoInstrumento | None = None
    fecha_aprobado: datetime | None = None


class InstrumentoProcesadoRead(InstrumentoProcesadoBase):
    model_config = ConfigDict(from_attributes=True)

    id_instrumento: int
    fecha_procesamiento: datetime | None = None
    fecha_aprobado: datetime | None = None
