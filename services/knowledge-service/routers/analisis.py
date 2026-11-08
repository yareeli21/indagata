"""Router del análisis de respuestas de entrevista (prefijo `/conocimiento`, vía api-gateway).

- POST  /conocimiento/{id_crudo}/documento/analisis                     inicia el análisis (segundo plano)
- GET   /conocimiento/{id_crudo}/documento/analisis                     avance y análisis por intercambio
- PATCH /conocimiento/{id_crudo}/documento/analisis/{participante}/{n}  corrección del investigador
- PATCH /conocimiento/{id_crudo}/documento/polaridad/{pregunta}         polaridad decidida por el investigador (encuestas)
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


class Polaridad(BaseModel):
    favorables: list[str] = Field(default_factory=list)
    desfavorables: list[str] = Field(default_factory=list)


class Correccion(BaseModel):
    unidades: list[Unidad] | None = None
    postura: str | None = None
    motivo: str | None = Field(default=None, max_length=300)


@router.post("/{id_crudo}/documento/analisis", status_code=status.HTTP_202_ACCEPTED,
             summary="Analiza el documento: respuestas de entrevista (unidades, postura, temas…) o polaridad de encuesta")
def iniciar(id_crudo: int, db: DBSession, usuario: Investigador, tareas: BackgroundTasks,
            modelo: bool = True) -> dict[str, Any]:
    """`?modelo=false`: solo reglas, sin el modelo de lenguaje."""
    avance = analisis.iniciar(db, usuario, id_crudo)
    if avance.pop("nuevo"):
        tareas.add_task(analisis.correr, sessionmaker(bind=db.get_bind(), future=True), id_crudo, None, modelo)
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


@router.patch("/{id_crudo}/documento/polaridad/{pregunta}", summary="Polaridad de una pregunta de encuesta, decidida por el investigador")
def corregir_polaridad(id_crudo: int, pregunta: str, cuerpo: Polaridad, db: DBSession, usuario: Investigador) -> dict[str, Any]:
    return analisis.corregir_polaridad(db, usuario, id_crudo, pregunta, cuerpo.favorables, cuerpo.desfavorables)
