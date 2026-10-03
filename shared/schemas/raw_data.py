"""Schemas Pydantic: raw_data (tabla PADRE del pipeline).

Refleja 1:1 la tabla `tt_rag.raw_data` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RawDataBase(BaseModel):
    """Campos de un instrumento recibido en crudo."""

    id_owner: int
    tipo_instrumento: str
    nombre_archivo: str
    raw_archivo: str
    raw_archivo_original: str | None = None


class RawDataCreate(RawDataBase):
    pass


class RawDataUpdate(BaseModel):
    id_owner: int | None = None
    tipo_instrumento: str | None = None
    nombre_archivo: str | None = None
    raw_archivo: str | None = None
    raw_archivo_original: str | None = None


class RawDataRead(RawDataBase):
    model_config = ConfigDict(from_attributes=True)

    id_crudo: int
    fecha_carga: datetime | None = None
