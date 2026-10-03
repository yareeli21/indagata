"""Schemas Pydantic: metadatos_dc (Dublin Core adaptado, hija de raw_data).

Refleja 1:1 la tabla `tt_rag.metadatos_dc` de 01_schema.sql. La PK es `id_crudo`
(FK a raw_data). `dc_title` es el único campo obligatorio.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MetadatosDCBase(BaseModel):
    """Los 13 campos Dublin Core. dc_title es el único obligatorio."""

    model_config = ConfigDict(from_attributes=True)

    dc_title: str
    dc_creator: str | None = None
    dc_description: str | None = None
    dc_type: str | None = None
    dc_date: str | None = None
    dc_language: str | None = None
    dc_coverage: str | None = None
    dc_subject: str | None = None
    dc_publisher: str | None = None
    dc_rights: str | None = None
    dc_format: str | None = None
    dc_source: str | None = None
    dc_relation: str | None = None


class MetadatosDCCreate(MetadatosDCBase):
    id_crudo: int


class MetadatosDCUpdate(BaseModel):
    dc_title: str | None = None
    dc_creator: str | None = None
    dc_description: str | None = None
    dc_type: str | None = None
    dc_date: str | None = None
    dc_language: str | None = None
    dc_coverage: str | None = None
    dc_subject: str | None = None
    dc_publisher: str | None = None
    dc_rights: str | None = None
    dc_format: str | None = None
    dc_source: str | None = None
    dc_relation: str | None = None


class MetadatosDCRead(MetadatosDCBase):
    id_crudo: int
