"""Schemas Pydantic: kpi.

Refleja 1:1 la tabla `tt_rag.kpi` de 01_schema.sql: `kpi_id` + las 8 columnas
en español (`nombre`, 6 metadatos y `texto_contexto_rag_vectorial`).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPIBase(BaseModel):
    nombre: str
    polaridad_rendimiento: str | None = None
    tipo_objetivo_estrategico: str | None = None
    formula_metrica_calculo: str | None = None
    descripcion_ampliada_educativa: str | None = None
    comportamiento_direccional_causalidad: str | None = None
    razon_estrategica_decisiones: str | None = None
    texto_contexto_rag_vectorial: str


class KPICreate(KPIBase):
    pass


class KPIUpdate(BaseModel):
    nombre: str | None = None
    polaridad_rendimiento: str | None = None
    tipo_objetivo_estrategico: str | None = None
    formula_metrica_calculo: str | None = None
    descripcion_ampliada_educativa: str | None = None
    comportamiento_direccional_causalidad: str | None = None
    razon_estrategica_decisiones: str | None = None
    texto_contexto_rag_vectorial: str | None = None


class KPIRead(KPIBase):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
