"""Router — noticias de educación e investigación (panel del chat).

  GET /visualizacion/noticias[?actualizar=true]   fuentes RSS de config/noticias.yaml (+ GNews con clave)
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from dependencies import Investigador
from services import noticias

router = APIRouter(prefix="/visualizacion", tags=["noticias"])


@router.get("/noticias", summary="Noticias recientes de educación e investigación")
async def listar(_: Investigador, actualizar: bool = Query(False)) -> dict:
    return await run_in_threadpool(noticias.obtener, actualizar)
