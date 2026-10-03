"""Inspección de solo lectura de los vectores del summary.

Permite confirmar que el embedding del instrumento existe, su dimensión y con
qué modelo se generó. Útil para auditar que se usó el modelo esperado
(p. ej. multilingüe de 768 dimensiones).
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.vectorization.core import chroma_client
from app.vectorization.schemas.vectorizacion import SummaryEmbeddingResponse
from shared.db.core.config import settings
from shared.models.coleccion_vectorial import ColeccionVectorial

logger = logging.getLogger(__name__)

# Nº de valores del vector que se devuelven como muestra.
_PREVIEW_DIMS = 12
# Nº de caracteres del documento que se devuelven como muestra.
_PREVIEW_CHARS = 300


def _resolver_modelo(db: Session) -> str | None:
    """Modelo registrado para la colección del summary, o el de settings."""
    col = (
        db.query(ColeccionVectorial)
        .filter(ColeccionVectorial.nombre == settings.CHROMA_COLLECTION_SUMMARY)
        .first()
    )
    if col is not None and col.embedding_model:
        return col.embedding_model
    return settings.EMBEDDING_MODEL


class InspectionService:
    """Caso de uso de solo lectura: ver el embedding del summary."""

    @staticmethod
    def get_summary_embedding(
        db: Session, id_instrumento: int
    ) -> SummaryEmbeddingResponse:
        """Lee el vector del summary del instrumento desde Chroma."""
        try:
            coleccion = chroma_client.get_or_create_collection(
                settings.CHROMA_COLLECTION_SUMMARY
            )
            punto = chroma_client.get_point(coleccion, str(id_instrumento))
        except Exception as exc:
            logger.exception("No se pudo consultar Chroma.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Servicio de vectorización no disponible: {exc}",
            ) from exc

        if punto is None or punto.get("embedding") is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No hay summary vectorizado para el instrumento {id_instrumento}. "
                    f"Genera primero las propuestas (POST /vectorizacion/propuestas)."
                ),
            )

        vector = punto["embedding"]
        documento = punto.get("document") or ""

        return SummaryEmbeddingResponse(
            id_instrumento=id_instrumento,
            coleccion=settings.CHROMA_COLLECTION_SUMMARY,
            embedding_model=_resolver_modelo(db),
            dimension=len(vector),
            embedding_preview=[round(float(x), 6) for x in vector[:_PREVIEW_DIMS]],
            metadata=punto.get("metadata") or {},
            document_preview=documento[:_PREVIEW_CHARS],
        )
