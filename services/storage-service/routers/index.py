"""Router — índice vectorial (ChromaDB).

Prefijo /almacenamiento/indice. El storage-service es el único escritor de la
colección `instrumentos`; los demás servicios (metadata-service al aprobar,
visualization-service al armar una investigación) le piden la ingesta.

  POST   /almacenamiento/indice/instrumentos/{id_crudo}   ingerir / reingerir
  DELETE /almacenamiento/indice/instrumentos/{id_crudo}   quitar sus vectores
  GET    /almacenamiento/indice/instrumentos/{id_crudo}   estado de la ingesta
  GET    /almacenamiento/indice/colecciones               colecciones y conteos
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from dependencies import Autenticado, DBSession, Interno
from models import ColeccionInfo, DesindexarResponse, EstadoIndice, IndexarRequest, IndexarResponse
from services import chroma_indexer

router = APIRouter(prefix="/almacenamiento/indice", tags=["indice-vectorial"])


def _http(exc: chroma_indexer.IndiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post(
    "/instrumentos/{id_crudo}",
    response_model=IndexarResponse,
    summary="Ingerir un instrumento aprobado en la colección `instrumentos`",
)
def indexar(id_crudo: int, _: Interno, db: DBSession, peticion: IndexarRequest | None = None) -> IndexarResponse:
    reindexar = True if peticion is None else peticion.reindexar
    try:
        return IndexarResponse(**chroma_indexer.indexar_instrumento(db, id_crudo, reindexar=reindexar))
    except chroma_indexer.IndiceError as exc:
        db.rollback()
        raise _http(exc)


@router.delete(
    "/instrumentos/{id_crudo}",
    response_model=DesindexarResponse,
    summary="Quitar los vectores de un instrumento",
)
def desindexar(id_crudo: int, _: Interno, db: DBSession) -> DesindexarResponse:
    try:
        eliminados = chroma_indexer.desindexar_instrumento(db, id_crudo)
    except chroma_indexer.IndiceError as exc:
        db.rollback()
        raise _http(exc)
    return DesindexarResponse(instrumentoId=str(id_crudo), vectores_eliminados=eliminados)


@router.get(
    "/instrumentos/{id_crudo}",
    response_model=EstadoIndice,
    summary="Estado de la ingesta de un instrumento",
)
def estado(id_crudo: int, _: Autenticado, db: DBSession) -> EstadoIndice:
    try:
        return EstadoIndice(**chroma_indexer.estado_indice(db, id_crudo))
    except chroma_indexer.IndiceError as exc:
        raise _http(exc)


@router.get("/colecciones", response_model=list[ColeccionInfo], summary="Colecciones de ChromaDB")
def colecciones(_: Autenticado, db: DBSession) -> list[ColeccionInfo]:
    try:
        return [ColeccionInfo(**c) for c in chroma_indexer.listar_colecciones(db)]
    except chroma_indexer.IndiceError as exc:
        raise _http(exc)
