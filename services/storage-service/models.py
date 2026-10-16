"""DTOs (Pydantic v2) del storage-service.

Los modelos ORM viven en `shared/models`; aquí solo están los contratos HTTP.

Dos responsabilidades:
  - Archivos: el servicio custodia los binarios (raw/clean/sav/temp) y los JSON
    (metadata/analysis/documento) bajo una clave versionada estable y devuelve dónde
    quedaron guardados. El archivo crudo se guarda SIN NINGÚN CAMBIO: se registra
    su SHA-256 para poder comprobarlo al descargarlo.
  - Índice vectorial: es el único servicio que escribe la colección
    `instrumentos` de ChromaDB (y sus filas en `documento_vectorizado`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Tipos de artefacto soportados (ruteo a directorio en file_manager).
TipoArtefacto = Literal["raw", "clean", "sav", "metadata", "analysis", "documento", "temp"]
TIPOS_BINARIOS: frozenset[str] = frozenset({"raw", "clean", "sav", "temp"})
# `documento`: documento final del knowledge-service (insumo de los chunks del RAG).
TIPOS_JSON: frozenset[str] = frozenset({"metadata", "analysis", "documento"})


# ── Archivos ───────────────────────────────────────────────────────────────────


class GuardarJsonRequest(BaseModel):
    """Cuerpo de POST /almacenamiento/json."""

    instrumentoId: str
    tipo: Literal["metadata", "analysis", "documento"]
    contenido: dict[str, Any]
    nombre: str | None = None  # para el slug del archivo; default "instrumento"


class ArtefactoRef(BaseModel):
    """Referencia a un artefacto almacenado (dónde quedó guardado)."""

    key: str = Field(..., description="Clave estable: <tipo>/<instrumentoId>/<version>__<slug>.")
    tipo: str
    instrumentoId: str | None
    version: int
    ruta_absoluta: str
    ruta_relativa: str = Field(..., description="Relativa a la raíz de storage.")
    size_bytes: int
    nombre_original: str
    creado: datetime
    sha256: str | None = Field(default=None, description="Huella del contenido almacenado.")
    mime_type: str | None = None


class ArtefactoDetalle(ArtefactoRef):
    """Como ArtefactoRef, más el contenido si el artefacto es JSON."""

    contenido: dict[str, Any] | None = None


class EliminarResultado(BaseModel):
    ruta: str
    eliminado: bool


class PurgaResultado(BaseModel):
    instrumentoId: str
    artefactos_eliminados: int
    vectores_eliminados: int


class TablaResponse(BaseModel):
    """Contenido tabular de un archivo (CSV/XLSX o JSON de instrumento)."""

    headers: list[str]
    rows: list[list[str]]
    n_filas: int = Field(..., description="Filas totales del archivo (antes de truncar).")
    n_columnas: int
    hoja: str | None = None
    encoding: str | None = None
    notas: list[str] = Field(default_factory=list)
    truncado: bool = False


class TextoResponse(BaseModel):
    """Texto plano extraído de un archivo (PDF/DOCX/TXT/MD/JSON/CSV)."""

    texto: str
    n_caracteres: int
    n_paginas: int | None = None
    notas: list[str] = Field(default_factory=list)


class EstadisticaTipo(BaseModel):
    n_artefactos: int
    bytes: int


class EstadisticasAlmacenamiento(BaseModel):
    por_tipo: dict[str, EstadisticaTipo]
    total_artefactos: int
    total_bytes: int
    cache: dict[str, int]


class LimpiezaTemporales(BaseModel):
    eliminados: int


# ── Índice vectorial ───────────────────────────────────────────────────────────


class IndexarRequest(BaseModel):
    reindexar: bool = True


class IndexarResponse(BaseModel):
    instrumentoId: str
    idInstrumento: int | None = None
    coleccion: str
    chunks: int
    estado: Literal["indexado", "omitido"]
    motivo: str | None = None


class DesindexarResponse(BaseModel):
    instrumentoId: str
    vectores_eliminados: int


class EstadoIndice(BaseModel):
    instrumentoId: str
    coleccion: str
    indexado: bool
    chunks: int
    aprobado: bool


class ColeccionInfo(BaseModel):
    nombre: str
    n_vectores: int
    embedding_model: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
