"""Indexación de la colección `kpis` en Chroma desde la tabla `tt_rag.kpi`.

Cada KPI se vectoriza con ÚNICAMENTE su `texto_contexto_rag_vectorial` (párrafo RAG
autocontenido); el resto de columnas viajan como metadata escalar. El id del punto
en Chroma es el `kpi_id` (como string) para poder mapear de vuelta a la BD tras una
búsqueda.

Operación de mantenimiento: se ejecuta al sembrar el catálogo de KPIs o cuando
este cambia. No se dispara en cada carga de instrumento. El reindex borra y recrea
la colección antes del upsert, de modo que no sobrevivan puntos obsoletos ni la
clave de metadato vieja `nombre_kpi`.
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
    """Texto a vectorizar: ÚNICAMENTE el párrafo RAG autocontenido del KPI."""
    return kpi.texto_contexto_rag_vectorial or ""


def build_kpi_metadata(kpi: KPI) -> dict:
    """Metadata escalar del punto Chroma (sin None; simétrica a build_kpi_text)."""
    return {
        "kpi_id": kpi.kpi_id,
        "nombre": kpi.nombre or "",
        "polaridad_rendimiento": kpi.polaridad_rendimiento or "",
        "tipo_objetivo_estrategico": kpi.tipo_objetivo_estrategico or "",
        "formula_metrica_calculo": kpi.formula_metrica_calculo or "",
        "descripcion_ampliada_educativa": kpi.descripcion_ampliada_educativa or "",
    }


def reindex_kpis(db: Session, *, client=None) -> ReindexResult:
    """(Re)vectoriza TODOS los KPIs de la BD en la colección `kpis`.

    Borra y recrea la colección antes del upsert para que quede con exactamente
    los KPIs actuales (sin puntos huérfanos ni la clave de metadato vieja).

    Args:
        db:     Sesión de BD.
        client: Cliente Chroma a usar (opcional; para inyección en tests).

    Returns:
        ReindexResult con el nombre de la colección y el nº de KPIs indexados.
    """
    cli = client or chroma_client.get_client()
    nombre = settings.CHROMA_COLLECTION_KPIS

    kpis = db.query(KPI).order_by(KPI.kpi_id).all()
    if not kpis:
        return ReindexResult(coleccion=nombre, n_kpis=0)

    chroma_client.delete_collection(nombre, client=cli)
    coleccion = chroma_client.get_or_create_collection(nombre, client=cli)

    textos = [build_kpi_text(k) for k in kpis]
    vectores = embeddings.embed_texts(textos)
    ids = [str(k.kpi_id) for k in kpis]
    metadatas = [build_kpi_metadata(k) for k in kpis]

    chroma_client.upsert(coleccion, ids, vectores, textos, metadatas)
    return ReindexResult(coleccion=nombre, n_kpis=len(kpis))
