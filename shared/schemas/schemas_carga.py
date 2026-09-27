# app/schemas/schemas_carga.py
"""
Schemas Pydantic — Módulo de CARGA de instrumentos.

Cubre los endpoints del wizard (flujo vigente):
  POST /instrumentos/upload                    → Paso 1
  POST /instrumentos/metadata                  → Paso 2
  POST /instrumentos/{id}/analyze              → Paso 3 (SIS)
  GET  /instrumentos/{id}/etl/proposals        → ver propuestas
  POST /instrumentos/{id}/approve/cleaning     → Paso 4a
  POST /instrumentos/{id}/approve/enrichment   → Paso 4b

Tipos base compartidos con visualización también se definen aquí
porque son fundamentales para el pipeline de estados.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from api.core import domain_constants as _dc

# ---------------------------------------------------------------------------
# Tipos base (compartidos con schemas_visualizacion.py)
#
# Los valores son la contraparte tipada (Literal) de las tuplas canónicas de
# api/core/domain_constants.py. El guard de import-time (más abajo) garantiza
# que ambos no se desincronicen.
# ---------------------------------------------------------------------------

TipoInstrumento   = Literal["encuesta", "entrevista", "prueba_estandarizada"]
EstadoPipeline    = Literal[
    "pendiente",
    "metadata_registrado",
    "etl_pendiente_limpieza",
    "etl_pendiente_enriquecimiento",
    "etl_aprobado",
    "en_ingesta",
    "vectorizado",
    "error",
]
TipoPropuesta     = Literal["transformacion", "metadato_enriquecido", "kpi_sugerido"]
DecisionPropuesta = Literal["aceptada", "rechazada"]

# Guard: si un Literal y su tupla canónica divergen, el arranque falla con un
# mensaje claro (evita desincronización silenciosa entre schemas y modelos/BD).
_dc.assert_literal_matches(
    "TipoInstrumento", ("encuesta", "entrevista", "prueba_estandarizada"), _dc.TIPOS_INSTRUMENTO
)
_dc.assert_literal_matches(
    "EstadoPipeline",
    (
        "pendiente",
        "metadata_registrado",
        "etl_pendiente_limpieza",
        "etl_pendiente_enriquecimiento",
        "etl_aprobado",
        "en_ingesta",
        "vectorizado",
        "error",
    ),
    _dc.ESTADOS_PIPELINE,
)
_dc.assert_literal_matches(
    "TipoPropuesta", ("transformacion", "metadato_enriquecido", "kpi_sugerido"), _dc.TIPOS_PROPUESTA
)


# ---------------------------------------------------------------------------
# Normalizador compartido de tipo_instrumento (fuente única)
# ---------------------------------------------------------------------------

def normalizar_tipo_instrumento(v: str | None) -> str | None:
    """
    Normaliza un valor de tipo_instrumento a la forma canónica.

    Acepta indistintamente mayúsculas/minúsculas, espacios sobrantes y el uso de
    espacio en lugar de guion bajo (p.ej. 'Prueba Estandarizada' -> 'prueba_estandarizada').
    Usado por los validadores de carga y de visualización para garantizar un
    comportamiento idéntico en ambos endpoints.
    """
    if isinstance(v, str):
        return v.lower().strip().replace(" ", "_")
    return v


# ===========================================================================
# ENTRADA — Paso 1: Upload
# ===========================================================================

class UploadRequest(BaseModel):
    """
    Se envía como form-data junto al archivo.
    tipo_instrumento es inmutable desde este momento.
    Todos los instrumentos son públicos (acceso RAG colaborativo).
    
    NOTA: tipo_instrumento acepta mayúsculas/minúsculas (se normaliza a minúsculas).
    """
    tipo_instrumento: TipoInstrumento

    @field_validator("tipo_instrumento", mode="before")
    @classmethod
    def _normalizar_tipo(cls, v: str) -> str:
        """Normaliza el tipo con el helper compartido (minúsculas, trim, espacio->guion bajo)."""
        return normalizar_tipo_instrumento(v)


# ===========================================================================
# ENTRADA — Paso 2: Metadatos Dublin Core
# ===========================================================================

# ===========================================================================
# ENTRADA — Paso 2: Registro de metadatos Dublin Core
# ===========================================================================

class MetadataInitialData(BaseModel):
    """
    Datos pre-poblados para inicializar el formulario del Paso 2.
    El frontend muestra estos valores y permite editar solo los campos manuales.
    """
    instrumento_id: int
    
    # Campos autocompletados (solo lectura en UI)
    dc_creator:    str = Field(..., description="Usuario que subió el instrumento")
    dc_publisher:  str = Field(..., description="Organización propietaria del sistema")
    dc_type:       str = Field(..., description="Tipo de instrumento")
    dc_format:     str = Field(..., description="Formato del archivo")
    dc_date:       str = Field(..., description="Fecha de registro YYYY-MM-DD")
    dc_language:   str = Field(default="es", description="Idioma del instrumento")
    
    # Título propuesto (editable)
    dc_title_sugerido: str = Field(..., description="Título generado, puede modificarse")


class MetadataRequest(BaseModel):
    """
    Campos del Paso 2: Registro de metadatos Dublin Core.
    
    AUTOCOMPLETADOS (no están en el request, el backend los completa):
    - instrumento_id → obtenido del parámetro de ruta
    - dc_creator → usuario autenticado
    - dc_publisher → configuración institucional
    - dc_type → InstrumentoProcesado.tipo_instrumento
    - dc_format → extensión del archivo
    - dc_date → fecha de registro
    - dc_language → "es" por defecto
    
    CAPTURA MANUAL (están en el request):
    - dc_title → inicializado con nombre del instrumento, editable
    - dc_subject → lista de temas
    - dc_description → descripción del contenido
    - dc_coverage → cobertura espacial/temporal
    - dc_rights → derechos de uso
    - dc_source → opcional
    - dc_relation → opcional
    """
    dc_title:       str       = Field(..., min_length=1)
    dc_subject:     list[str] = Field(..., min_length=1)
    dc_description: str       = Field(..., min_length=1)
    dc_coverage:    str       = Field(..., min_length=1)
    dc_rights:      str       = Field(..., min_length=1)
    dc_source:      str | None = None
    dc_relation:    str | None = None


# ===========================================================================
# ENTRADA — Paso 4: Aprobación de propuestas ETL
# ===========================================================================

class DecisionInput(BaseModel):
    """Decisión del usuario sobre una propuesta individual."""
    propuesta_id: int
    decision:     DecisionPropuesta


class AprobacionRequest(BaseModel):
    """
    Debe incluir una DecisionInput por CADA propuesta en estado 'pendiente'.
    Si falta alguna, el endpoint devuelve 400 con la lista de IDs faltantes.
    """
    instrumento_id: int
    decisiones:     list[DecisionInput] = Field(..., min_length=1)


# ===========================================================================
# ENTRADA — Paso 5: Ingesta
# ===========================================================================

class IngestaRequest(BaseModel):
    """El servicio verifica internamente que el estado sea 'etl_aprobado'."""
    instrumento_id: int


# ===========================================================================
# SALIDA — Paso 1
# ===========================================================================

class UploadResponse(BaseModel):
    instrumento_id: int
    estado:         EstadoPipeline  # siempre 'pendiente'
    mensaje:        str


# ===========================================================================
# SALIDA — Paso 2
# ===========================================================================

class MetadataResponse(BaseModel):
    instrumento_id: int
    estado:         EstadoPipeline  # siempre 'metadata_registrado'
    mensaje:        str


# ===========================================================================
# SALIDA — Ver propuestas (idempotente, entre paso 3 y 4)
# ===========================================================================

from datetime import datetime
from pydantic import ConfigDict

class EtlPropuestaOutput(BaseModel):
    propuesta_id:     int
    tipo:             TipoPropuesta
    descripcion:      str
    accion_sugerida:  str
    justificacion:    str
    impacto_esperado: str | None
    valor_original:   str | None
    valor_propuesto:  str | None
    estado_decision:  str
    fecha_propuesta:  datetime
    fecha_decision:   datetime | None

    model_config = ConfigDict(from_attributes=True)


class EtlProposalsResponse(BaseModel):
    instrumento_id: int
    estado:         EstadoPipeline
    propuestas:     list[EtlPropuestaOutput]
    n_pendientes:   int
    n_aceptadas:    int
    n_rechazadas:   int


# ===========================================================================
# SALIDA — Paso 5 (reservado: módulo de vectorización futuro)
# ===========================================================================

class IngestaResponse(BaseModel):
    instrumento_id: int
    mensaje:        str


# ===========================================================================
# SALIDA — analyze (SIS): ejecuta el pipeline completo y persiste propuestas
# ===========================================================================

class AnalyzeResponse(BaseModel):
    """Confirma que el SIS analizó el instrumento y dejó propuestas por decidir."""
    instrumento_id:      int
    estado:              EstadoPipeline   # 'etl_pendiente_limpieza'
    status_sis:          str              # completed | completed_degraded | failed
    n_transformaciones:  int              # propuestas de limpieza (camino 1)
    n_metadatos:         int              # metadatos enriquecidos (camino 2)
    n_kpis:              int              # KPIs inferidos (camino 2)
    n_hallazgos:         int              # hallazgos analíticos de resultados (S8b)
    n_improvements:      int              # oportunidades de mejora emitidas
    degraded:            bool             # True si el LLM no participó
    mensaje:             str


# ===========================================================================
# SALIDA — approve/cleaning (camino 1: transformaciones sobre los datos)
# ===========================================================================

class CleaningApprovalResponse(BaseModel):
    instrumento_id:      int
    estado:              EstadoPipeline   # 'etl_pendiente_enriquecimiento'
    n_aceptadas:         int
    n_rechazadas:        int
    n_aplicadas:         int              # transformaciones realmente ejecutadas
    ruta_dataset_limpio: str | None = None  # storage/clean/{id}_clean.csv (encuestas)
    mensaje:             str


# ===========================================================================
# SALIDA — approve/enrichment (camino 2: metadatos + KPIs)
# ===========================================================================

class EnrichmentApprovalResponse(BaseModel):
    instrumento_id: int
    estado:         EstadoPipeline   # 'etl_aprobado'
    n_aceptadas:    int
    n_rechazadas:   int
    mensaje:        str
