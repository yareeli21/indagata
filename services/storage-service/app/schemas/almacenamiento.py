"""Schemas (Pydantic v2) del storage-service — contratos de artefactos.

Ver design.md §3.3: el servicio custodia JSON (metadata|analysis) y binarios
(raw|sav|temp) bajo una clave versionada estable y devuelve dónde quedaron
guardados.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class GuardarJsonRequest(BaseModel):
    """Cuerpo de POST /almacenamiento/json."""

    instrumentoId: str
    tipo: Literal["metadata", "analysis"]
    contenido: dict[str, Any]  # el JSON a persistir
    nombre: str | None = None  # para el slug; default "instrumento"


class ArtefactoRef(BaseModel):
    """Referencia a un artefacto almacenado (dónde quedó guardado)."""

    key: str  # clave relativa estable (§3.2): <tipo>/<instrumentoId>/<version>__<slug>.<ext>
    tipo: str
    instrumentoId: str | None
    version: int
    ruta_absoluta: str  # path dentro del contenedor
    ruta_relativa: str  # relativa a la raíz de storage
    size_bytes: int
    nombre_original: str
    creado: datetime


class ArtefactoDetalle(ArtefactoRef):
    """Como ArtefactoRef, pero incluye el contenido si es JSON (metadata/analysis)."""

    contenido: dict[str, Any] | None = None
