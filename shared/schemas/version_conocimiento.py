"""Schemas Pydantic: version_conocimiento (knowledge-service / analysis-service).

Refleja 1:1 la tabla `tt_rag.version_conocimiento` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict

from shared.models.version_conocimiento import ESTADOS_CONOCIMIENTO

EstadoConocimiento = Literal["perfil_aprobado", "kpis_confirmados", "borrador", "vigente", "reemplazado"]

# El Literal y el CHECK del modelo deben coincidir (falla al importar si divergen).
assert set(get_args(EstadoConocimiento)) == set(ESTADOS_CONOCIMIENTO), "EstadoConocimiento ≠ CHECK de la tabla"


class VersionConocimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_version: int
    id_crudo: int
    version: int
    estado: EstadoConocimiento
    perfil: dict[str, Any]
    decisiones_kpi: list[dict[str, Any]] = []
    ruta_documento: str | None = None
    esquema_version: str | None = None
    avisos: list[dict[str, Any]] = []
    sha256: str | None = None
    id_limpieza: int | None = None
    id_usuario: int | None = None
    fecha_creacion: datetime | None = None
    fecha_kpis: datetime | None = None
    fecha_documento: datetime | None = None
    fecha_publicacion: datetime | None = None
