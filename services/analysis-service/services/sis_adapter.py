# services/sis_adapter.py
"""
Adaptador entre el HOST (INDAGATA) y el Survey Intelligence Service (SIS).

Este módulo es el ÚNICO punto de acople con el SIS. Aquí vive todo lo que el SIS no
debe conocer: cómo se llama a Ollama, cómo se leen los archivos, y cómo se mapea el
resultado a las tablas tt_rag.

Responsabilidades:
  - OllamaLLMAdapter: implementa LLMPort del SIS envolviendo enviar_mensaje_chat.
  - build_request(): construye SurveyIngestionRequest desde el instrumento del host.
  - load_kpi_catalog(): lee el catálogo tt_rag.kpi para la inferencia de KPIs.

El mapeo del resultado a EtlPropuesta/KpiInferido/JSON/.SAV vive en services_carga.py
(capa de negocio del host), no aquí, para mantener este adaptador delgado.
"""
from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.models_instrumentos import KPI, InstrumentoProcesado
from services.ollama_client import enviar_mensaje_chat

# El SIS se importa como bloque de Lego: solo su superficie pública.
from survey_intelligence import (
    SurveyIngestionRequest,
    SurveyIntelligenceService,
)
from survey_intelligence.contracts.request import (
    DublinCoreMetadata,
    IngestionOptions,
    SurveyFile,
)


class OllamaLLMAdapter:
    """
    Implementa LLMPort del SIS reutilizando el cliente Ollama del host.

    Pasa opciones de rendimiento a Ollama para VRAM limitada (GTX 1650, 4 GB):
      - num_predict: limita la salida (evita generación excesiva).
      - num_ctx:     ventana de contexto acotada (prompts comprimidos caben).
      - temperature: baja para reproducibilidad.
    """

    def complete_json(
        self, *, system_prompt: str, user_prompt: str,
        temperature: float = 0.1, timeout_s: float = 300.0,
    ) -> str:
        return enviar_mensaje_chat(
            system_prompt=system_prompt,
            historial=[{"role": "user", "content": user_prompt}],
            timeout=timeout_s,
            options={
                "num_predict": 1200,   # tope de tokens de salida
                "num_ctx": 4096,       # contexto (coincide con el del modelo cargado)
                "temperature": temperature,
            },
        )


def load_kpi_catalog(db: Session) -> list[dict]:
    """
    Lee el catálogo de KPIs del host para la inferencia del SIS.

    Nota: la columna kpi.activo es boolean en la BD. Filtramos por 'verdadero' a
    nivel Python tras traer las filas, para no depender del tipo exacto (boolean/int)
    y evitar el error 'boolean = integer' de Postgres.
    """
    filas = db.query(KPI).all()
    return [
        {"nombre": k.nombrekpi, "descripcion": k.descripcion or ""}
        for k in filas
        if getattr(k, "activo", True)  # incluye True, 1, o ausencia del atributo
    ]


def _dc_from_instrument(instrumento: InstrumentoProcesado) -> DublinCoreMetadata:
    """Mapea los metadatos DC del host al contrato del SIS (1:1)."""
    dc = instrumento.metadatos_dc
    if dc is None:
        # Metadatos mínimos si aún no se registraron (no debería pasar tras paso 2).
        return DublinCoreMetadata(
            dc_title=instrumento.nombre, dc_creator="", dc_subject=[],
            dc_description="", dc_publisher=settings.APP_NAME, dc_date="",
            dc_type=instrumento.tipo_instrumento, dc_format="", dc_language="es",
            dc_coverage="", dc_rights="",
        )
    import json as _json
    try:
        subject = _json.loads(dc.dc_subject) if dc.dc_subject else []
    except (ValueError, TypeError):
        subject = []
    return DublinCoreMetadata(
        dc_title=dc.dc_title, dc_creator=dc.dc_creator, dc_subject=subject,
        dc_description=dc.dc_description, dc_publisher=dc.dc_publisher,
        dc_date=str(dc.dc_date), dc_type=dc.dc_type, dc_format=dc.dc_format,
        dc_language=dc.dc_language, dc_coverage=dc.dc_coverage, dc_rights=dc.dc_rights,
        dc_source=dc.dc_source, dc_relation=dc.dc_relation,
    )


def build_request(
    instrumento: InstrumentoProcesado,
    request_id: str,
    extracted_text: str | None = None,
) -> SurveyIngestionRequest:
    """
    Construye el SurveyIngestionRequest.

    - Encuesta: envía los bytes del CSV/XLSX (vía tabular).
    - Entrevista/prueba: envía extracted_text (vía documento).
    - Codebook opcional (encuestas): se parsea a un CodebookModel estructurado
      (read_codebook) y se adjunta en request.codebook para resolución
      determinística en S5 (sin RAG).
    """
    tipo = instrumento.tipo_instrumento
    file_name = Path(instrumento.ruta_archivo).name if instrumento.ruta_archivo else "archivo"
    mime = _mime_for(file_name)

    if tipo == "encuesta":
        ruta_abs = settings.PROJECT_ROOT / instrumento.ruta_archivo
        file_bytes_b64 = base64.b64encode(ruta_abs.read_bytes()).decode()
        survey = SurveyFile(file_name=file_name, file_bytes_b64=file_bytes_b64, mime_type=mime)
    else:
        survey = SurveyFile(file_name=file_name, mime_type=mime, extracted_text=extracted_text or "")

    # Codebook opcional (solo encuestas): resolución determinística estructurada.
    codebook_model = None
    has_codebook = bool(getattr(instrumento, "ruta_codebook", None))
    if tipo == "encuesta" and has_codebook:
        cb_abs = settings.PROJECT_ROOT / instrumento.ruta_codebook
        if cb_abs.is_file():
            try:
                from survey_intelligence.engine.readers.codebook_reader import read_codebook
                cb_bytes = cb_abs.read_bytes()
                codebook_model = read_codebook(cb_bytes, file_name=cb_abs.name)
            except Exception as e:
                import logging
                logging.warning(f"No se pudo parsear el codebook {cb_abs.name}: {e}")

    return SurveyIngestionRequest(
        request_id=request_id,
        survey=survey,
        metadata=_dc_from_instrument(instrumento),
        codebook=codebook_model,
        options=IngestionOptions(
            instrument_type=tipo,
            language_hint="es",
            # Modo v2 del canónico (reagrupación por preguntas): controlado por .env.
            # Default False = comportamiento actual. Solo aplica a encuestas.
            question_grouping=(tipo == "encuesta" and settings.SIS_QUESTION_GROUPING),
        ),
    )


def build_service(db: Session) -> SurveyIntelligenceService:
    """Construye el SIS con los adaptadores del host inyectados."""
    return SurveyIntelligenceService(
        llm=OllamaLLMAdapter(),
        kpi_catalog=load_kpi_catalog(db),
    )


def _mime_for(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    return {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")
