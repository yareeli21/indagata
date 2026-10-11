"""Router — CATÁLOGO de KPIs (read-only).

Expone el catálogo real de KPIs de la tabla `tt_rag.kpi` para la pantalla de KPIs
del frontend:

  GET /vectorizacion/kpis/catalogo  → lista de KPIs ordenada por kpi_id, cada uno
                                      con los campos string que el frontend necesita
                                      (el ícono se calcula en el frontend, no aquí).

El frontend lo llama directo vía ANALYSIS_URL (el gateway no proxea /vectorizacion/*),
igual que `getEspacioVectorial`. No colisiona con POST /vectorizacion/kpis/reindex
(método y ruta distintos).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, status
from sqlalchemy.exc import SQLAlchemyError

from app.vectorization.dependencies import DBSession, UsuarioActual
from app.vectorization.schemas.vectorizacion import KpiCatalogoDTO
from shared.models.kpi import KPI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vectorizacion", tags=["vectorizacion-kpis-catalogo"])


@router.get(
    "/kpis/catalogo",
    response_model=list[KpiCatalogoDTO],
    status_code=status.HTTP_200_OK,
    summary="Catálogo real de KPIs (read-only)",
    description=(
        "Devuelve TODOS los KPIs de la tabla `tt_rag.kpi` ordenados por `kpi_id`, "
        "cada uno con sus campos string (nombre, significado y metadatos). El ícono "
        "no se calcula aquí: lo resuelve el frontend. BD vacía → []."
    ),
)
def catalogo_kpis(
    usuario_actual: UsuarioActual,
    db: DBSession,
) -> list[KpiCatalogoDTO]:
    try:
        kpis = db.query(KPI).order_by(KPI.kpi_id).all()
    except SQLAlchemyError:
        logger.exception("Error al leer el catálogo de KPIs de tt_rag.kpi.")
        raise

    return [
        KpiCatalogoDTO(
            id=str(k.kpi_id),
            nombre=k.nombre,
            descripcion_ampliada_educativa=k.descripcion_ampliada_educativa or "",
            polaridad_rendimiento=k.polaridad_rendimiento or "",
            tipo_objetivo_estrategico=k.tipo_objetivo_estrategico or "",
            formula_metrica_calculo=k.formula_metrica_calculo or "",
            comportamiento_direccional_causalidad=k.comportamiento_direccional_causalidad or "",
            razon_estrategica_decisiones=k.razon_estrategica_decisiones or "",
        )
        for k in kpis
    ]
