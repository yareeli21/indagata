"""Esquemas Pydantic compartidos (DTOs alineados 1:1 con la base de datos).

Hay un módulo por tabla de `infrastructure/postgres/init/01_schema.sql`
(fuente única de verdad). Cada módulo define el patrón habitual de una
arquitectura FastAPI por microservicios:

  - ``<Entidad>Base``   : campos comunes de entrada (sin PK ni columnas que
                          genera la base de datos).
  - ``<Entidad>Create`` : payload de alta.
  - ``<Entidad>Update`` : actualización parcial (todos los campos opcionales).
  - ``<Entidad>Read``   : representación de salida (incluye PK y timestamps,
                          con ``from_attributes=True`` para serializar modelos
                          ORM directamente).

Los nombres transversales históricos (``UsuarioRead``, ``InstrumentoRead``,
``MetadatosDCBase``, ``KPIRead``) se mantienen para no romper los servicios que
ya los importan desde ``shared.schemas``.
"""
from __future__ import annotations

from shared.schemas.coleccion_vectorial import (
    ColeccionVectorialBase,
    ColeccionVectorialCreate,
    ColeccionVectorialRead,
    ColeccionVectorialUpdate,
)
from shared.schemas.documento_vectorizado import (
    DocumentoVectorizadoBase,
    DocumentoVectorizadoCreate,
    DocumentoVectorizadoRead,
    DocumentoVectorizadoUpdate,
)
from shared.schemas.instrumento_procesado import (
    EstadoInstrumento,
    InstrumentoProcesadoBase,
    InstrumentoProcesadoCreate,
    InstrumentoProcesadoRead,
    InstrumentoProcesadoUpdate,
)
from shared.schemas.kpi import KPIBase, KPICreate, KPIRead, KPIUpdate
from shared.schemas.kpi_inferido import (
    KPIInferidoBase,
    KPIInferidoCreate,
    KPIInferidoRead,
    KPIInferidoUpdate,
)
from shared.schemas.kpi_inferido_chunk import (
    KpiInferidoChunkBase,
    KpiInferidoChunkCreate,
    KpiInferidoChunkRead,
)
from shared.schemas.kpi_variable import (
    KPIVariableBase,
    KPIVariableCreate,
    KPIVariableRead,
)
from shared.schemas.metadatos_dc import (
    MetadatosDCBase,
    MetadatosDCCreate,
    MetadatosDCRead,
    MetadatosDCUpdate,
)
from shared.schemas.metadatos_encuestas import (
    MetadatosEncuestasBase,
    MetadatosEncuestasCreate,
    MetadatosEncuestasRead,
    MetadatosEncuestasUpdate,
)
from shared.schemas.metadatos_entrevistas import (
    MetadatosEntrevistasBase,
    MetadatosEntrevistasCreate,
    MetadatosEntrevistasRead,
    MetadatosEntrevistasUpdate,
)
from shared.schemas.metadatos_pruebasestandarizadas import (
    MetadatosPruebasBase,
    MetadatosPruebasCreate,
    MetadatosPruebasRead,
    MetadatosPruebasUpdate,
)
from shared.schemas.prompt import PromptBase, PromptCreate, PromptRead, PromptUpdate
from shared.schemas.rag_log import RagLogBase, RagLogCreate, RagLogRead
from shared.schemas.raw_data import (
    RawDataBase,
    RawDataCreate,
    RawDataRead,
    RawDataUpdate,
)
from shared.schemas.usuario import (
    UsuarioBase,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)
from shared.schemas.valor_variable_inferido import (
    ValorVariableInferidoBase,
    ValorVariableInferidoCreate,
    ValorVariableInferidoRead,
    ValorVariableInferidoUpdate,
)
from shared.schemas.variable import (
    VariableBase,
    VariableCreate,
    VariableRead,
    VariableUpdate,
)

# ── Alias de compatibilidad ──────────────────────────────────────────────────
# `InstrumentoRead` era el nombre histórico del DTO de salida de instrumento.
InstrumentoRead = InstrumentoProcesadoRead

__all__ = [
    # usuario
    "UsuarioBase",
    "UsuarioCreate",
    "UsuarioUpdate",
    "UsuarioRead",
    # raw_data
    "RawDataBase",
    "RawDataCreate",
    "RawDataUpdate",
    "RawDataRead",
    # instrumento_procesado
    "EstadoInstrumento",
    "InstrumentoProcesadoBase",
    "InstrumentoProcesadoCreate",
    "InstrumentoProcesadoUpdate",
    "InstrumentoProcesadoRead",
    "InstrumentoRead",  # alias de compatibilidad
    # metadatos_dc
    "MetadatosDCBase",
    "MetadatosDCCreate",
    "MetadatosDCUpdate",
    "MetadatosDCRead",
    # metadatos_encuestas
    "MetadatosEncuestasBase",
    "MetadatosEncuestasCreate",
    "MetadatosEncuestasUpdate",
    "MetadatosEncuestasRead",
    # metadatos_entrevistas
    "MetadatosEntrevistasBase",
    "MetadatosEntrevistasCreate",
    "MetadatosEntrevistasUpdate",
    "MetadatosEntrevistasRead",
    # metadatos_pruebas
    "MetadatosPruebasBase",
    "MetadatosPruebasCreate",
    "MetadatosPruebasUpdate",
    "MetadatosPruebasRead",
    # coleccion_vectorial
    "ColeccionVectorialBase",
    "ColeccionVectorialCreate",
    "ColeccionVectorialUpdate",
    "ColeccionVectorialRead",
    # prompt
    "PromptBase",
    "PromptCreate",
    "PromptUpdate",
    "PromptRead",
    # kpi
    "KPIBase",
    "KPICreate",
    "KPIUpdate",
    "KPIRead",
    # variable
    "VariableBase",
    "VariableCreate",
    "VariableUpdate",
    "VariableRead",
    # kpi_variable
    "KPIVariableBase",
    "KPIVariableCreate",
    "KPIVariableRead",
    # kpi_inferido
    "KPIInferidoBase",
    "KPIInferidoCreate",
    "KPIInferidoUpdate",
    "KPIInferidoRead",
    # valor_variable_inferido
    "ValorVariableInferidoBase",
    "ValorVariableInferidoCreate",
    "ValorVariableInferidoUpdate",
    "ValorVariableInferidoRead",
    # rag_log
    "RagLogBase",
    "RagLogCreate",
    "RagLogRead",
    # documento_vectorizado
    "DocumentoVectorizadoBase",
    "DocumentoVectorizadoCreate",
    "DocumentoVectorizadoUpdate",
    "DocumentoVectorizadoRead",
    # kpi_inferido_chunk
    "KpiInferidoChunkBase",
    "KpiInferidoChunkCreate",
    "KpiInferidoChunkRead",
]
