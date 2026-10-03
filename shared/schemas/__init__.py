"""Esquemas Pydantic compartidos (DTOs de entidades transversales).

Solo se definen aquí los DTOs de entidades que cruzan servicios (instrumento,
usuario, KPI, metadatos Dublin Core). Cada microservicio define sus propios
DTOs de request/response específicos en su carpeta `schemas/`.

Los campos reflejan 1:1 el esquema de
`infrastructure/postgres/init/01_schema.sql`.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Usuario ──────────────────────────────────────────────────────────────────
class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    nombre: str
    email: str
    rol: str | None = None


# ── Instrumento ──────────────────────────────────────────────────────────────
class InstrumentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_instrumento: int
    id_crudo: int
    ruta_de_archivo_limpio: str | None = None
    ruta_json: str | None = None
    estado: str
    fecha_procesamiento: datetime | None = None
    fecha_aprobado: datetime | None = None


# ── Dublin Core ──────────────────────────────────────────────────────────────
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


# ── KPI ──────────────────────────────────────────────────────────────────────
class KPIRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
    nombre_kpi: str
    descripcion: str | None = None
    categoria: str | None = None
    ambito: str | None = None
    url_documentacion: str | None = None
    formula: str | None = None


__all__ = ["UsuarioRead", "InstrumentoRead", "MetadatosDCBase", "KPIRead"]
