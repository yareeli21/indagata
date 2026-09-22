# survey_intelligence/contracts/request.py
"""
Contrato de ENTRADA del SIS: SurveyIngestionRequest.

El SIS recibe bytes + metadatos, nunca rutas de disco ni acceso a BD.
Los 13 metadatos Dublin Core usan los mismos nombres que MetadatosDC del host
para permitir un mapeo 1:1 (design.md §5.1).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.codebook import CodebookModel

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class DublinCoreMetadata(BaseModel):
    """Los 13 campos Dublin Core, alineados con el modelo MetadatosDC del host."""
    model_config = _FROZEN

    dc_title: str
    dc_creator: str
    dc_subject: list[str]
    dc_description: str
    dc_publisher: str
    dc_date: str
    dc_type: str
    dc_format: str
    dc_language: str
    dc_coverage: str
    dc_rights: str
    dc_source: str | None = None
    dc_relation: str | None = None


class SurveyFile(BaseModel):
    """
    El archivo del instrumento.

    - Vía encuesta (tabular): file_bytes_b64 con el CSV/XLSX.
    - Vía documento (narrativa): extracted_text con el texto ya extraído por el host
      (entrevistas/pruebas). Si se provee extracted_text, file_bytes_b64 puede ir vacío.
    """
    model_config = _FROZEN

    file_name: str
    file_bytes_b64: str = Field(default="", description="Contenido del archivo (CSV/XLSX) en base64.")
    mime_type: str
    sheet: str | None = Field(default=None, description="Hoja XLSX; None = primera hoja.")
    extracted_text: str | None = Field(
        default=None,
        description="Texto ya extraído (vía documento: entrevista/prueba). Lo provee el host.",
    )


class IngestionOptions(BaseModel):
    """Opciones de procesamiento. Valores por defecto operan sin infraestructura externa."""
    model_config = _FROZEN

    # Tipo de instrumento -> elige la vía (encuesta: tabular; entrevista/prueba: documento).
    instrument_type: str = "encuesta"
    run_methodology_audit: bool = True
    language_hint: str = "es"
    max_rows_profiled: int = 50_000
    llm_temperature: float = 0.1
    # Rediseño v2 (encuestas): si True, S2 reagrupa columnas en preguntas lógicas
    # (questions[]) además de derivar variables[] de compatibilidad. Default OFF:
    # con la bandera apagada, el pipeline se comporta exactamente como hoy.
    question_grouping: bool = False


class SurveyIngestionRequest(BaseModel):
    """
    Contrato único de entrada al SIS.

    Attributes:
        request_id: Identificador de correlación provisto por el host.
        survey:     El archivo de encuesta (bytes en base64).
        metadata:   Los 13 metadatos Dublin Core.
        codebook:   Diccionario estructurado opcional (encuestas). Resolución
                    determinística en S5, sin RAG.
        options:    Configuración del procesamiento.
    """
    model_config = _FROZEN

    request_id: str
    survey: SurveyFile
    metadata: DublinCoreMetadata
    codebook: CodebookModel | None = None
    options: IngestionOptions = Field(default_factory=IngestionOptions)
