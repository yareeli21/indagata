"""DTOs HTTP del knowledge-service."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetadatosPayload(BaseModel):
    """Metadatos revisados por el autor (mismo cuerpo que la vista previa de metadata-service)."""

    dublin_core: dict[str, Any] = Field(default_factory=dict)
    enriquecidos: dict[str, Any] = Field(default_factory=dict)


class AvisoOut(BaseModel):
    codigo: str
    mensaje: str
    n: int | None = None


class PerfilVistaPreviaOut(BaseModel):
    """Perfil semántico sin guardar (paso «Aprobar metadatos»)."""

    perfil: dict[str, Any]
    fuente: str = Field(..., description="original | encabezados | json_tecnico")
    n_preguntas: int
    avisos: list[AvisoOut] = Field(default_factory=list)


class PerfilOut(PerfilVistaPreviaOut):
    """Perfil semántico guardado en una versión del conocimiento."""

    id_crudo: int
    version: int
    estado: str
    fecha_creacion: datetime | None = None


class DocumentoOut(BaseModel):
    """Documento final de una versión del conocimiento (vista ligera, sin respuestas individuales)."""

    id_crudo: int
    version: int
    estado: str
    esquema_version: str
    sha256: str | None = None
    fecha_documento: datetime | None = None
    avisos: list[dict[str, Any]] = Field(default_factory=list)
    documento: dict[str, Any] = Field(..., description="Todo el documento salvo respondentes/alumnos/participantes, con su conteo y una muestra.")


class PublicadoOut(BaseModel):
    id_crudo: int
    version: int
    estado: str
    fecha_publicacion: datetime | None = None
