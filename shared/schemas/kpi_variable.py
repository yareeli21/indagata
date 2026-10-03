"""Schemas Pydantic: kpi_variable (relación N:M entre KPI y variable).

Refleja 1:1 la tabla `tt_rag.kpi_variable` de 01_schema.sql. PK compuesta
(kpi_id, variable_id); no tiene columnas adicionales.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPIVariableBase(BaseModel):
    kpi_id: int
    variable_id: int


class KPIVariableCreate(KPIVariableBase):
    pass


class KPIVariableRead(KPIVariableBase):
    model_config = ConfigDict(from_attributes=True)
