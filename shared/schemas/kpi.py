"""Schemas Pydantic: kpi.

Refleja 1:1 la tabla `tt_rag.kpi` de 01_schema.sql.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPIBase(BaseModel):
    nombre_kpi: str
    descripcion: str | None = None
    categoria: str | None = None
    ambito: str | None = None
    url_documentacion: str | None = None
    formula: str | None = None


class KPICreate(KPIBase):
    pass


class KPIUpdate(BaseModel):
    nombre_kpi: str | None = None
    descripcion: str | None = None
    categoria: str | None = None
    ambito: str | None = None
    url_documentacion: str | None = None
    formula: str | None = None


class KPIRead(KPIBase):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
