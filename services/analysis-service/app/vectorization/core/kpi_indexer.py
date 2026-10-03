"""Indexación de la colección `kpis` en Chroma desde la tabla `tt_rag.kpi`.

Cada KPI se vectoriza con un texto construido a partir de su nombre, descripción,
categoría y ámbito. El id del punto en Chroma es el `kpi_id` (como string) para
poder mapear de vuelta a la BD tras una búsqueda.

Operación de mantenimiento: se ejecuta al sembrar el catálogo de KPIs o cuando
este cambia. No se dispara en cada carga de instrumento.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.vectorization.core import chroma_client, embeddings
from shared.db.core.config import settings
from shared.models.kpi import KPI


@dataclass(frozen=True)
class ReindexResult:
    """Resultado de reindexar la colección de KPIs."""

    coleccion: str
    n_kpis: int


def build_kpi_text(kpi: KPI) -> str:
    """Construye el texto representativo de un KPI para vectorizar."""
    partes = [kpi.nombre_kpi]
    if kpi.descripcion:
        partes.append(kpi.descripcion)
    if kpi.categoria:
        partes.append(f"Categoría: {kpi.categoria}")
    if kpi.ambito:
        partes.append(f"Ámbito: {kpi.ambito}")
    return ". ".join(p for p in partes if p)


def reindex_kpis(db: Session, *, collection=None) -> ReindexResult:
    """(Re)vectoriza TODOS los KPIs de la BD en la colección `kpis`.

    Args:
        db:         Sesión de BD.
        collection: Colección Chroma a usar (opcional; para inyección en tests).

    Returns:
        ReindexResult con el nombre de la colección y el nº de KPIs indexados.
    """
    coleccion = collection or chroma_client.get_or_create_collection(
        settings.CHROMA_COLLECTION_KPIS
    )

    kpis = db.query(KPI).order_by(KPI.kpi_id).all()
    if not kpis:
        return ReindexResult(coleccion=settings.CHROMA_COLLECTION_KPIS, n_kpis=0)

    textos = [build_kpi_text(k) for k in kpis]
    vectores = embeddings.embed_texts(textos)

    ids = [str(k.kpi_id) for k in kpis]
    metadatas = [
        {
            "kpi_id": k.kpi_id,
            "nombre_kpi": k.nombre_kpi,
            "categoria": k.categoria or "",
            "ambito": k.ambito or "",
        }
        for k in kpis
    ]

    chroma_client.upsert(coleccion, ids, vectores, textos, metadatas)
    return ReindexResult(coleccion=settings.CHROMA_COLLECTION_KPIS, n_kpis=len(kpis))
