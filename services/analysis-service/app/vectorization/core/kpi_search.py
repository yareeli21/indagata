"""Vectorización del summary y búsqueda semántica de KPIs cercanos.

Dos pasos:
  1. index_summary(): añade/actualiza el punto del instrumento en la colección
     `summary_instrument` (id = id_instrumento). El vector es el summary
     (instrumento original + metadatos clave), sin respuestas.
  2. search_kpis(): consulta la colección `kpis` con ese vector y devuelve los
     `top_k` KPIs más cercanos, con un score de similitud, filtrando por umbral.

El score se deriva de la distancia coseno de Chroma: score = 1 - distancia, en
[0, 1] (mayor = más parecido). Las colecciones se crean con hnsw:space=cosine.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.vectorization.config.constants import SUMMARY_SECCION
from app.vectorization.core import chroma_client, embeddings
from shared.db.core.config import settings


@dataclass(frozen=True)
class KpiMatch:
    """Un KPI candidato devuelto por la búsqueda semántica."""

    kpi_id: int
    nombre: str
    polaridad_rendimiento: str
    tipo_objetivo_estrategico: str
    score: float


def index_summary(
    id_instrumento: int,
    tipo_instrumento: str,
    summary_text: str,
    summary_vector: list[float],
    *,
    collection=None,
) -> None:
    """Añade/actualiza el vector del summary del instrumento en `summary_instrument`."""
    coleccion = collection or chroma_client.get_or_create_collection(
        settings.CHROMA_COLLECTION_SUMMARY
    )
    chroma_client.upsert(
        coleccion,
        ids=[str(id_instrumento)],
        embeddings=[summary_vector],
        documents=[summary_text],
        metadatas=[
            {
                "id_instrumento": id_instrumento,
                "tipo_instrumento": tipo_instrumento,
                "seccion": SUMMARY_SECCION,
            }
        ],
    )


def _distance_to_score(distance: float) -> float:
    """Convierte distancia coseno [0,2] a score de similitud [0,1]."""
    score = 1.0 - float(distance)
    # Acotar por seguridad numérica.
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def search_kpis(
    summary_vector: list[float],
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    collection=None,
) -> list[KpiMatch]:
    """Busca los KPIs más cercanos al summary.

    Args:
        summary_vector: Vector del summary del instrumento.
        top_k:          Nº de candidatos (default: settings.KPI_SEARCH_TOP_K).
        min_score:      Score mínimo para incluir (default: settings.KPI_SEARCH_MIN_SCORE).
        collection:     Colección `kpis` (opcional; para inyección en tests).

    Returns:
        Lista de KpiMatch ordenada por score descendente (ya filtrada por umbral).
    """
    k = top_k if top_k is not None else settings.KPI_SEARCH_TOP_K
    umbral = min_score if min_score is not None else settings.KPI_SEARCH_MIN_SCORE

    coleccion = collection or chroma_client.get_or_create_collection(
        settings.CHROMA_COLLECTION_KPIS
    )
    res = chroma_client.query(coleccion, summary_vector, top_k=k)

    # Chroma devuelve listas anidadas (una por query). Tomamos la primera.
    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    matches: list[KpiMatch] = []
    for meta, dist in zip(metadatas, distances):
        score = _distance_to_score(dist)
        if score < umbral:
            continue
        matches.append(
            KpiMatch(
                kpi_id=int(meta.get("kpi_id")),
                nombre=str(meta.get("nombre", "")),
                polaridad_rendimiento=str(meta.get("polaridad_rendimiento", "")),
                tipo_objetivo_estrategico=str(meta.get("tipo_objetivo_estrategico", "")),
                score=round(score, 4),
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches
