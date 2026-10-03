"""Schemas Pydantic: metadatos_enriquecidos_pruebas (hija de raw_data).

Refleja 1:1 la tabla `tt_rag.metadatos_enriquecidos_pruebas` de 01_schema.sql.
PK = id_crudo (FK a raw_data). `mapeo_de_reactivos_por_seccion` es JSONB.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class MetadatosPruebasBase(BaseModel):
    unidad_de_aprendizaje: str | None = None
    mapeo_de_reactivos_por_seccion: dict[str, Any] | None = None
    institucion: str | None = None
    campus: str | None = None
    grado: str | None = None
    grupo: str | None = None
    ciclo_escolar: str | None = None
    tipo_de_prueba: str | None = None
    version: str | None = None
    taxonomia_bloom: str | None = None
    nivel_educativo: str | None = None
    objetivo_de_evaluacion: str | None = None
    subareas: str | None = None
    competencias: str | None = None


class MetadatosPruebasCreate(MetadatosPruebasBase):
    id_crudo: int


class MetadatosPruebasUpdate(MetadatosPruebasBase):
    pass


class MetadatosPruebasRead(MetadatosPruebasBase):
    model_config = ConfigDict(from_attributes=True)

    id_crudo: int
