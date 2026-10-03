"""Schemas Pydantic: kpi_inferido (KPIs inferidos por instrumento).

Refleja 1:1 la tabla `tt_rag.kpi_inferido` de 01_schema.sql. PK compuesta
(id_procesado, kpi_id).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class KPIInferidoBase(BaseModel):
    id_procesado: int
    kpi_id: int
    razon: str | None = None
    resultado: Decimal | None = None


class KPIInferidoCreate(KPIInferidoBase):
    pass


class KPIInferidoUpdate(BaseModel):
    razon: str | None = None
    resultado: Decimal | None = None


class KPIInferidoRead(KPIInferidoBase):
    model_config = ConfigDict(from_attributes=True)

    fecha_inferencia: datetime | None = None
