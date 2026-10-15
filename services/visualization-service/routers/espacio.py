"""Router — ESPACIO VECTORIAL explicable (solo lectura).

  GET /visualizacion/espacio/mapa                 KPIs, instrumentos y (opcional)
                                                  chunks en 2D, con varianza
                                                  explicada y clusters de KPIs.
  GET /visualizacion/espacio/vecinos/{tipo}/{id}  vecinos de un punto por coseno
                                                  en el espacio original.
  POST /visualizacion/espacio/buscar              frase libre: posición en el mapa
                                                  (mismo modelo y PCA) y vecinos.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query, status

from dependencies import DBSession, Investigador
from models import BusquedaEspacioIn, BusquedaEspacioOut, MapaEspacioOut, VecinosEspacioOut
from services.espacio import buscar as servicio_buscar
from services.espacio import mapa as servicio_mapa
from services.espacio import vecinos as servicio_vecinos

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
        "explicada por cada componente y clusters semánticos de KPIs. Con "
        "`alinear=true` cada grupo se centra en su propio centroide antes del PCA "
        "(quita la brecha de modalidad; solo cambia el dibujo)."
    ),
)
def mapa(
    _: Investigador,
    db: DBSession,
    chunks: bool = False,
    limiteChunks: int = Query(3000, ge=0, le=20000),
    alinear: bool = False,
) -> MapaEspacioOut:
    try:
        return MapaEspacioOut(
            **servicio_mapa.mapa(db, chunks=chunks, limite_chunks=limiteChunks, alinear=alinear)
        )
    except Exception as exc:  # noqa: BLE001 — Chroma o el modelo no disponibles
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo construir el espacio vectorial: {exc}",
        ) from exc


@router.get(
    "/vecinos/{tipo}/{ref}",
    response_model=VecinosEspacioOut,
    summary="Vecinos de un punto del espacio vectorial",
    description=(
        "Para un KPI, instrumento o chunk devuelve los `k` KPIs, instrumentos y "
        "chunks más parecidos, ordenados por similitud coseno entre los embeddings "
        "originales (nunca por la distancia en el mapa 2D)."
    ),
)
def vecinos(
    _: Investigador,
    db: DBSession,
    tipo: Literal["kpi", "instrumento", "chunk"],
    ref: str = Path(min_length=1, max_length=200),
    k: int = Query(8, ge=1, le=30),
) -> VecinosEspacioOut:
    try:
        return VecinosEspacioOut(**servicio_vecinos.vecinos(db, tipo, ref, k))
    except servicio_vecinos.PuntoNoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — Chroma o el modelo no disponibles
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudieron calcular los vecinos: {exc}",
        ) from exc


@router.post(
    "/buscar",
    response_model=BusquedaEspacioOut,
    summary="Búsqueda semántica en el espacio vectorial",
    description=(
        "Embebe la frase con el mismo modelo que el resto del mapa, la proyecta con "
        "el mismo PCA (vista original y alineada) y devuelve los KPIs, instrumentos "
        "y chunks más parecidos por similitud coseno en el espacio original."
    ),
)
def buscar(peticion: BusquedaEspacioIn, _: Investigador, db: DBSession) -> BusquedaEspacioOut:
    texto = " ".join(peticion.texto.split())
    if len(texto) < 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escribe al menos 3 caracteres.")
    try:
        return BusquedaEspacioOut(**servicio_buscar.buscar(db, texto, peticion.k))
    except Exception as exc:  # noqa: BLE001 — Chroma o el modelo no disponibles
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo hacer la búsqueda: {exc}",
        ) from exc
