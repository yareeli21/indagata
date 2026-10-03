"""Schemas Pydantic: kpi_inferido_chunk (evidencia de la inferencia de KPIs).

Refleja 1:1 la tabla `tt_rag.kpi_inferido_chunk` de 01_schema.sql. PK compuesta
(id_procesado, kpi_id, documento_vectorizado_id); FK compuesta
(id_procesado, kpi_id) -> kpi_inferido.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class KpiInferidoChunkBase(BaseModel):
    id_procesado: int
    kpi_id: int
    documento_vectorizado_id: int
    score: Decimal | None = None


class KpiInferidoChunkCreate(KpiInferidoChunkBase):
    pass


class KpiInferidoChunkRead(KpiInferidoChunkBase):
    model_config = ConfigDict(from_attributes=True)
