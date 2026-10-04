"""Schemas Pydantic: metadatos_enriquecidos_encuestas (hija de raw_data).

Refleja 1:1 la tabla `tt_rag.metadatos_enriquecidos_encuestas` de 01_schema.sql.
PK = id_crudo (FK a raw_data). `palabras_clave` y `dimensiones` son JSONB.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class MetadatosEncuestasBase(BaseModel):
    n_respondentes: int | None = None
    n_poblacion: int | None = None
    objetivo: str | None = None
    carrera: str | None = None
    poblacion_objetivo: str | None = None
    constructo_principal: str | None = None
    palabras_clave: list[Any] | None = None
    dimensiones: list[Any] | None = None
    notas_contextuales: str | None = None
    notas_interpretacion: str | None = None


class MetadatosEncuestasCreate(MetadatosEncuestasBase):
    id_crudo: int


class MetadatosEncuestasUpdate(MetadatosEncuestasBase):
    pass


class MetadatosEncuestasRead(MetadatosEncuestasBase):
    model_config = ConfigDict(from_attributes=True)

    id_crudo: int
