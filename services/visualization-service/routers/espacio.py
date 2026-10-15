"""Router — ESPACIO VECTORIAL explicable (solo lectura).

  GET /visualizacion/espacio/mapa   KPIs, instrumentos y (opcional) chunks en 2D,
                                    con varianza explicada y clusters de KPIs.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import DBSession, Investigador
from models import MapaEspacioOut
from services.espacio import mapa as servicio_mapa

router = APIRouter(prefix="/visualizacion/espacio", tags=["espacio-vectorial"])


@router.get(
    "/mapa",
    response_model=MapaEspacioOut,
    summary="Mapa 2D del espacio de embeddings",
    description=(
        "Proyecta con PCA (2 componentes, ajustado sobre KPIs + instrumentos) los "
        "embeddings del catálogo de KPIs y de cada instrumento (metadatos + preguntas). "
        "Con `chunks=true` añade los chunks del RAG proyectados con la misma "
        "transformación (fuente marcada como provisional). Incluye la varianza "
        "explicada por cada componente y clusters semánticos de KPIs."
    ),
)
def mapa(
    _: Investigador,
    db: DBSession,
    chunks: bool = False,
    limiteChunks: int = Query(3000, ge=0, le=20000),
) -> MapaEspacioOut:
    try:
        return MapaEspacioOut(**servicio_mapa.mapa(db, chunks=chunks, limite_chunks=limiteChunks))
    except Exception as exc:  # noqa: BLE001 — Chroma o el modelo no disponibles
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo construir el espacio vectorial: {exc}",
        ) from exc
