"""Schemas Pydantic: variable.

Refleja 1:1 la tabla `tt_rag.variable` de 01_schema.sql.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VariableBase(BaseModel):
    nombre_variable: str
    descripcion: str | None = None
    tipo_dato: str | None = None
    unidad: str | None = None


class VariableCreate(VariableBase):
    pass


class VariableUpdate(BaseModel):
    nombre_variable: str | None = None
    descripcion: str | None = None
    tipo_dato: str | None = None
    unidad: str | None = None


class VariableRead(VariableBase):
    model_config = ConfigDict(from_attributes=True)

    variable_id: int
