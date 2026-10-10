"""Router — KPIs: catálogo, resumen del acervo y relación instrumento ↔ KPI.

  GET  /visualizacion/kpis/catalogo                 KPIs del catálogo (tabla `kpi`)
  GET  /visualizacion/kpis/resumen                  métricas del acervo
  POST /visualizacion/kpis/{kpi_id}/datos           dashboard de un KPI + evidencia
  GET  /visualizacion/instrumentos/{id}/kpis        KPIs de un instrumento y las preguntas que los miden
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from dependencies import DBSession, Investigador
from models import DatosGraficaOut, DatosGraficaRequest, KpiCatalogoOut, KpiDeInstrumentoOut, KpiResumenOut
from services import query_engine

router = APIRouter(prefix="/visualizacion", tags=["kpis"])


@router.get("/kpis/catalogo", response_model=list[KpiCatalogoOut], summary="Catálogo de KPIs")
def catalogo(_: Investigador, db: DBSession) -> list[KpiCatalogoOut]:
    fichas = query_engine.cargar_fichas(db)
    return [KpiCatalogoOut(**k) for k in query_engine.catalogo_kpis(db, fichas)]


@router.get("/kpis/resumen", response_model=list[KpiResumenOut], summary="Métricas del acervo")
def resumen(_: Investigador, db: DBSession) -> list[KpiResumenOut]:
    fichas = query_engine.cargar_fichas(db)
    return [KpiResumenOut(**m) for m in query_engine.resumen(db, fichas)]


@router.post(
    "/kpis/{kpi_id}/datos",
    response_model=DatosGraficaOut,
    summary="Dashboard de un KPI sobre un conjunto de instrumentos",
    description=(
        "Agrega los instrumentos asociados al KPI (aceptados en el analysis-service o "
        "declarados en su diseño) por nivel, año y tipo, y para cada uno devuelve las "
        "preguntas que mejor miden el KPI (similitud entre el vector del KPI y los "
        "vectores de sus preguntas). Sin `instrumentoIds` se usa todo el acervo."
    ),
)
def datos(kpi_id: str, peticion: DatosGraficaRequest, _: Investigador, db: DBSession) -> DatosGraficaOut:
    fichas = query_engine.cargar_fichas(db)
    resultado = query_engine.datos_grafica(db, fichas, kpi_id, peticion.instrumentoIds)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "KPI no encontrado.")
    return DatosGraficaOut(**resultado)


@router.get(
    "/instrumentos/{id_crudo}/kpis",
    response_model=list[KpiDeInstrumentoOut],
    summary="KPIs de un instrumento y las preguntas que los miden",
)
def kpis_de_instrumento(id_crudo: int, _: Investigador, db: DBSession) -> list[KpiDeInstrumentoOut]:
    ficha = next((f for f in query_engine.cargar_fichas(db) if f.id_crudo == id_crudo), None)
    if ficha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrumento no encontrado.")
    return [KpiDeInstrumentoOut(**k) for k in query_engine.kpis_de_instrumento(db, ficha)]
