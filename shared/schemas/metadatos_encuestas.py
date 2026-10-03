"""Schemas Pydantic: metadatos_enriquecidos_encuestas (hija de raw_data).

Refleja 1:1 la tabla `tt_rag.metadatos_enriquecidos_encuestas` de 01_schema.sql.
PK = id_crudo (FK a raw_data).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MetadatosEncuestasBase(BaseModel):
    n_respondentes: int | None = None
    n_poblacion: int | None = None
    carrera: str | None = None
    poblacion_objetivo: str | None = None
    notas_contextuales: str | None = None
    notas_interpretacion: str | None = None


class MetadatosEncuestasCreate(MetadatosEncuestasBase):
    id_crudo: int


class MetadatosEncuestasUpdate(MetadatosEncuestasBase):
    pass


class MetadatosEncuestasRead(MetadatosEncuestasBase):
    model_config = ConfigDict(from_attributes=True)

    id_crudo: int
