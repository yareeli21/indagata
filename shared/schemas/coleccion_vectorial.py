"""Schemas Pydantic: coleccion_vectorial (config de colección Chroma).

Refleja 1:1 la tabla `tt_rag.coleccion_vectorial` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ColeccionVectorialBase(BaseModel):
    nombre: str
    embedding_model: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class ColeccionVectorialCreate(ColeccionVectorialBase):
    pass


class ColeccionVectorialUpdate(BaseModel):
    nombre: str | None = None
    embedding_model: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class ColeccionVectorialRead(ColeccionVectorialBase):
    model_config = ConfigDict(from_attributes=True)

    coleccion_id: int
    creado_en: datetime | None = None
