# app/schemas/schemas_visualizacion.py
"""
Schemas Pydantic — Módulo de VISUALIZACIÓN y DESCARGA de instrumentos.

Cubre los 4 endpoints de solo lectura + eliminación:
  GET    /instrumentos              → Catálogo con filtros
  GET    /instrumentos/{id}         → Detalle completo
  GET    /instrumentos/{id}/download → Descargar artefacto
  DELETE /instrumentos/{id}         → Eliminar (requiere ser propietario)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Importar tipos base y el normalizador desde schemas_carga (fuente única de verdad)
from api.schemas.schemas_carga import (
    TipoInstrumento,
    EstadoPipeline,
    normalizar_tipo_instrumento,
)

TipoDescarga = Literal["original", "json", "sav"]


# ===========================================================================
# ENTRADA — Filtros para GET /instrumentos
# ===========================================================================

class FiltrosInstrumento(BaseModel):
    """
    Query params opcionales para filtrar el catálogo de instrumentos.
    """
    tipo_instrumento: TipoInstrumento | None = Field(
        default=None, 
        description="Acepta: 'encuesta', 'entrevista', 'prueba_estandarizada' (con guion o espacio)"
    )
    kpi_nombre:       str | None             = Field(
        default=None, 
        description="Buscar instrumentos con KPIs que contengan este texto (case-insensitive)"
    )
    busqueda:         str | None             = Field(
        default=None, 
        description="Búsqueda de texto libre en título (dc_title) y descripción (dc_description)"
    )
    desde:            date | None            = Field(
        default=None, 
        description="Instrumentos creados desde esta fecha (YYYY-MM-DD)"
    )
    hasta:            date | None            = Field(
        default=None, 
        description="Instrumentos creados hasta esta fecha (YYYY-MM-DD)"
    )
    skip:             int                    = Field(
        default=0, 
        ge=0, 
        description="Paginación: número de resultados a saltar (ej: 0 para página 1, 20 para página 2 con limit=20)"
    )
    limit:            int                    = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Cantidad máxima de instrumentos a devolver por página (máximo: 100)"
    )

    @field_validator("tipo_instrumento", mode="before")
    @classmethod
    def _normalizar_tipo(cls, v: str | None) -> str | None:
        """Normaliza el tipo con el helper compartido (minúsculas, trim, espacio->guion bajo)."""
        return normalizar_tipo_instrumento(v)


# ===========================================================================
# SALIDA — Catálogo de KPIs
# ===========================================================================

class KpiCatalogo(BaseModel):
    """Item del catálogo de KPIs disponibles."""
    kpi_id:      int
    nombre:      str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# SALIDA — Catálogo (lista)
# ===========================================================================

class InstrumentoResumen(BaseModel):
    """Campos mínimos para la tabla del catálogo."""
    instrumento_id:   int
    nombre:           str
    tipo_instrumento: TipoInstrumento
    idioma:           str | None = None
    propietario:      str | None = None
    creado_en:        datetime
    kpis:             list[str] = Field(
        default_factory=list,
        description="Lista de nombres de KPIs asociados al instrumento"
    )

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# SALIDA — Detalle completo
# ===========================================================================

class KpiInferidoOutput(BaseModel):
    """KPI con nombre resuelto. Incluye los del paso 2 y los del ETL."""
    kpi_id:            int
    nombre_kpi:        str
    tipo_relacion:     str | None = Field(
        default=None, description="directa | indirecta | complementaria"
    )
    evidencia_textual: str | None
    score_inferencia:  float | None
    origen:            str = Field(description="registro_manual | propuesta_etl")

    model_config = ConfigDict(from_attributes=True)


class MetadatosEnriquecidosOutput(BaseModel):
    """Metadatos adicionales inferidos por el LLM y aceptados en el paso 4.
    
    Estructura flexible JSONB. Ejemplos de claves comunes:
    - poblacion_objetivo
    - unidad_analisis
    - sector_economico
    - ambito_geografico
    - dominio_tematico
    - metodologia_levantamiento
    - nivel_educativo
    - periodicidad
    - tamano_muestra
    """
    metadatos: dict[str, Any] = Field(
        default_factory=dict,
        description="Diccionario flexible con metadatos enriquecidos. Las claves dependen del análisis del LLM."
    )

    model_config = ConfigDict(from_attributes=True)


class InstrumentoDetalle(InstrumentoResumen):
    """
    Detalle completo. Solo lectura. Los datos vienen de PostgreSQL, no del JSON en disco.
    dublin_core y metadatos_enriquecidos son None si el instrumento no completó esos pasos.
    """
    dublin_core:            dict[str, Any] | None       = Field(
        default=None, description="15 campos DC. Disponible desde 'metadata_registrado'."
    )
    metadatos_enriquecidos: MetadatosEnriquecidosOutput | None = Field(
        default=None, description="None si el instrumento aún no pasó por ETL."
    )
    kpis_inferidos_detalle: list[KpiInferidoOutput]     = Field(default_factory=list)
    fecha_procesamiento:    datetime | None              = None
    error_detalle:          str | None                   = Field(
        default=None, description="Solo cuando estado = 'error'."
    )

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# SALIDA — Eliminación
# ===========================================================================

class EliminacionResponse(BaseModel):
    mensaje: str
