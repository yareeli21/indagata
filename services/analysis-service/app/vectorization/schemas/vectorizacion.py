"""Schemas Pydantic del módulo de vectorización e inferencia de KPIs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Paso 1: proponer KPIs ─────────────────────────────────────────────────────

class PropuestaKPI(BaseModel):
    """Un KPI candidato propuesto por similitud semántica."""

    kpi_id: int = Field(..., description="PK del KPI en la tabla tt_rag.kpi.")
    nombre_kpi: str = Field(..., description="Nombre del KPI.")
    categoria: str | None = Field(default=None, description="Categoría del KPI.")
    ambito: str | None = Field(default=None, description="Ámbito del KPI.")
    score: float = Field(..., description="Similitud [0,1] con el instrumento (mayor = más cercano).")


class PropuestasResponse(BaseModel):
    """Respuesta del paso 1: KPIs propuestos para que el usuario decida."""

    id_instrumento: int
    tipo_instrumento: str
    metadatos_clave: dict[str, str] = Field(
        ..., description="Metadatos extraídos que alimentaron el vector del summary."
    )
    propuestas: list[PropuestaKPI] = Field(
        ..., description="KPIs candidatos ordenados por score descendente."
    )
    mensaje: str = Field(default="Propuestas generadas por similitud semántica.")


# ── Paso 2: confirmar y enriquecer ────────────────────────────────────────────

class DecisionKPI(BaseModel):
    """Decisión del usuario sobre un KPI propuesto."""

    kpi_id: int
    aceptado: bool
    score: float | None = Field(
        default=None, description="Score mostrado al usuario (se persiste como evidencia)."
    )


class ConfirmarRequest(BaseModel):
    """Payload del paso 2: decisiones + el JSON original a enriquecer."""

    id_instrumento: int = Field(..., description="PK de instrumento_procesado.")
    decisiones: list[DecisionKPI] = Field(..., description="Aceptación/rechazo por KPI.")
    json_instrumento: dict[str, Any] = Field(
        ..., description="El JSON del instrumento recibido en el paso 1."
    )


class KpiAgregado(BaseModel):
    """Un KPI que quedó agregado al JSON enriquecido."""

    kpi_id: int
    nombre_kpi: str
    score: float | None = None


class ConfirmarResponse(BaseModel):
    """Respuesta del paso 2: el JSON enriquecido con los KPIs aceptados."""

    id_instrumento: int
    kpis_agregados: list[KpiAgregado]
    json_enriquecido: dict[str, Any] = Field(
        ..., description="El JSON con la clave 'inferred_kpis' añadida."
    )
    mensaje: str = Field(default="JSON enriquecido con los KPIs aceptados.")


# ── Mantenimiento: reindexar colección de KPIs ────────────────────────────────

class ReindexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coleccion: str
    n_kpis: int
    mensaje: str = Field(default="Colección de KPIs reindexada.")


# ── Inspección: ver el embedding del summary de un instrumento ────────────────

class SummaryEmbeddingResponse(BaseModel):
    """Vista de solo lectura del vector del summary de un instrumento."""

    id_instrumento: int
    coleccion: str = Field(..., description="Colección Chroma donde vive el summary.")
    embedding_model: str | None = Field(
        default=None, description="Modelo con el que se generó el vector."
    )
    dimension: int = Field(..., description="Nº de dimensiones del vector (p. ej. 768).")
    embedding_preview: list[float] = Field(
        ..., description="Primeros valores del vector (muestra; no el vector completo)."
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata del punto en Chroma.")
    document_preview: str | None = Field(
        default=None, description="Primeros caracteres del texto (summary) que se vectorizó."
    )
