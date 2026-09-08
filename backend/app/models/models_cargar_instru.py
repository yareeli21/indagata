# cargar_instru/models.py
"""
Modelos ORM para el módulo de gestión de instrumentos.

Tablas cubiertas:
  - instrumento_procesado  → registro operativo del instrumento
  - raw_data               → historial de archivos físicos por versión
  - permiso_instrumento    → propietario del instrumento
  - pipeline_limpieza_log  → trazabilidad de cada ejecución del pipeline

El modelo Usuario se define aquí solo como referencia de lectura.
La gestión de usuarios es responsabilidad del módulo de autenticación.

Esquema PostgreSQL: tt_rag
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


# ---------------------------------------------------------------------------
# Constantes de dominio
# ---------------------------------------------------------------------------

TIPOS_INSTRUMENTO = ("encuesta", "entrevista", "prueba_estandarizada")
ESTADOS_PIPELINE  = ("recibido", "limpio", "estandarizado", "vectorizado", "error")
VISIBILIDADES     = ("publico", "privado")
RESULTADOS_LOG    = ("en_proceso", "exitoso", "error")


# ---------------------------------------------------------------------------
# Paso 1 — Usuario
# Modelo de solo lectura en este módulo.
# La creación y autenticación de usuarios está en otro módulo.
# ---------------------------------------------------------------------------

class Usuario(Base):
    """
    Referencia a la tabla tt_rag.usuarios.
    Solo se lee desde este módulo para resolver el nombre del propietario.
    """
    __tablename__ = "usuarios"
    __table_args__ = ({"schema": "tt_rag"},)

    usuario_id:    Mapped[int]      = mapped_column(Integer, primary_key=True)
    usuario:       Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str]      = mapped_column(String(255), nullable=False)
    creado_en:     Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# Paso 2 — InstrumentoProcesado
# Registro operativo maestro del instrumento.
# No almacena metadatos semánticos — esos viven en storage/json/{id}.json.
# ---------------------------------------------------------------------------

class InstrumentoProcesado(Base):
    """
    Registro operativo de un instrumento de investigación.

    Información que almacena:
      - Identificación básica: nombre, tipo, versión.
      - Estado del pipeline: recibido → limpio → estandarizado → vectorizado.
      - Visibilidad de acceso: publico (default) | privado.
      - Rutas a los artefactos generados en disco:
          · ruta_texto_limpio → disponible desde estado 'limpio' (uso exclusivo del pipeline)
          · ruta_json         → disponible desde estado 'estandarizado' (interfaz + pipeline)
          · ruta_sav          → disponible desde estado 'estandarizado', solo encuestas
      - Trazabilidad de errores del pipeline.

    Información que NO almacena (vive en el JSON canónico en disco):
      - Metadatos Dublin Core completos.
      - Bloque contexto semántico.
      - KPIs inferidos, unidades semánticas.
      - Información de limpieza (modelo LLM, extractores, hashes).
        → Esa trazabilidad está en pipeline_limpieza_log.
    """
    __tablename__ = "instrumento_procesado"
    __table_args__ = (
        CheckConstraint(
            f"tipo_instrumento IN {TIPOS_INSTRUMENTO}",
            name="ck_tipo_instrumento",
        ),
        CheckConstraint(
            f"estado IN {ESTADOS_PIPELINE}",
            name="ck_estado_instrumento",
        ),
        CheckConstraint(
            f"visibilidad IN {VISIBILIDADES}",
            name="ck_visibilidad",
        ),
        {"schema": "tt_rag"},
    )

    # ── Identificación ────────────────────────────────────────────────────
    instrumento_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre descriptivo del instrumento. Se actualiza si dublin_core.dc_title cambia.",
    )

    tipo_instrumento: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="encuesta | entrevista | prueba_estandarizada",
    )

    plataforma: Mapped[str | None] = mapped_column(
        String(50),
        comment="Plataforma de origen, si aplica.",
    )

    # ── Estado y visibilidad ──────────────────────────────────────────────
    estado: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="recibido",
        comment="recibido | limpio | estandarizado | vectorizado | error",
    )

    visibilidad: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="publico",
        comment="publico (default) | privado. El investigador lo cambia explícitamente.",
    )

    # ── Versionado ────────────────────────────────────────────────────────
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Número de versión del archivo físico. Se incrementa con cada POST /versiones.",
    )

    schema_version: Mapped[str | None] = mapped_column(
        String(10),
        default="1.0",
        comment="Versión del schema del JSON canónico. Permite migraciones futuras.",
    )

    # ── Rutas a artefactos en disco ───────────────────────────────────────
    ruta_json: Mapped[str | None] = mapped_column(
        Text,
        comment=(
            "Ruta relativa al JSON canónico en storage/json/{id}.json. "
            "NULL hasta que el instrumento alcanza estado estandarizado."
        ),
    )

    ruta_sav: Mapped[str | None] = mapped_column(
        Text,
        comment=(
            "Ruta relativa al .sav en storage/sav/{id}.sav. "
            "Solo para encuestas a partir del estado estandarizado."
        ),
    )

    ruta_texto_limpio: Mapped[str | None] = mapped_column(
        Text,
        comment=(
            "Ruta relativa al texto limpio en storage/data/{id}_limpio.txt. "
            "Los pipelines de KPI y chunking leen este archivo directamente."
        ),
    )

    # ── Trazabilidad de errores ───────────────────────────────────────────
    error_detalle: Mapped[str | None] = mapped_column(
        Text,
        comment="Descripción del error cuando estado = 'error'. NULL en flujo exitoso.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    fecha_procesamiento: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Se actualiza en cada cambio de estado del pipeline.",
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Fecha de creación del instrumento. Nunca cambia. Usada en filtros del catálogo.",
    )

    # ── Relaciones ────────────────────────────────────────────────────────
    raw_versions: Mapped[list[RawData]] = relationship(
        "RawData",
        back_populates="instrumento",
        cascade="all, delete-orphan",
        order_by="RawData.raw_data_id",
    )

    permiso: Mapped[PermisoInstrumento | None] = relationship(
        "PermisoInstrumento",
        back_populates="instrumento",
        cascade="all, delete-orphan",
        uselist=False,  # uno a uno: cada instrumento tiene exactamente un propietario
    )

    logs_limpieza: Mapped[list[PipelineLimpiezaLog]] = relationship(
        "PipelineLimpiezaLog",
        back_populates="instrumento",
        cascade="all, delete-orphan",
        order_by="PipelineLimpiezaLog.iniciado_en",
    )


# ---------------------------------------------------------------------------
# Paso 3 — RawData
# Historial de archivos físicos del instrumento.
# Cada versión cargada crea un nuevo registro. Los anteriores no se borran.
# ---------------------------------------------------------------------------

class RawData(Base):
    """
    Registro de un archivo físico asociado a un instrumento.

    Un instrumento puede tener múltiples registros (uno por versión).
    El registro con el mayor raw_data_id es la versión actual.

    La unicidad de hash_md5 es por (hash_md5, usuario_id), no global.
    Dos investigadores distintos pueden subir el mismo archivo.
    Un mismo investigador no puede subir el mismo archivo dos veces
    para el mismo instrumento.
    """
    __tablename__ = "raw_data"
    __table_args__ = (
        # Un mismo usuario no puede tener el mismo archivo dos veces
        # en la misma versión de un instrumento.
        # Nota: el UNIQUE global de hash_md5 del esquema original
        # debe eliminarse y reemplazarse por este índice compuesto.
        UniqueConstraint("hash_md5", "usuario_id", name="uq_raw_data_hash_usuario"),
        {"schema": "tt_rag"},
    )

    # ── Identificación ────────────────────────────────────────────────────
    raw_data_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    instrumento_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tt_rag.usuarios.usuario_id"),
        nullable=False,
        comment="Investigador que subió esta versión del archivo.",
    )

    # ── Datos del archivo ─────────────────────────────────────────────────
    tipo_de_instrumento: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Copia del tipo al momento de la carga. Para historial.",
    )

    raw_archivo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ruta relativa al archivo desde PROJECT_ROOT. Ej: storage/raw/42_1722000000_a1b2c3d4.pdf",
    )

    nombre_original: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Nombre del archivo tal como lo subió el investigador. Para la descarga.",
    )

    tipo_mime: Mapped[str | None] = mapped_column(
        String(100),
        comment="MIME type detectado por el cliente. Ej: application/pdf",
    )

    tamano_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Tamaño real del archivo en bytes.",
    )

    hash_md5: Mapped[str | None] = mapped_column(
        String(32),
        comment="Hash MD5 del contenido del archivo. Detecta duplicados por usuario.",
    )

    # ── Timestamp ─────────────────────────────────────────────────────────
    subido: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="Cuándo fue subido este archivo.",
    )

    # ── Relaciones ────────────────────────────────────────────────────────
    instrumento: Mapped[InstrumentoProcesado] = relationship(
        "InstrumentoProcesado",
        back_populates="raw_versions",
    )


# ---------------------------------------------------------------------------
# Paso 4 — PermisoInstrumento
# Registra quién es el propietario de cada instrumento.
# Solo existe el rol 'propietario'. No hay colaboradores ni lectores.
# La visibilidad público/privado cubre el control de lectura.
# ---------------------------------------------------------------------------

class PermisoInstrumento(Base):
    """
    Propietario de un instrumento.

    Se crea automáticamente al hacer POST /instrumentos.
    No se modifica manualmente.
    Se elimina en cascada si el instrumento es eliminado.

    Diseño simplificado:
      - Solo existe el rol 'propietario'.
      - La visibilidad del instrumento (publico/privado) controla
        quién puede leerlo. Esta tabla solo controla quién puede
        modificarlo, eliminarlo o subir nuevas versiones.
    """
    __tablename__ = "permiso_instrumento"
    __table_args__ = (
        CheckConstraint("rol = 'propietario'", name="ck_rol_solo_propietario"),
        UniqueConstraint("instrumento_id", "usuario_id", name="uq_permiso_instrumento_usuario"),
        {"schema": "tt_rag"},
    )

    permiso_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    instrumento_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tt_rag.usuarios.usuario_id", ondelete="CASCADE"),
        nullable=False,
        comment="Propietario del instrumento.",
    )

    rol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="propietario",
        comment="Siempre 'propietario'. El CHECK garantiza que no existan otros valores.",
    )

    otorgado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Cuándo se creó el instrumento (y se asignó el propietario).",
    )

    # ── Relaciones ────────────────────────────────────────────────────────
    instrumento: Mapped[InstrumentoProcesado] = relationship(
        "InstrumentoProcesado",
        back_populates="permiso",
    )


# ---------------------------------------------------------------------------
# Paso 5 — PipelineLimpiezaLog
# Trazabilidad de cada ejecución del pipeline de limpieza.
# Tres propósitos:
#   1. Lock optimista: resultado='en_proceso' bloquea doble procesamiento.
#   2. Trazabilidad: modelo LLM, prompt, extractor, tokens, latencia.
#   3. Diagnóstico de errores: mensaje detallado sin contaminar la tabla principal.
#
# NOTA: el bloque 'limpieza' fue removido del JSON canónico.
# Toda la información operativa del pipeline vive aquí.
# ---------------------------------------------------------------------------

class PipelineLimpiezaLog(Base):
    """
    Registro de una ejecución del pipeline de limpieza sobre un instrumento.

    EXCLUSIVAMENTE INTERNO DEL PIPELINE. La interfaz de usuario no consulta
    esta tabla en ningún momento. Sus tres propósitos son:
      1. Lock optimista: resultado='en_proceso' bloquea doble procesamiento.
      2. Trazabilidad y auditoría: modelo LLM, prompt, extractor, tokens, latencia.
      3. Diagnóstico técnico: error_mensaje con detalle completo del fallo.

    La interfaz solo muestra instrumento_procesado.error_detalle (mensaje amigable).
    error_mensaje de esta tabla es para monitoreo técnico, nunca para el investigador.
    """
    __tablename__ = "pipeline_limpieza_log"
    __table_args__ = (
        CheckConstraint(
            f"resultado IN {RESULTADOS_LOG}",
            name="ck_resultado_limpieza",
        ),
        {"schema": "tt_rag"},
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    instrumento_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Estado de la ejecución ────────────────────────────────────────────
    iniciado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    finalizado_en: Mapped[datetime | None] = mapped_column(
        DateTime,
        comment="NULL mientras resultado = 'en_proceso'.",
    )

    resultado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="en_proceso",
        comment="en_proceso | exitoso | error",
    )

    # ── Trazabilidad técnica del pipeline ─────────────────────────────────
    extractor_usado: Mapped[str | None] = mapped_column(
        String(50),
        comment="Biblioteca usada para extraer texto. Ej: 'pypdf', 'python-docx', 'openpyxl'.",
    )

    modelo_llm: Mapped[str | None] = mapped_column(
        String(100),
        comment="Modelo Ollama usado para limpiar el texto. Ej: 'llama3.1:8b'.",
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(20),
        comment="Versión del prompt activo en la tabla prompt al momento de la ejecución.",
    )

    texto_extraido_hash: Mapped[str | None] = mapped_column(
        String(32),
        comment=(
            "Hash MD5 del texto crudo extraído del archivo. "
            "Permite verificar que el texto limpio corresponde a una versión específica "
            "del archivo, incluso después de eliminar los archivos temporales."
        ),
    )

    # ── Métricas de la llamada al LLM ─────────────────────────────────────
    tokens_entrada: Mapped[int | None] = mapped_column(
        Integer,
        comment="Aproximación de tokens enviados al LLM (conteo de palabras del prompt).",
    )

    tokens_salida: Mapped[int | None] = mapped_column(
        Integer,
        comment="Aproximación de tokens recibidos del LLM (conteo de palabras de la respuesta).",
    )

    latencia_ms: Mapped[int | None] = mapped_column(
        Integer,
        comment="Tiempo total de la llamada al LLM en milisegundos.",
    )

    segmentos: Mapped[int | None] = mapped_column(
        Integer,
        comment=(
            "Número de segmentos en que se dividió el texto si superó el umbral. "
            "1 si no hubo segmentación."
        ),
    )

    # ── Diagnóstico de errores ────────────────────────────────────────────
    error_mensaje: Mapped[str | None] = mapped_column(
        Text,
        comment="Mensaje detallado del error si resultado = 'error'. NULL en flujo exitoso.",
    )

    # ── Relaciones ────────────────────────────────────────────────────────
    instrumento: Mapped[InstrumentoProcesado] = relationship(
        "InstrumentoProcesado",
        back_populates="logs_limpieza",
    )
