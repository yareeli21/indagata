# cargar_instru/schemas.py
"""
Schemas Pydantic para el módulo de gestión de instrumentos.

Cubren exclusivamente las cuatro pantallas funcionales:
  - Catálogo de instrumentos (listado con filtros)
  - Detalle de instrumento
  - Visualización y descarga de artefactos (archivo original, JSON, SAV)
  - Historial de versiones

Principio de diseño:
  La interfaz solo consume las tablas:
    instrumento_procesado, raw_data, permiso_instrumento, usuarios.
  Nunca expone información de pipeline_limpieza_log ni rutas internas
  de disco (ruta_texto_limpio, schema_version).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Tipos base — Literals de dominio
# ---------------------------------------------------------------------------

TipoInstrumento = Literal["encuesta", "entrevista", "prueba_estandarizada"]
EstadoPipeline  = Literal["recibido", "limpio", "estandarizado", "vectorizado", "error"]
Visibilidad     = Literal["publico", "privado"]


# ---------------------------------------------------------------------------
# Schemas de entrada — Carga y creación
# ---------------------------------------------------------------------------

class InstrumentoCreate(BaseModel):
    """
    Campos de texto enviados junto con el archivo al crear un instrumento
    (multipart/form-data).

    El archivo llega como UploadFile directamente en el router.
    Los 13 campos Dublin Core son obligatorios; sin ellos el endpoint
    devuelve 422 con la lista de campos faltantes.
    """

    # ── Datos básicos ─────────────────────────────────────────────────────
    nombre:           str           = Field(..., min_length=1, max_length=255)
    tipo_instrumento: TipoInstrumento
    visibilidad:      Visibilidad   = Field(
        default="publico",
        description="Por defecto público. El investigador lo cambia a privado si lo desea.",
    )

    # ── 13 campos Dublin Core obligatorios ────────────────────────────────
    dc_title:       str       = Field(..., min_length=1, description="Título completo del instrumento")
    dc_creator:     str       = Field(..., min_length=1, description="Autor o grupo creador")
    dc_subject:     list[str] = Field(..., min_length=1, description="Temas o palabras clave (al menos uno)")
    dc_description: str       = Field(..., min_length=1, description="Resumen del propósito")
    dc_publisher:   str       = Field(..., min_length=1, description="Institución que lo publicó o aplicó")
    dc_contributor: str       = Field(..., min_length=1, description="Personas que contribuyeron")
    dc_date:        str       = Field(..., min_length=1, description="Fecha de aplicación (YYYY o YYYY-MM)")
    dc_type:        str       = Field(..., min_length=1, description="Tipo de recurso")
    dc_format:      str       = Field(..., min_length=1, description="Formato del archivo original (PDF, DOCX…)")
    dc_identifier:  str       = Field(..., min_length=1, description="Código único legible (ej. IND-ENC-042)")
    dc_language:    str       = Field(..., min_length=1, description="Idioma (ej. 'es', 'en')")
    dc_coverage:    str       = Field(..., min_length=1, description="Población o cobertura geográfica")
    dc_rights:      str       = Field(..., min_length=1, description="Condiciones de uso y acceso")

    # ── Campos Dublin Core opcionales ─────────────────────────────────────
    dc_source:   str | None = Field(default=None, description="Fuente de origen, si aplica")
    dc_relation: str | None = Field(default=None, description="Relación con otros recursos")


class MetadatosUpdate(BaseModel):
    """
    Campos actualizables por el investigador después de la carga.
    Todos son opcionales — solo se actualizan los enviados.
    El servicio hace merge parcial sobre el JSON canónico (si existe).
    """

    # ── Dublin Core actualizables ─────────────────────────────────────────
    dc_title:       str | None       = None
    dc_creator:     str | None       = None
    dc_subject:     list[str] | None = None
    dc_description: str | None       = None
    dc_publisher:   str | None       = None
    dc_contributor: str | None       = None
    dc_date:        str | None       = None
    dc_type:        str | None       = None
    dc_format:      str | None       = None
    dc_identifier:  str | None       = None
    dc_language:    str | None       = None
    dc_coverage:    str | None       = None
    dc_rights:      str | None       = None
    dc_source:      str | None       = None
    dc_relation:    str | None       = None

    # ── Campos de contexto no cubiertos por Dublin Core ───────────────────
    objetivo:   str | None = Field(default=None, description="Objetivo detallado del instrumento")
    periodo_fin: str | None = Field(default=None, description="Periodo de fin de aplicación")

    # ── Metadatos específicos del instrumento (opcional) ──────────────────
    especifico: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Estructura interna del instrumento según su tipo. "
            "Encuesta: dimensiones e ítems. "
            "Entrevista: guión temático. "
            "Prueba: áreas de competencia."
        ),
    )


class VisibilidadUpdate(BaseModel):
    """Cambio de visibilidad público/privado."""
    visibilidad: Visibilidad


# ---------------------------------------------------------------------------
# Schemas de salida — Catálogo (pantalla de listado)
# ---------------------------------------------------------------------------

class InstrumentoResumen(BaseModel):
    """
    Representación mínima para la tabla del catálogo.

    Campos expuestos: los que la interfaz muestra en columnas y badges.
    No incluye rutas de disco ni metadatos semánticos completos.
    """

    instrumento_id:   int
    nombre:           str
    tipo_instrumento: TipoInstrumento
    estado:           EstadoPipeline
    visibilidad:      Visibilidad
    version:          int
    creado_en:        datetime
    propietario:      str | None = Field(
        default=None,
        description="Nombre de usuario (usuarios.usuario) del propietario.",
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Schemas de salida — Detalle del instrumento
# ---------------------------------------------------------------------------

class InstrumentoDetalle(InstrumentoResumen):
    """
    Representación completa para la pantalla de detalle.

    Extiende InstrumentoResumen con los campos adicionales que muestra
    la pantalla de detalle.

    Campos de información del procesamiento visibles:
      - fecha_procesamiento  → cuándo cambió de estado por última vez
      - error_detalle        → mensaje amigable si estado = 'error'

    Campos que NO se exponen (exclusivos del pipeline):
      - ruta_texto_limpio    → uso interno del pipeline de estandarización
      - schema_version       → uso interno del sistema de migración del JSON
      - pipeline_limpieza_log → ningún campo de esta tabla llega aquí
    """

    fecha_procesamiento: datetime

    # Información de procesamiento visible (solo si estado = 'error')
    error_detalle: str | None = Field(
        default=None,
        description=(
            "Mensaje amigable que explica qué salió mal. "
            "Presente solo cuando estado = 'error'."
        ),
    )

    # Metadatos semánticos — leídos del JSON canónico en disco.
    # None si el instrumento aún no alcanzó estado 'estandarizado'.
    metadatos_canonicos: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Contenido del JSON canónico (dublin_core, contexto, kpis_inferidos, "
            "unidades_semanticas). None si estado es 'recibido' o 'limpio'."
        ),
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Schemas de salida — Artefactos descargables
# ---------------------------------------------------------------------------

class ArtefactosDisponibles(BaseModel):
    """
    Indica qué artefactos existen para un instrumento dado.
    La interfaz usa esto para decidir qué botones de descarga mostrar.
    """

    instrumento_id:     int
    archivo_original:   bool = Field(
        default=True,
        description="Siempre disponible desde estado 'recibido'.",
    )
    json_canonico:      bool = Field(
        default=False,
        description="Disponible desde estado 'estandarizado'.",
    )
    sav:                bool = Field(
        default=False,
        description="Disponible desde estado 'estandarizado', solo para encuestas.",
    )


# ---------------------------------------------------------------------------
# Schemas de salida — Historial de versiones
# ---------------------------------------------------------------------------

class VersionInfo(BaseModel):
    """
    Representa una versión del archivo físico del instrumento.
    Mostrado en la sección 'Versiones' de la pantalla de detalle.

    Campos visibles para el propietario:
      - numero_version   → orden cronológico (1, 2, 3…)
      - nombre_original  → nombre del archivo tal como fue subido
      - tipo_mime        → tipo del archivo
      - tamano_bytes     → tamaño en bytes para mostrar al usuario
      - subido           → fecha y hora de la carga

    Campos que NO se exponen:
      - raw_archivo      → ruta interna en disco
      - hash_md5         → uso interno de detección de duplicados
      - tipo_de_instrumento → dato histórico interno
    """

    raw_data_id:     int
    numero_version:  int
    nombre_original: str
    tipo_mime:       str | None
    tamano_bytes:    int
    subido:          datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Schemas de respuesta — Operaciones de escritura
# ---------------------------------------------------------------------------

class CargaResponse(BaseModel):
    """Respuesta al crear un instrumento o cargar una nueva versión."""
    instrumento_id: int
    version:        int
    estado:         EstadoPipeline
    visibilidad:    Visibilidad
    mensaje:        str


class OperacionResponse(BaseModel):
    """Respuesta genérica para operaciones de actualización (PATCH)."""
    instrumento_id: int
    mensaje:        str


# ---------------------------------------------------------------------------
# Schemas de entrada — Filtros del catálogo
# ---------------------------------------------------------------------------

class FiltrosInstrumento(BaseModel):
    """
    Parámetros de query para GET /instrumentos.
    Se declaran como Query params en el router, no como body.

    Sin filtro de estado: el estado es información operativa del pipeline,
    no un criterio de búsqueda para los investigadores.
    """

    q:                str | None             = Field(
        default=None,
        description="Búsqueda de texto libre en el nombre del instrumento.",
    )
    tipo_instrumento: TipoInstrumento | None = Field(
        default=None,
        description="Filtrar por tipo: encuesta, entrevista o prueba_estandarizada.",
    )
    propietario:      str | None             = Field(
        default=None,
        description="Nombre de usuario del propietario (búsqueda parcial).",
    )
    visibilidad:      Visibilidad | None     = Field(
        default=None,
        description="Filtrar por visibilidad. None muestra públicos + propios.",
    )
    fecha_desde:      date | None            = Field(
        default=None,
        description="Incluye instrumentos cargados a partir de esta fecha (creado_en ≥ fecha_desde).",
    )
    fecha_hasta:      date | None            = Field(
        default=None,
        description="Incluye instrumentos cargados hasta esta fecha (creado_en ≤ fecha_hasta).",
    )
    solo_propios:     bool                   = Field(
        default=False,
        description="Si True, devuelve solo los instrumentos del usuario autenticado.",
    )
    skip:             int                    = Field(default=0, ge=0)
    limit:            int                    = Field(default=20, ge=1, le=100)
