"""Router — LISTADO / CONSULTA / CATÁLOGO de instrumentos (diseño §6).

  GET /instrumentos                 -> list[InstrumentoDTO]
  GET /instrumentos/kpis/catalogo   -> list[str]  (unión ordenada de KPIs)
  GET /instrumentos/{id}            -> InstrumentoDTO | 404   ({id} = id_crudo)

Los tres exigen `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)`, igual que
`upload`/`delete`. El id canónico que viaja al frontend es `str(id_crudo)`
(§2.1). El JSON de dominio se resuelve por fila con `instrumento_query` y se
mapea con `map_instrumento` (lectura defensiva, nunca aborta).

El borrado (`DELETE /instrumentos/{id_crudo}`) vive en `delete.py`: NO se
re-declara aquí.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import DBSession, require_rol
from app.schemas.instrumentos import InstrumentoDTO
from app.services.instrumento_query import resolver_json_por_id_crudo
from app.services.map_instrumento import extraer_kpis, mapear_instrumento
from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

router = APIRouter(prefix="/instrumentos", tags=["consulta-instrumentos"])

# Consultar el catálogo requiere, como mínimo, rol investigador.
UsuarioQuePuedeConsultar = Annotated[
    Usuario, Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))
]


def _filas_instrumentos(db: DBSession) -> list[tuple[RawData, InstrumentoProcesado | None]]:
    """RawData LEFT JOIN InstrumentoProcesado por id_crudo (una fila/instrumento)."""
    filas = (
        db.query(RawData, InstrumentoProcesado)
        .outerjoin(
            InstrumentoProcesado,
            InstrumentoProcesado.id_crudo == RawData.id_crudo,
        )
        .order_by(RawData.id_crudo)
        .all()
    )
    return [(raw, procesado) for raw, procesado in filas]


@router.get(
    "",
    response_model=list[InstrumentoDTO],
    summary="Listar todos los instrumentos",
)
def listar_instrumentos(
    usuario_actual: UsuarioQuePuedeConsultar,
    db: DBSession,
) -> list[InstrumentoDTO]:
    resultado: list[InstrumentoDTO] = []
    for raw, procesado in _filas_instrumentos(db):
        instrumento_json = resolver_json_por_id_crudo(raw.id_crudo, procesado)
        resultado.append(mapear_instrumento(raw, procesado, instrumento_json))
    return resultado


# NOTA: declarar /kpis/catalogo ANTES de /{id} y tipar {id:int} evita que
# "kpis" sea capturado como un {id} (defensa doble, §6/plan paso 8).
@router.get(
    "/kpis/catalogo",
    response_model=list[str],
    summary="Catálogo de KPIs (unión de kpi_hints de todos los instrumentos)",
)
def catalogo_kpis(
    usuario_actual: UsuarioQuePuedeConsultar,
    db: DBSession,
) -> list[str]:
    catalogo: set[str] = set()
    for raw, procesado in _filas_instrumentos(db):
        instrumento_json = resolver_json_por_id_crudo(raw.id_crudo, procesado)
        catalogo.update(extraer_kpis(instrumento_json))
    return sorted(catalogo)


@router.get(
    "/{id}",
    response_model=InstrumentoDTO,
    summary="Obtener un instrumento por id (id_crudo)",
)
def obtener_instrumento(
    usuario_actual: UsuarioQuePuedeConsultar,
    db: DBSession,
    id: int,
) -> InstrumentoDTO:
    raw = db.get(RawData, id)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrumento no encontrado.",
        )
    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    instrumento_json = resolver_json_por_id_crudo(id, procesado)
    return mapear_instrumento(raw, procesado, instrumento_json)
