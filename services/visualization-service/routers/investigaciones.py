"""Router — investigaciones del usuario y su conversación (25 nov 2026).

  GET    /visualizacion/investigaciones        las del usuario del token, con instrumentos y conversación
  PUT    /visualizacion/investigaciones/{id}   crea o actualiza (solo los campos enviados)
  DELETE /visualizacion/investigaciones/{id}   elimina (no toca instrumentos ni el registro de consultas)

Antes vivían solo en el navegador; cada usuario ve únicamente las suyas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from dependencies import DBSession, Investigador
from shared.models.investigacion import Investigacion

router = APIRouter(prefix="/visualizacion", tags=["investigaciones"])

_MAX_MENSAJES = 200


class InvestigacionIn(BaseModel):
    nombre: str | None = Field(default=None, max_length=255)
    fechaCreacion: datetime | None = None
    instrumentos: list[str] | None = None
    sesion: dict[str, Any] | None = None


class InvestigacionOut(BaseModel):
    id: str
    nombre: str
    fechaCreacion: datetime | None
    instrumentos: list[str]
    sesion: dict[str, Any] | None
    actualizada: datetime | None


def _out(i: Investigacion) -> InvestigacionOut:
    return InvestigacionOut(id=i.id, nombre=i.nombre, fechaCreacion=i.fecha_creacion,
                            instrumentos=[str(x) for x in i.instrumentos or []], sesion=i.sesion,
                            actualizada=i.actualizada)


@router.get("/investigaciones", response_model=list[InvestigacionOut], summary="Mis investigaciones")
def listar(usuario: Investigador, db: DBSession) -> list[InvestigacionOut]:
    filas = (db.query(Investigacion).filter(Investigacion.usuario_id == usuario.usuario_id)
             .order_by(Investigacion.fecha_creacion).all())
    return [_out(i) for i in filas]


@router.put("/investigaciones/{investigacion_id}", response_model=InvestigacionOut,
            summary="Crear o actualizar una investigación")
def guardar(investigacion_id: str, datos: InvestigacionIn, usuario: Investigador, db: DBSession) -> InvestigacionOut:
    fila = db.get(Investigacion, {"usuario_id": usuario.usuario_id, "id": investigacion_id[:64]})
    if fila is None:
        fila = Investigacion(usuario_id=usuario.usuario_id, id=investigacion_id[:64],
                             nombre=(datos.nombre or "Investigación").strip()[:255] or "Investigación",
                             instrumentos=[], fecha_creacion=datos.fechaCreacion or datetime.now())
        db.add(fila)
    if datos.nombre is not None and datos.nombre.strip():
        fila.nombre = datos.nombre.strip()[:255]
    if datos.instrumentos is not None:
        fila.instrumentos = [str(x) for x in datos.instrumentos]
    if datos.sesion is not None:
        sesion = dict(datos.sesion)
        if isinstance(sesion.get("mensajes"), list):
            sesion["mensajes"] = sesion["mensajes"][-_MAX_MENSAJES:]
        fila.sesion = sesion
    fila.actualizada = datetime.now()
    db.commit()
    db.refresh(fila)
    return _out(fila)


@router.delete("/investigaciones/{investigacion_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar una investigación")
def eliminar(investigacion_id: str, usuario: Investigador, db: DBSession) -> Response:
    fila = db.get(Investigacion, {"usuario_id": usuario.usuario_id, "id": investigacion_id})
    if fila is not None:
        db.delete(fila)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
