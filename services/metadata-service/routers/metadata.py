"""Router — metadatos Dublin Core y aprobación por el autor.

Prefijo /api/metadata (el api-gateway lo reenvía tal cual). `{id_crudo}` es el
id canónico del instrumento (PK de raw_data), el mismo que usa el frontend.

  GET    /api/metadata                         listado paginado
  GET    /api/metadata/{id}/propuesta          Dublin Core propuesto (o aprobado)
  POST   /api/metadata/{id}/vista-previa       JSON estandarizado sin guardar + errores
  POST   /api/metadata/{id}/aprobar            el autor aprueba → persistir + ingesta RAG
  POST   /api/metadata/{id}/finalizar          añadir los KPIs aceptados al JSON
  GET    /api/metadata/{id}                    metadatos aprobados
  DELETE /api/metadata/{id}                    retirar la aprobación (sale del RAG)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import DBSession, Investigador
from models import (
    AprobacionResponse,
    FinalizacionResponse,
    ListadoMetadatos,
    MetadatosPayload,
    MetadatosResponse,
    PropuestaResponse,
    ResumenMetadatos,
    RetiroResponse,
    VistaPreviaResponse,
)
from services import aprobacion
from services.dc_manager import DCManager
from services.enrichment_engine import EnrichmentEngine

router = APIRouter(prefix="/api/metadata", tags=["metadatos-dublin-core"])


@router.get("", response_model=ListadoMetadatos, summary="Listar metadatos Dublin Core")
def listar(
    _: Investigador,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ListadoMetadatos:
    total, filas = DCManager.listar(db, skip, limit)
    return ListadoMetadatos(
        total=total,
        skip=skip,
        limit=limit,
        metadatos=[
            ResumenMetadatos(
                id_crudo=f.id_crudo, dc_title=f.dc_title, dc_creator=f.dc_creator, dc_type=f.dc_type, dc_date=f.dc_date
            )
            for f in filas
        ],
    )


@router.get(
    "/{id_crudo}/propuesta",
    response_model=PropuestaResponse,
    summary="Dublin Core propuesto para el instrumento",
    description=(
        "Propone los 13 campos Dublin Core: los automáticos (autor, fecha, formato, "
        "fuente, idioma) y los inferidos del contenido (título, tema, descripción, "
        "cobertura). Con `usar_llm` el modelo local completa los campos interpretativos. "
        "Si los metadatos ya fueron aprobados, devuelve los aprobados."
    ),
)
def propuesta(
    id_crudo: int, usuario: Investigador, db: DBSession, usar_llm: bool | None = None
) -> PropuestaResponse:
    return PropuestaResponse(**aprobacion.propuesta(db, usuario, id_crudo, "dublin_core", usar_llm))


@router.post(
    "/{id_crudo}/vista-previa",
    response_model=VistaPreviaResponse,
    summary="Vista previa del JSON estandarizado (no guarda nada)",
)
def vista_previa(
    id_crudo: int, payload: MetadatosPayload, usuario: Investigador, db: DBSession
) -> VistaPreviaResponse:
    return VistaPreviaResponse(**aprobacion.vista_previa(db, usuario, id_crudo, payload.model_dump()))


@router.post(
    "/{id_crudo}/aprobar",
    response_model=AprobacionResponse,
    summary="El autor aprueba los metadatos (requisito para el RAG)",
    description=(
        "Valida el Dublin Core y los metadatos del tipo, genera el JSON estandarizado, "
        "lo guarda en el storage-service, persiste `metadatos_dc` + "
        "`metadatos_enriquecidos_*`, marca el instrumento como aprobado y pide su "
        "ingesta al índice vectorial. Solo el autor (o un administrador)."
    ),
)
def aprobar(
    id_crudo: int, payload: MetadatosPayload, usuario: Investigador, db: DBSession
) -> AprobacionResponse:
    return AprobacionResponse(**aprobacion.aprobar(db, usuario, id_crudo, payload.model_dump()))


@router.post(
    "/{id_crudo}/finalizar",
    response_model=FinalizacionResponse,
    summary="Guardar el instrumento con los KPIs aceptados",
)
def finalizar(id_crudo: int, usuario: Investigador, db: DBSession) -> FinalizacionResponse:
    return FinalizacionResponse(**aprobacion.finalizar(db, usuario, id_crudo))


@router.get("/{id_crudo}", response_model=MetadatosResponse, summary="Metadatos registrados del instrumento")
def obtener(id_crudo: int, usuario: Investigador, db: DBSession) -> MetadatosResponse:
    ctx = aprobacion.cargar_contexto(db, usuario, id_crudo, exigir_dueno=False)
    dc = DCManager.obtener(db, id_crudo)
    if dc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El instrumento no tiene metadatos registrados.")
    return MetadatosResponse(
        id_crudo=id_crudo,
        tipo_instrumento=ctx.tipo,
        estado=ctx.procesado.estado,
        aprobado=ctx.aprobado,
        fecha_aprobado=ctx.procesado.fecha_aprobado,
        dublin_core=dc,
        enriquecidos=EnrichmentEngine.obtener(db, ctx.tipo, id_crudo),
    )


@router.delete("/{id_crudo}", response_model=RetiroResponse, summary="Retirar los metadatos aprobados")
def retirar(id_crudo: int, usuario: Investigador, db: DBSession) -> RetiroResponse:
    return RetiroResponse(**aprobacion.retirar(db, usuario, id_crudo))
