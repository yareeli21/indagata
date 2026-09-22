# app/routers/routers_carga.py
"""
Router — CARGA de instrumentos (6 endpoints).

Wizard de 5 pasos:
  POST /instrumentos/upload               → Paso 1: subir archivo
  POST /instrumentos/metadata             → Paso 2: registrar metadatos DC + KPIs base
  GET  /instrumentos/{id}/etl/extract     → Paso 3: análisis ETL por el LLM  ⚠️ requiere Ollama
  GET  /instrumentos/{id}/etl/proposals   → Ver propuestas generadas
  POST /instrumentos/{id}/etl/approve     → Paso 4: enviar decisiones
  POST /instrumentos/ingesta              → Paso 5: pipeline final

Acceso: solo el propietario (InstrumentoProp / UsuarioActual).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, UploadFile, status

from api.dependencies.dependencies_instrumentos import (
    DBSession,
    InstrumentoProp,
    UsuarioActual,
)
from api.schemas.schemas_carga import (
    AnalyzeResponse,
    AprobacionRequest,
    CleaningApprovalResponse,
    EnrichmentApprovalResponse,
    EtlProposalsResponse,
    MetadataInitialData,
    MetadataRequest,
    MetadataResponse,
    UploadResponse,
)
from api.services.services_carga import EtlService, InstrumentCargaService

router = APIRouter(tags=["carga-instrumentos"])


# ===========================================================================
# PASO 1 — Subir archivo
# ===========================================================================

@router.post(
    "/instrumentos/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Paso 1/5 — Subir archivo del instrumento",
    description=(
        "Recibe el archivo del instrumento y registra su tipo. Formatos por tipo: "
        "encuesta (.csv, .xlsx, .xls); entrevista y prueba estandarizada (.pdf, .txt, .docx). "
        "Devuelve `instrumento_id` para los pasos siguientes."
    ),
)
async def upload_instrumento(
    usuario_actual:   UsuarioActual,
    db:               DBSession,
    archivo:          UploadFile,
    tipo_instrumento: str = Form(..., description="encuesta | entrevista | prueba_estandarizada"),
    codebook:         UploadFile | None = None,
) -> UploadResponse:
    """
    Sube el instrumento. Para ENCUESTAS se puede adjuntar opcionalmente un `codebook`
    (.csv o .pdf) que el SIS resuelve de forma determinística (etapa S5, sin RAG).
    Para los demás tipos se ignora.
    """
    from api.schemas.schemas_carga import UploadRequest
    datos = UploadRequest(
        tipo_instrumento=tipo_instrumento,  # type: ignore
    )
    return await InstrumentCargaService.upload(
        db, usuario_actual.usuario_id, datos, archivo, codebook=codebook
    )


# ===========================================================================
# PASO 2 — Registrar metadatos Dublin Core
# ===========================================================================

@router.get(
    "/instrumentos/{instrumento_id}/metadata/init",
    response_model=MetadataInitialData,
    summary="Obtener datos iniciales para Paso 2",
    description=(
        "Devuelve datos pre-poblados (autocompletados) para inicializar "
        "el formulario de metadatos Dublin Core. El frontend los muestra "
        "en campos de solo lectura + dc_title editable."
    ),
)
def obtener_metadata_inicial(
    instrumento: InstrumentoProp,
    usuario_actual: UsuarioActual,
    db: DBSession,
) -> MetadataInitialData:
    return InstrumentCargaService.get_metadata_initial_data(
        db, usuario_actual.usuario_id, instrumento.instrumento_id
    )


@router.post(
    "/instrumentos/{instrumento_id}/metadata",
    response_model=MetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Paso 2/5 — Registrar metadatos Dublin Core",
    description=(
        "Registra los 13 campos Dublin Core. 6 campos se autocompletan "
        "(dc_creator, dc_publisher, dc_type, dc_format, dc_date, dc_language). "
        "El usuario captura 7 campos manualmente. Inmutable: un segundo intento devuelve 409."
    ),
)
def registrar_metadata(
    instrumento: InstrumentoProp,
    usuario_actual: UsuarioActual,
    db: DBSession,
    request: MetadataRequest,
) -> MetadataResponse:
    return InstrumentCargaService.create_metadata(
        db, usuario_actual.usuario_id, instrumento.instrumento_id, request
    )


# ===========================================================================
# PASO 3 — Análisis por el Survey Intelligence Service (SIS)
# ===========================================================================

@router.post(
    "/instrumentos/{instrumento_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Paso 3 — Analizar el instrumento con el SIS requiere Ollama",
    description=(
        "Ejecuta el Survey Intelligence Service completo (limpieza, profiling, "
        "enriquecimiento semántico, inferencia de KPIs y oportunidades de mejora) en "
        "una sola llamada. Persiste las propuestas. Requiere estado 'metadata_registrado'. "
        "Pasa a 'etl_pendiente_limpieza'."
    ),
)
def analizar_instrumento(
    instrumento: InstrumentoProp,
    db:          DBSession,
) -> AnalyzeResponse:
    return EtlService.analyze(db, instrumento)


# ===========================================================================
# Ver propuestas (idempotente)
# ===========================================================================

@router.get(
    "/instrumentos/{instrumento_id}/etl/proposals",
    response_model=EtlProposalsResponse,
    summary="Ver propuestas generadas por el SIS",
    description="Devuelve todas las propuestas con su estado. Puede llamarse múltiples veces.",
)
def obtener_propuestas(
    instrumento: InstrumentoProp,
    db:          DBSession,
) -> EtlProposalsResponse:
    return EtlService.get_proposals(db, instrumento)


# ===========================================================================
# PASO 4a — Aprobar LIMPIEZA (camino 1: transformaciones)
# ===========================================================================

@router.post(
    "/instrumentos/{instrumento_id}/approve/cleaning",
    response_model=CleaningApprovalResponse,
    summary="Paso 4a — Aprobar/rechazar propuestas de limpieza",
    description=(
        "Decide sobre las propuestas de transformación (eliminar columnas, normalizar "
        "escalas). Envía una decisión por cada propuesta de limpieza pendiente. "
        "Requiere 'etl_pendiente_limpieza'. Pasa a 'etl_pendiente_enriquecimiento'."
    ),
)
def aprobar_limpieza(
    instrumento: InstrumentoProp,
    db:          DBSession,
    request:     AprobacionRequest,
) -> CleaningApprovalResponse:
    return EtlService.approve_cleaning(db, instrumento, request)


# ===========================================================================
# PASO 4b — Aprobar ENRIQUECIMIENTO (camino 2: metadatos + KPIs)
# ===========================================================================

@router.post(
    "/instrumentos/{instrumento_id}/approve/enrichment",
    response_model=EnrichmentApprovalResponse,
    summary="Paso 4b — Aprobar/rechazar metadatos y KPIs",
    description=(
        "Decide sobre los metadatos enriquecidos y los KPIs inferidos. Genera el JSON "
        "consolidado (y el .SAV si es encuesta). Requiere 'etl_pendiente_enriquecimiento'. "
        "Pasa a 'etl_aprobado'."
    ),
)
def aprobar_enriquecimiento(
    instrumento: InstrumentoProp,
    db:          DBSession,
    request:     AprobacionRequest,
) -> EnrichmentApprovalResponse:
    return EtlService.approve_enrichment(db, instrumento, request)


# ===========================================================================
# PASO 5 — Pipeline de ingesta
# ===========================================================================

# ===========================================================================
# PASO 5 — Pipeline de ingesta (DESHABILITADO - Implementación futura)
# ===========================================================================
# NOTA: Este endpoint está deshabilitado porque el JSON consolidado se genera
# automáticamente en el Paso 4 (approve). El estado final del módulo de carga
# es 'etl_aprobado' y el JSON ya está disponible para descarga.
#
# Cuando se implemente el módulo de vectorización (futuro), se creará un nuevo
# endpoint POST /instrumentos/{id}/vectorize que procesará instrumentos en
# estado 'etl_aprobado' y los convertirá a 'vectorizado'.

# @router.post(
#     "/instrumentos/ingesta",
#     response_model=IngestaResponse,
#     status_code=status.HTTP_202_ACCEPTED,
#     summary="[DESHABILITADO] Paso 5/5 — Ejecutar pipeline de ingesta final",
#     description="Requiere estado 'etl_aprobado'. Inicia el pipeline de vectorización.",
# )
# def ejecutar_ingesta(
#     usuario_actual: UsuarioActual,
#     db:             DBSession,
#     request:        IngestaRequest,
# ) -> IngestaResponse:
#     return InstrumentCargaService.ingest(db, usuario_actual.usuario_id, request.instrumento_id)

