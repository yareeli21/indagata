"""Router — catálogo de instrumentos (filtrar y explorar el acervo).

  GET  /visualizacion/catalogo              instrumentos con filtros + facetas
  GET  /visualizacion/catalogo/{id}         ficha completa (metadatos, preguntas, estadísticas)
  GET  /visualizacion/investigadores        autores (para mostrar nombres)
  POST /visualizacion/relacionados          instrumentos de otros autores relacionados
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import DBSession, Investigador
from shared.models.metadatos_dc import MetadatosDC
from models import (
    CatalogoResponse,
    InstrumentoCatalogo,
    InstrumentoDetalle,
    InvestigadorOut,
    PreguntaOut,
    RelacionadoOut,
    RelacionadosRequest,
)
from services import query_engine
from services.query_engine import Filtros

router = APIRouter(prefix="/visualizacion", tags=["catalogo"])


@router.get("/catalogo", response_model=CatalogoResponse, summary="Catálogo con filtros y facetas")
def catalogo(
    usuario: Investigador,
    db: DBSession,
    q: str = Query("", max_length=200, description="Texto en título, descripción, etiquetas o KPIs."),
    tipo: str | None = None,
    nivel: str | None = None,
    kpi: str | None = Query(None, description="Id del KPI o su nombre."),
    autor: str | None = Query(None, description="Id del autor."),
    anio: int | None = None,
    estado: str | None = None,
    propios: bool = False,
    aprobados: bool = False,
    limite: int = Query(100, ge=1, le=500),
    desplazamiento: int = Query(0, ge=0),
) -> CatalogoResponse:
    fichas = query_engine.cargar_fichas(db)
    filtros = Filtros(
        q=q, tipo=tipo, nivel=nivel, kpi=kpi, autor=autor, anio=anio, estado=estado,
        solo_propios=propios, solo_aprobados=aprobados,
    )
    kpi_ref = query_engine.resolver_kpi(db, kpi, fichas) if kpi else None
    resultado = query_engine.filtrar(fichas, filtros, usuario.usuario_id, kpi_ref)
    return CatalogoResponse(
        total=len(resultado),
        items=[InstrumentoCatalogo(**f.dto()) for f in resultado[desplazamiento : desplazamiento + limite]],
        facetas=query_engine.facetas(resultado),
    )


@router.get("/catalogo/{id_crudo}", response_model=InstrumentoDetalle, summary="Ficha completa de un instrumento")
def detalle(id_crudo: int, _: Investigador, db: DBSession) -> InstrumentoDetalle:
    ficha = next((f for f in query_engine.cargar_fichas(db) if f.id_crudo == id_crudo), None)
    if ficha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrumento no encontrado.")
    metadata = (ficha.data or {}).get("metadata") or {}
    dc_fila = db.get(MetadatosDC, id_crudo)
    if dc_fila is not None:
        dublin_core = {c.name: getattr(dc_fila, c.name) for c in MetadatosDC.__table__.columns if c.name != "id_crudo"}
    else:
        dublin_core = {k.replace(":", "_"): v for k, v in (metadata.get("dublin_core") or {}).items()}
    modelo = query_engine.TABLAS_TIPO.get(ficha.tipo_backend)
    esp_fila = db.get(modelo, id_crudo) if modelo else None
    if esp_fila is not None:
        enriquecidos = {c.name: getattr(esp_fila, c.name) for c in modelo.__table__.columns if c.name != "id_crudo"}
    else:
        enriquecidos = dict(metadata.get("survey_specific") or {})
    return InstrumentoDetalle(
        instrumento=InstrumentoCatalogo(**ficha.dto()),
        dublin_core=dublin_core,
        enriquecidos=enriquecidos,
        preguntas=[PreguntaOut(**p) for p in query_engine.preguntas_de(ficha.data)],
        estadisticas=((ficha.data or {}).get("statistics") or {}).get("per_question") or {},
    )


@router.get("/investigadores", response_model=list[InvestigadorOut], summary="Autores del acervo")
def investigadores(_: Investigador, db: DBSession) -> list[InvestigadorOut]:
    fichas = query_engine.cargar_fichas(db)
    return [InvestigadorOut(**i) for i in query_engine.investigadores(db, fichas)]


@router.post(
    "/relacionados",
    response_model=list[RelacionadoOut],
    summary="Instrumentos de otros autores relacionados con una selección",
    description=(
        "Compara la selección con los instrumentos de otros autores por KPIs en común, "
        "nivel educativo y similitud semántica de su ficha (vectores en ChromaDB; si no "
        "están ingeridos, similitud léxica de título y descripción)."
    ),
)
def relacionados(peticion: RelacionadosRequest, usuario: Investigador, db: DBSession) -> list[RelacionadoOut]:
    fichas = query_engine.cargar_fichas(db)
    autor = peticion.autorId or str(usuario.usuario_id)
    return [RelacionadoOut(**r) for r in query_engine.relacionados(fichas, peticion.ids, autor)]
