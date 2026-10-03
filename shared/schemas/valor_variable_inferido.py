"""Schemas Pydantic: valor_variable_inferido (valores inferidos por variable).

Refleja 1:1 la tabla `tt_rag.valor_variable_inferido` de 01_schema.sql. PK
compuesta (id_procesado, kpi_id, variable_id); FK compuesta
(id_procesado, kpi_id) -> kpi_inferido.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ValorVariableInferidoBase(BaseModel):
    id_procesado: int
    kpi_id: int
    variable_id: int
    valor_numerico: Decimal | None = None
    valor_texto: str | None = None
    valor_booleano: bool | None = None
    confianza_variable: Decimal | None = None


class ValorVariableInferidoCreate(ValorVariableInferidoBase):
    pass


class ValorVariableInferidoUpdate(BaseModel):
    valor_numerico: Decimal | None = None
    valor_texto: str | None = None
    valor_booleano: bool | None = None
    confianza_variable: Decimal | None = None


class ValorVariableInferidoRead(ValorVariableInferidoBase):
    model_config = ConfigDict(from_attributes=True)
