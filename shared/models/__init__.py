"""Modelos ORM compartidos.

Importar este paquete registra TODAS las tablas en `Base.metadata`, de modo
que SQLAlchemy conoce el mapa completo sin importar qué servicio lo cargue.
Refleja 1:1 el esquema de `infrastructure/postgres/init/01_schema.sql`.
"""
from shared.models.usuario import Usuario
from shared.models.raw_data import RawData
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.metadatos_dc import MetadatosDC
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.metadatos_entrevistas import MetadatosEnriquecidosEntrevistas
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas
from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.prompt import Prompt
from shared.models.kpi import KPI
from shared.models.variable import Variable
from shared.models.kpi_variable import KPIVariable
from shared.models.kpi_inferido import KPIInferido
from shared.models.valor_variable_inferido import ValorVariableInferido
from shared.models.rag_log import RagLog
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.kpi_inferido_chunk import KpiInferidoChunk

__all__ = [
    "Usuario",
    "RawData",
    "InstrumentoProcesado",
    "MetadatosDC",
    "MetadatosEnriquecidosEncuestas",
    "MetadatosEnriquecidosEntrevistas",
    "MetadatosEnriquecidosPruebas",
    "ColeccionVectorial",
    "Prompt",
    "KPI",
    "Variable",
    "KPIVariable",
    "KPIInferido",
    "ValorVariableInferido",
    "RagLog",
    "DocumentoVectorizado",
    "KpiInferidoChunk",
]
