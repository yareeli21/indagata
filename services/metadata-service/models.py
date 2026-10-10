"""DTOs (Pydantic v2) del metadata-service.

Los modelos ORM viven en `shared/models` (metadatos_dc y metadatos_enriquecidos_*);
aquí solo están los contratos HTTP que consume el asistente de carga del frontend.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CampoOut(BaseModel):
    clave: str
    etiqueta: str
    tipo: str
    requerido: bool
    automatico: bool
    ayuda: str = ""
    max_longitud: int | None = None


class PropuestaResponse(BaseModel):
    """Valores propuestos (o ya aprobados) para un grupo de metadatos."""

    id_crudo: int
    id_instrumento: int
    tipo_instrumento: str
    tabla: str = Field(..., description="Tabla de destino de estos metadatos.")
    aprobado: bool
    fecha_aprobado: datetime | None = None
    valores: dict[str, Any]
    origen: dict[str, str] = Field(
        default_factory=dict,
        description="De dónde salió cada valor: automatico | archivo | inferido | llm | aprobado.",
    )
    obligatorios: list[str]
    campos: list[CampoOut]
    notas: list[str] = Field(default_factory=list)


class MetadatosPayload(BaseModel):
    """Metadatos revisados por el autor (Dublin Core + específicos del tipo)."""

    dublin_core: dict[str, Any] = Field(default_factory=dict)
    enriquecidos: dict[str, Any] = Field(default_factory=dict)


class VistaPreviaResponse(BaseModel):
    json_estandarizado: dict[str, Any]
    valido: bool
    errores: dict[str, dict[str, str]]


class ArtefactoOut(BaseModel):
    key: str
    version: int


class IngestaOut(BaseModel):
    indexado: bool
    chunks: int
    motivo: str | None = None


class AprobacionResponse(BaseModel):
    id_crudo: int
    id_instrumento: int
    estado: str
    aprobado: bool
    fecha_aprobado: datetime | None
    json_estandarizado: dict[str, Any]
    texto_instrumento: str = Field(..., description="Instrumento en Markdown (entrada para proponer KPIs).")
    artefacto: ArtefactoOut
    ingesta: IngestaOut
    mensaje: str


class KpiFinal(BaseModel):
    kpi_id: int
    nombre_kpi: str
    score: float | None = None


class FinalizacionResponse(BaseModel):
    id_crudo: int
    kpis: list[KpiFinal]
    artefacto: ArtefactoOut
    ingesta: IngestaOut
    mensaje: str


class MetadatosResponse(BaseModel):
    id_crudo: int
    tipo_instrumento: str
    estado: str
    aprobado: bool
    fecha_aprobado: datetime | None = None
    dublin_core: dict[str, Any]
    enriquecidos: dict[str, Any] | None = None


class ResumenMetadatos(BaseModel):
    id_crudo: int
    dc_title: str
    dc_creator: str | None = None
    dc_type: str | None = None
    dc_date: str | None = None


class ListadoMetadatos(BaseModel):
    total: int
    skip: int
    limit: int
    metadatos: list[ResumenMetadatos]


class RetiroResponse(BaseModel):
    id_crudo: int
    mensaje: str
