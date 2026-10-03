"""Schemas Pydantic: metadatos_enriquecidos_entrevistas (hija de raw_data).

Refleja 1:1 la tabla `tt_rag.metadatos_enriquecidos_entrevistas` de 01_schema.sql.
PK = id_crudo (FK a raw_data).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MetadatosEntrevistasBase(BaseModel):
    identificador_propio: str | None = None
    objetivo: str | None = None
    metodologia: str | None = None
    institucion: str | None = None
    derechos: str | None = None


class MetadatosEntrevistasCreate(MetadatosEntrevistasBase):
    id_crudo: int


class MetadatosEntrevistasUpdate(MetadatosEntrevistasBase):
    pass


class MetadatosEntrevistasRead(MetadatosEntrevistasBase):
    model_config = ConfigDict(from_attributes=True)

    id_crudo: int
