# app/routers/routers_visualizacion.py
"""
Router — VISUALIZACIÓN y DESCARGA de instrumentos (5 endpoints).

  GET    /kpis                              → Catálogo de KPIs disponibles
  GET    /instrumentos                      → Catálogo con filtros
  GET    /instrumentos/{id}                 → Detalle completo
  GET    /instrumentos/{id}/download        → Descargar artefacto (?type=original|json|sav)
  DELETE /instrumentos/{id}                 → Eliminar instrumento

Acceso:
  Lectura:    PÚBLICO - todos los usuarios pueden ver y descargar cualquier instrumento (RAG colaborativo)
  Eliminación: solo propietario (InstrumentoProp)
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse

from api.dependencies.dependencies_instrumentos import (
    DBSession,
    InstrumentoAcceso,
    InstrumentoProp,
    UsuarioActual,
)
from api.schemas.schemas_carga import TipoInstrumento
from api.schemas.schemas_visualizacion import (
    FiltrosInstrumento,
    InstrumentoDetalle,
    InstrumentoResumen,
    KpiCatalogo,
    TipoDescarga,
)
from api.services.services_visualizacion import InstrumentVisualizacionService

router = APIRouter(tags=["visualizacion-instrumentos"])


# ===========================================================================
# Catálogo de KPIs
# ===========================================================================

@router.get(
    "/kpis",
    response_model=list[KpiCatalogo],
    summary="Listar KPIs disponibles",
    description="Devuelve el catálogo completo de KPIs del sistema para filtros y búsquedas.",
)
def listar_kpis(
    db: DBSession,
) -> list[KpiCatalogo]:
    return InstrumentVisualizacionService.list_kpis(db)


# ===========================================================================
# Catálogo de instrumentos
# ===========================================================================

@router.get(
    "/instrumentos",
    response_model=list[InstrumentoResumen],
    summary="Listar instrumentos accesibles",
    description=(
        "Devuelve todos los instrumentos del sistema (acceso público para RAG colaborativo). "
        "Filtros: tipo, KPI (por nombre), búsqueda de texto, fechas. "
        "Soporta paginación con skip/limit. "
        "Todos los instrumentos son en español."
    ),
)
def listar_instrumentos(
    usuario_actual:   UsuarioActual,
    db:               DBSession,
    tipo_instrumento: TipoInstrumento | None = Query(
        default=None,
        description="Acepta 'encuesta', 'entrevista', 'prueba_estandarizada' o 'prueba estandarizada'"
    ),
    kpi_nombre:       str | None             = Query(
        default=None, 
        description=(
            "Filtrar por nombre de KPI (búsqueda parcial, case-insensitive). "
            "Ejemplos: 'deserción', 'reprobación', 'asistencia'. "
            "Para ver todos los KPIs disponibles, consulta GET /kpis"
        ),
        examples=["deserción", "reprobación", "asistencia"]
    ),
    busqueda:         str | None             = Query(
        default=None, 
        description="Búsqueda de texto libre en título y descripción"
    ),
    desde:            date | None            = Query(
        default=None, 
        description="Instrumentos creados desde (YYYY-MM-DD)"
    ),
    hasta:            date | None            = Query(
        default=None, 
        description="Instrumentos creados hasta (YYYY-MM-DD)"
    ),
    skip:             int                    = Query(
        default=0, 
        ge=0,
        description="Paginación: saltar N resultados (ej: 0 para página 1, 20 para página 2)"
    ),
    limit:            int                    = Query(
        default=20, 
        ge=1, 
        le=100,
        description="Cantidad máxima de instrumentos por página (máximo: 100)"
    ),
) -> list[InstrumentoResumen]:
    filtros = FiltrosInstrumento(
        tipo_instrumento=tipo_instrumento,
        kpi_nombre=kpi_nombre,
        busqueda=busqueda,
        desde=desde,
        hasta=hasta,
        skip=skip,
        limit=limit,
    )
    return InstrumentVisualizacionService.list(db, usuario_actual.usuario_id, filtros)


# ===========================================================================
# Detalle del instrumento
# ===========================================================================

@router.get(
    "/instrumentos/{instrumento_id}",
    response_model=InstrumentoDetalle,
    summary="Detalle completo del instrumento",
    description=(
        "Devuelve metadatos DC, metadatos enriquecidos (si existen) y KPIs asociados. "
        "Acceso público - cualquier usuario autenticado puede ver cualquier instrumento."
    ),
)
def obtener_instrumento(
    instrumento: InstrumentoAcceso,
    db:          DBSession,
) -> InstrumentoDetalle:
    return InstrumentVisualizacionService.get_detail(db, instrumento)


# ===========================================================================
# Descargar artefacto
# ===========================================================================

@router.get(
    "/instrumentos/{instrumento_id}/download",
    summary="Descargar artefacto del instrumento",
    description=(
        "`type=original` — archivo subido (disponible desde paso 1)\n"
        "`type=json`     — JSON enriquecido (disponible desde 'vectorizado')\n"
        "`type=sav`      — archivo SPSS (solo encuestas, desde 'vectorizado')"
    ),
)
def descargar_artefacto(
    instrumento: InstrumentoAcceso,
    tipo: TipoDescarga = Query(
        default="original",
        alias="type",
        description="original | json | sav",
    ),
) -> FileResponse:
    ruta, nombre_archivo = InstrumentVisualizacionService.download(instrumento, tipo)
    media_type = "application/json" if tipo == "json" else "application/octet-stream"
    return FileResponse(path=str(ruta), filename=nombre_archivo, media_type=media_type)


# ===========================================================================
# Eliminar instrumento
# ===========================================================================

@router.delete(
    "/instrumentos/{instrumento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Eliminar instrumento",
    description=(
        "Elimina el instrumento, archivos en disco y chunks en ChromaDB. Irreversible. "
        "Solo el propietario puede eliminar su instrumento."
    ),
)
def eliminar_instrumento(
    instrumento: InstrumentoProp,
    db:          DBSession,
):
    InstrumentVisualizacionService.delete(db, instrumento)
    return None
