"""Router — limpieza de instrumentos (expuesto en el api-gateway bajo /limpieza).

  POST  /limpieza/{id}/ejecuciones                       fase automática → versión nueva (o retoma)
  GET   /limpieza/{id}/ejecuciones/actual                última versión (retomar / vista final)
  GET   /limpieza/{id}/ejecuciones/{version}             fase asistida de una versión
  PATCH /limpieza/{id}/ejecuciones/{version}/decisiones  guardado parcial de decisiones
  POST  /limpieza/{id}/ejecuciones/{version}/confirmar   aplica, guarda el CSV limpio y cierra
  GET   /limpieza/{id}/ejecuciones/{version}/vista-final cifras clave + muestra del resultado

`{id}` es el id_crudo del instrumento. Solo el autor (o un admin) puede limpiarlo.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import DBSession, Investigador
from models import DecisionesIn, EjecucionOut, VistaFinalOut
from services import ejecuciones

router = APIRouter(prefix="/limpieza", tags=["limpieza"])


def _dto(db, usuario, ejecucion) -> EjecucionOut:  # noqa: ANN001
    ctx = ejecuciones.cargar_contexto(db, usuario, ejecucion.id_crudo)
    return EjecucionOut(**ejecuciones.a_dto(ejecucion, ctx.raw.tipo_instrumento))


@router.post(
    "/{id_crudo}/ejecuciones",
    response_model=EjecucionOut,
    summary="Ejecutar la fase automática",
    description=(
        "Lee el archivo crudo (sin modificarlo), aplica la fase automática según el tipo "
        "de instrumento y crea una versión nueva en `esperando_decisiones`. Si ya hay una "
        "versión esperando decisiones la devuelve para retomarla, salvo con `nueva=true`. "
        "Si la limpieza falla, la versión queda `fallida` con un mensaje claro."
    ),
)
def ejecutar(id_crudo: int, usuario: Investigador, db: DBSession, nueva: bool = Query(False)) -> EjecucionOut:
    ejecucion = ejecuciones.crear(db, usuario, id_crudo, nueva=nueva)
    return _dto(db, usuario, ejecucion)


@router.get("/{id_crudo}/ejecuciones/actual", response_model=EjecucionOut, summary="Última versión de la limpieza")
def actual(id_crudo: int, usuario: Investigador, db: DBSession) -> EjecucionOut:
    ejecuciones.cargar_contexto(db, usuario, id_crudo)
    ejecucion = ejecuciones.ultima(db, id_crudo)
    if ejecucion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este instrumento aún no se ha limpiado.")
    return _dto(db, usuario, ejecucion)


@router.get("/{id_crudo}/ejecuciones/{version}", response_model=EjecucionOut, summary="Fase asistida de una versión")
def detalle(id_crudo: int, version: int, usuario: Investigador, db: DBSession) -> EjecucionOut:
    ejecuciones.cargar_contexto(db, usuario, id_crudo)
    return _dto(db, usuario, ejecuciones.obtener(db, id_crudo, version))


@router.patch(
    "/{id_crudo}/ejecuciones/{version}/decisiones",
    response_model=EjecucionOut,
    summary="Guardar decisiones parciales",
)
def decidir(id_crudo: int, version: int, cuerpo: DecisionesIn, usuario: Investigador, db: DBSession) -> EjecucionOut:
    ejecuciones.cargar_contexto(db, usuario, id_crudo)
    ejecucion = ejecuciones.obtener(db, id_crudo, version)
    return _dto(db, usuario, ejecuciones.guardar_decisiones(db, usuario, ejecucion, cuerpo.decisiones))


@router.post(
    "/{id_crudo}/ejecuciones/{version}/confirmar",
    response_model=EjecucionOut,
    summary="Confirmar la limpieza",
    description=(
        "Aplica las decisiones (las no tomadas usan la opción sugerida), guarda el CSV "
        "limpio en storage-service y cierra el reporte_limpieza. 409 si faltan decisiones "
        "obligatorias."
    ),
)
def confirmar(id_crudo: int, version: int, usuario: Investigador, db: DBSession) -> EjecucionOut:
    ejecuciones.cargar_contexto(db, usuario, id_crudo)
    ejecucion = ejecuciones.obtener(db, id_crudo, version)
    return _dto(db, usuario, ejecuciones.confirmar(db, usuario, ejecucion))


@router.get(
    "/{id_crudo}/ejecuciones/{version}/vista-final",
    response_model=VistaFinalOut,
    summary="Vista final del instrumento limpio",
)
def vista_final(id_crudo: int, version: int, usuario: Investigador, db: DBSession) -> VistaFinalOut:
    ejecuciones.cargar_contexto(db, usuario, id_crudo)
    ejecucion = ejecuciones.obtener(db, id_crudo, version)
    vista = (ejecucion.reporte or {}).get("vista_final")
    if ejecucion.estado != "confirmada" or not vista:
        raise HTTPException(status.HTTP_409_CONFLICT, "La limpieza de esta versión aún no se confirma.")
    return VistaFinalOut(**vista)
