# app/models/models_instrumentos.py
"""
Modelos ORM — Módulo de instrumentos de investigación.

Todas las tablas del schema tt_rag que usa este módulo viven aquí.
Este archivo es compartido por los dos módulos funcionales:
  - Carga de instrumentos  (routers/routers_carga.py)
  - Visualización          (routers/routers_visualizacion.py)

No se duplican modelos: InstrumentoProcesado es el centro de ambos flujos.

Tablas expuestas a la interfaz:
  instrumento_procesado, metadatos_dc, kpi_inferido,
  etl_propuesta, metadatos_enriquecidos,
  permiso_instrumento, usuarios

Tabla exclusivamente interna del pipeline:
  pipeline_ingesta_log  (nunca se expone en endpoints)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.base import Base

# ---------------------------------------------------------------------------
# Constantes de dominio — fuente única en api/core/domain_constants.py
# Se re-exportan aquí (y en api/models/__init__.py) por compatibilidad.
# ---------------------------------------------------------------------------

from api.core.domain_constants import (  # noqa: E402
    DECISIONES_PROPUESTA,
    ESTADOS_PIPELINE,
    IMPROVEMENT_ESTADOS,
    IMPROVEMENT_SCOPES,
    RESULTADOS_LOG,
    TIPOS_INSTRUMENTO,
    TIPOS_PROPUESTA,
)


# ---------------------------------------------------------------------------
# Usuario — solo lectura en este módulo
# ---------------------------------------------------------------------------

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = ({"schema": "tt_rag"},)

    usuario_id:    Mapped[int]      = mapped_column(Integer, primary_key=True)
    usuario:       Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str]      = mapped_column(String(255), nullable=False)
    creado_en:     Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# KPI — catálogo maestro de indicadores
# ---------------------------------------------------------------------------

class KPI(Base):
    __tablename__ = "kpi"
    __table_args__ = ({"schema": "tt_rag"},)

    kpi_id:            Mapped[int]           = mapped_column(Integer, primary_key=True)
    nombrekpi:         Mapped[str]           = mapped_column(String(255), nullable=False)
    descripcion:       Mapped[str | None]    = mapped_column(Text)
    direccion_deseada: Mapped[str | None]    = mapped_column(Text)
    razon:             Mapped[str | None]    = mapped_column(Text)
    formula:           Mapped[str | None]    = mapped_column(Text)
    umbral_bajo:       Mapped[float | None]  = mapped_column(Numeric)
    umbral_medio:      Mapped[float | None]  = mapped_column(Numeric)
    umbral_alto:       Mapped[float | None]  = mapped_column(Numeric)
    unidad:            Mapped[str | None]    = mapped_column(Text)
    activo:            Mapped[bool]          = mapped_column(Integer, nullable=False, server_default=text("1"))


# ---------------------------------------------------------------------------
# InstrumentoProcesado — registro maestro
# ---------------------------------------------------------------------------

class InstrumentoProcesado(Base):
    __tablename__ = "instrumento_procesado"
    __table_args__ = (
        CheckConstraint(f"tipo_instrumento IN {TIPOS_INSTRUMENTO}", name="ck_tipo_instrumento"),
        CheckConstraint(f"estado IN {ESTADOS_PIPELINE}", name="ck_estado_instrumento"),
        {"schema": "tt_rag"},
    )

    instrumento_id:      Mapped[int]           = mapped_column(Integer, primary_key=True)
    nombre:              Mapped[str]           = mapped_column(String(255), nullable=False)
    tipo_instrumento:    Mapped[str]           = mapped_column(String(30), nullable=False)
    plataforma:          Mapped[str | None]    = mapped_column(String(50))
    estado:              Mapped[str]           = mapped_column(String(50), nullable=False, default="pendiente")
    ruta_archivo:        Mapped[str | None]    = mapped_column(Text)
    ruta_json:           Mapped[str | None]    = mapped_column(Text)
    ruta_sav:            Mapped[str | None]    = mapped_column(Text)
    ruta_texto_limpio:   Mapped[str | None]    = mapped_column(Text)
    ruta_codebook:       Mapped[str | None]    = mapped_column(Text)
    error_detalle:       Mapped[str | None]    = mapped_column(Text)
    schema_version:      Mapped[str | None]    = mapped_column(String(10), default="2.0")
    creado_en:           Mapped[datetime]      = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_procesamiento: Mapped[datetime]      = mapped_column(DateTime, nullable=False, server_default=func.now())

    metadatos_dc: Mapped[MetadatosDC | None] = relationship(
        "MetadatosDC", back_populates="instrumento", cascade="all, delete-orphan", uselist=False,
    )
    kpis_inferidos: Mapped[list[KpiInferido]] = relationship(
        "KpiInferido", back_populates="instrumento", cascade="all, delete-orphan",
    )
    propuestas_etl: Mapped[list[EtlPropuesta]] = relationship(
        "EtlPropuesta", back_populates="instrumento", cascade="all, delete-orphan",
        order_by="EtlPropuesta.propuesta_id",
    )
    metadatos_enriquecidos: Mapped[MetadatosEnriquecidos | None] = relationship(
        "MetadatosEnriquecidos", back_populates="instrumento", cascade="all, delete-orphan", uselist=False,
    )
    permiso: Mapped[PermisoInstrumento | None] = relationship(
        "PermisoInstrumento", back_populates="instrumento", cascade="all, delete-orphan", uselist=False,
    )
    logs_pipeline: Mapped[list[PipelineIngestaLog]] = relationship(
        "PipelineIngestaLog", back_populates="instrumento", cascade="all, delete-orphan",
        order_by="PipelineIngestaLog.iniciado_en",
    )


# ---------------------------------------------------------------------------
# MetadatosDC — 13 campos Dublin Core obligatorios + 2 opcionales
# ---------------------------------------------------------------------------

class MetadatosDC(Base):
    __tablename__ = "metadatos_dc"
    __table_args__ = (
        UniqueConstraint("instrumento_id", name="uq_metadatos_dc_instrumento"),
        {"schema": "tt_rag"},
    )

    metadatos_id:   Mapped[int]       = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int]       = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    
    # 13 campos Dublin Core obligatorios
    dc_title:       Mapped[str]       = mapped_column(Text, nullable=False)
    dc_creator:     Mapped[str]       = mapped_column(Text, nullable=False)
    dc_subject:     Mapped[str]       = mapped_column(Text, nullable=False, comment="JSON array: '[\"tema1\"]'")
    dc_description: Mapped[str]       = mapped_column(Text, nullable=False)
    dc_publisher:   Mapped[str]       = mapped_column(Text, nullable=False)
    dc_date:        Mapped[str]       = mapped_column(String(20), nullable=False)
    dc_type:        Mapped[str]       = mapped_column(String(50), nullable=False)
    dc_format:      Mapped[str]       = mapped_column(String(50), nullable=False)
    dc_language:    Mapped[str]       = mapped_column(String(10), nullable=False)
    dc_coverage:    Mapped[str]       = mapped_column(Text, nullable=False)
    dc_rights:      Mapped[str]       = mapped_column(Text, nullable=False)
    dc_source:      Mapped[str | None] = mapped_column(Text)
    dc_relation:    Mapped[str | None] = mapped_column(Text)
    
    registrado_en:  Mapped[datetime]  = mapped_column(DateTime, nullable=False, server_default=func.now())

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="metadatos_dc")


# ---------------------------------------------------------------------------
# KpiInferido
# ---------------------------------------------------------------------------

class KpiInferido(Base):
    __tablename__ = "kpi_inferido"
    __table_args__ = (
        CheckConstraint("origen IN ('registro_manual', 'propuesta_etl')", name="ck_origen_kpi"),
        {"schema": "tt_rag"},
    )

    kpi_inferido_id:   Mapped[int]          = mapped_column(Integer, primary_key=True)
    instrumento_id:    Mapped[int]          = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    kpi_id:            Mapped[int]          = mapped_column(Integer, ForeignKey("tt_rag.kpi.kpi_id"), nullable=False)
    tipo_relacion:     Mapped[str | None]   = mapped_column(String(20))
    evidencia_textual: Mapped[str | None]   = mapped_column(Text)
    score_inferencia:  Mapped[float | None] = mapped_column(Numeric(4, 3))
    origen:            Mapped[str]          = mapped_column(String(20), nullable=False, default="registro_manual")
    registrado_en:     Mapped[datetime]     = mapped_column(DateTime, nullable=False, server_default=func.now())

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="kpis_inferidos")
    # Relación con el catálogo KPI para resolver el nombre sin SQL crudo ni N+1.
    # Solo lectura (viewonly): la FK ya la gestiona kpi_id; lazy="joined" evita consultas por fila.
    kpi: Mapped[KPI] = relationship("KPI", lazy="joined", viewonly=True)


# ---------------------------------------------------------------------------
# EtlPropuesta — propuestas del LLM y decisiones del usuario
# ---------------------------------------------------------------------------

class EtlPropuesta(Base):
    __tablename__ = "etl_propuesta"
    __table_args__ = (
        CheckConstraint(f"tipo IN {TIPOS_PROPUESTA}", name="ck_tipo_propuesta"),
        CheckConstraint(f"estado_decision IN {DECISIONES_PROPUESTA}", name="ck_estado_decision"),
        {"schema": "tt_rag"},
    )

    propuesta_id:     Mapped[int]              = mapped_column(Integer, primary_key=True)
    instrumento_id:   Mapped[int]              = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    tipo:             Mapped[str]              = mapped_column(String(30), nullable=False)
    descripcion:      Mapped[str]              = mapped_column(Text, nullable=False)
    accion_sugerida:  Mapped[str]              = mapped_column(Text, nullable=False)
    justificacion:    Mapped[str]              = mapped_column(Text, nullable=False)
    impacto_esperado: Mapped[str | None]       = mapped_column(Text)
    valor_original:   Mapped[str | None]       = mapped_column(Text)
    valor_propuesto:  Mapped[str | None]       = mapped_column(Text)
    estado_decision:  Mapped[str]              = mapped_column(String(20), nullable=False, default="pendiente")
    fecha_propuesta:  Mapped[datetime]         = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_decision:   Mapped[datetime | None]  = mapped_column(DateTime)

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="propuestas_etl")


# ---------------------------------------------------------------------------
# MetadatosEnriquecidos
# ---------------------------------------------------------------------------

class MetadatosEnriquecidos(Base):
    __tablename__ = "metadatos_enriquecidos"
    __table_args__ = (
        UniqueConstraint("instrumento_id", name="uq_metadatos_enriquecidos_instrumento"),
        {"schema": "tt_rag"},
    )

    enriquecido_id: Mapped[int]      = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int]      = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    metadatos:      Mapped[dict]     = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    registrado_en:  Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="metadatos_enriquecidos")


# ---------------------------------------------------------------------------
# PermisoInstrumento
# ---------------------------------------------------------------------------

class PermisoInstrumento(Base):
    __tablename__ = "permiso_instrumento"
    __table_args__ = (
        CheckConstraint("rol = 'propietario'", name="ck_rol_solo_propietario"),
        UniqueConstraint("instrumento_id", "usuario_id", name="uq_permiso_instrumento_usuario"),
        {"schema": "tt_rag"},
    )

    permiso_id:     Mapped[int]      = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int]      = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    usuario_id:     Mapped[int]      = mapped_column(
        Integer, ForeignKey("tt_rag.usuarios.usuario_id", ondelete="CASCADE"), nullable=False,
    )
    rol:            Mapped[str]      = mapped_column(String(20), nullable=False, default="propietario")
    otorgado_en:    Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="permiso")


# ---------------------------------------------------------------------------
# PipelineIngestaLog — solo interno, nunca expuesto en la interfaz
# ---------------------------------------------------------------------------

class PipelineIngestaLog(Base):
    __tablename__ = "pipeline_ingesta_log"
    __table_args__ = (
        CheckConstraint(f"resultado IN {RESULTADOS_LOG}", name="ck_resultado_ingesta"),
        {"schema": "tt_rag"},
    )

    log_id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
    instrumento_id:   Mapped[int]              = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    iniciado_en:      Mapped[datetime]         = mapped_column(DateTime, nullable=False, server_default=func.now())
    finalizado_en:    Mapped[datetime | None]  = mapped_column(DateTime)
    resultado:        Mapped[str]              = mapped_column(String(20), nullable=False, default="en_proceso")
    etapa_actual:     Mapped[str | None]       = mapped_column(String(50))
    modelo_llm:       Mapped[str | None]       = mapped_column(String(100))
    modelo_embedding: Mapped[str | None]       = mapped_column(String(100))
    n_chunks:         Mapped[int | None]       = mapped_column(Integer)
    error_mensaje:    Mapped[str | None]       = mapped_column(Text)

    instrumento: Mapped[InstrumentoProcesado] = relationship("InstrumentoProcesado", back_populates="logs_pipeline")


# ---------------------------------------------------------------------------
# ImprovementOpportunity — recomendaciones de mejora emitidas por el SIS
# (IMPROVEMENT_SCOPES / IMPROVEMENT_ESTADOS: fuente única en core/domain_constants.py)
# ---------------------------------------------------------------------------


class ImprovementOpportunity(Base):
    __tablename__ = "improvement_opportunity"
    __table_args__ = (
        CheckConstraint(f"scope IN {IMPROVEMENT_SCOPES}", name="ck_improvement_scope"),
        CheckConstraint(f"estado IN {IMPROVEMENT_ESTADOS}", name="ck_improvement_estado"),
        {"schema": "tt_rag"},
    )

    opportunity_id:     Mapped[int]           = mapped_column(Integer, primary_key=True)
    instrumento_id:     Mapped[int]           = mapped_column(
        Integer, ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"), nullable=False,
    )
    sis_opportunity_id: Mapped[str | None]    = mapped_column(Text)
    scope:              Mapped[str]           = mapped_column(String(30), nullable=False)
    titulo:             Mapped[str]           = mapped_column(Text, nullable=False)
    descripcion:        Mapped[str]           = mapped_column(Text, nullable=False)
    evidencia:          Mapped[list]          = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    proposed_rule:      Mapped[dict | None]   = mapped_column(JSONB)
    confianza:          Mapped[float | None]  = mapped_column(Numeric(4, 3))
    generado_por:       Mapped[str | None]    = mapped_column(String(60))
    estado:             Mapped[str]           = mapped_column(String(20), nullable=False, default="proposed")
    creado_en:          Mapped[datetime]      = mapped_column(DateTime, nullable=False, server_default=func.now())
