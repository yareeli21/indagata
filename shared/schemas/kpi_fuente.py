"""Schemas Pydantic: kpi_fuente (fuentes de referencia de cada KPI).

Refleja 1:1 la tabla `tt_rag.kpi_fuente` de 01_schema.sql.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPIFuenteBase(BaseModel):
    kpi_id: int
    organismo: str
    titulo: str
    url: str
    anio: int | None = None
    nota: str | None = None


class KPIFuenteCreate(KPIFuenteBase):
    pass


class KPIFuenteRead(KPIFuenteBase):
    model_config = ConfigDict(from_attributes=True)

    kpi_fuente_id: int
