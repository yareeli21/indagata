"""Schemas Pydantic: documento_vectorizado (chunks vectorizados en Chroma).

Refleja 1:1 la tabla `tt_rag.documento_vectorizado` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentoVectorizadoBase(BaseModel):
    instrumento_id: int | None = None
    coleccion_id: int | None = None
    chroma_vector_id: str | None = None
    chunk_index: int | None = None
    seccion: str | None = None
    chunk_texto: str
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)
    n_tokens: int | None = None


class DocumentoVectorizadoCreate(DocumentoVectorizadoBase):
    pass


class DocumentoVectorizadoUpdate(BaseModel):
    instrumento_id: int | None = None
    coleccion_id: int | None = None
    chroma_vector_id: str | None = None
    chunk_index: int | None = None
    seccion: str | None = None
    chunk_texto: str | None = None
    chunk_metadata: dict[str, Any] | None = None
    n_tokens: int | None = None


class DocumentoVectorizadoRead(DocumentoVectorizadoBase):
    model_config = ConfigDict(from_attributes=True)

    documento_vectorizado_id: int
    almacenado_en: datetime | None = None
