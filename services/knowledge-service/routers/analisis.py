"""Router del análisis de respuestas de entrevista (prefijo `/conocimiento`, vía api-gateway).

- POST  /conocimiento/{id_crudo}/documento/analisis                     inicia el análisis (segundo plano)
- GET   /conocimiento/{id_crudo}/documento/analisis                     avance y análisis por intercambio
- PATCH /conocimiento/{id_crudo}/documento/analisis/{participante}/{n}  corrección del investigador
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker

from dependencies import DBSession, Investigador
from services import analisis

router = APIRouter(prefix="/conocimiento", tags=["análisis de entrevistas"])


class Unidad(BaseModel):
    texto: str
    marco_temporal: str
    funcion: str
    postura: str


class Correccion(BaseModel):
    unidades: list[Unidad] | None = None
    postura: str | None = None
    motivo: str | None = Field(default=None, max_length=300)


@router.post("/{id_crudo}/documento/analisis", status_code=status.HTTP_202_ACCEPTED,
             summary="Analiza las respuestas de la entrevista (unidades, postura y motivo)")
def iniciar(id_crudo: int, db: DBSession, usuario: Investigador, tareas: BackgroundTasks) -> dict[str, Any]:
    avance = analisis.iniciar(db, usuario, id_crudo)
    if avance.pop("nuevo"):
        tareas.add_task(analisis.correr, sessionmaker(bind=db.get_bind(), future=True), id_crudo)
    return avance


@router.get("/{id_crudo}/documento/analisis", summary="Avance y análisis de cada respuesta")
def leer(id_crudo: int, db: DBSession, usuario: Investigador) -> dict[str, Any]:
    return analisis.leer(db, usuario, id_crudo)


@router.patch("/{id_crudo}/documento/analisis/{participante}/{n}", summary="Corrige el análisis de una respuesta")
def corregir(id_crudo: int, participante: str, n: int, cuerpo: Correccion, db: DBSession, usuario: Investigador) -> dict[str, Any]:
    cambios = cuerpo.model_dump(exclude_none=True)
    if "unidades" in cambios:
        cambios["unidades"] = [u.model_dump() for u in cuerpo.unidades or []]
    return analisis.corregir(db, usuario, id_crudo, participante, n, cambios)
