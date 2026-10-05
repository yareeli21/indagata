"""Paso 2 — Confirmar KPIs aceptados y enriquecer el JSON.

Flujo:
  1. Filtra las decisiones aceptadas y valida que los KPIs existan.
  2. Garantiza una fila `documento_vectorizado` para el summary del instrumento
     (es el "chunk" que sustenta la inferencia; idempotente por instrumento).
  3. Persiste cada KPI aceptado en `kpi_inferido` y su evidencia en
     `kpi_inferido_chunk` (con el score mostrado al usuario).
  4. Agrega los KPIs aceptados al JSON bajo la clave `inferred_kpis` y devuelve
     el JSON enriquecido.

Transaccional: si la persistencia falla, se revierte y no se devuelve JSON a medias.
"""
from __future__ import annotations

import copy
import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.vectorization.config.constants import INFERRED_KPIS_KEY, SUMMARY_SECCION
from app.vectorization.schemas.vectorizacion import (
    ConfirmarRequest,
    ConfirmarResponse,
    KpiAgregado,
)
from shared.db.core.config import settings
from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.kpi_inferido_chunk import KpiInferidoChunk

logger = logging.getLogger(__name__)


def _get_or_create_coleccion_summary(db: Session) -> ColeccionVectorial:
    """Obtiene (o crea) la fila de coleccion_vectorial del summary."""
    col = (
        db.query(ColeccionVectorial)
        .filter(ColeccionVectorial.nombre == settings.CHROMA_COLLECTION_SUMMARY)
        .first()
    )
    if col is None:
        col = ColeccionVectorial(
            nombre=settings.CHROMA_COLLECTION_SUMMARY,
            embedding_model=settings.EMBEDDING_MODEL,
        )
        db.add(col)
        db.flush()
    return col


def _get_or_create_doc_summary(
    db: Session, id_instrumento: int
) -> DocumentoVectorizado:
    """Garantiza una fila documento_vectorizado para el summary del instrumento."""
    doc = (
        db.query(DocumentoVectorizado)
        .filter(
            DocumentoVectorizado.instrumento_id == id_instrumento,
            DocumentoVectorizado.seccion == SUMMARY_SECCION,
        )
        .first()
    )
    if doc is not None:
        return doc

    col = _get_or_create_coleccion_summary(db)
    doc = DocumentoVectorizado(
        instrumento_id=id_instrumento,
        coleccion_id=col.coleccion_id,
        chroma_vector_id=str(id_instrumento),
        chunk_index=0,
        seccion=SUMMARY_SECCION,
        chunk_texto=f"summary del instrumento {id_instrumento}",
        chunk_metadata={"tipo": SUMMARY_SECCION},
    )
    db.add(doc)
    db.flush()
    return doc


class EnrichmentService:
    """Caso de uso del paso 2: confirmar KPIs y enriquecer el JSON."""

    @staticmethod
    def confirm(db: Session, request: ConfirmarRequest) -> ConfirmarResponse:
        """Persiste los KPIs aceptados y devuelve el JSON enriquecido."""
        # Validar que el instrumento existe.
        instrumento = db.get(InstrumentoProcesado, request.id_instrumento)
        if instrumento is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrumento {request.id_instrumento} no encontrado.",
            )

        aceptados = [d for d in request.decisiones if d.aceptado]

        # Mapear kpi_id -> KPI (validar existencia y obtener nombres).
        kpis_agregados: list[KpiAgregado] = []
        if aceptados:
            ids = [d.kpi_id for d in aceptados]
            kpis = {k.kpi_id: k for k in db.query(KPI).filter(KPI.kpi_id.in_(ids)).all()}
            faltantes = [i for i in ids if i not in kpis]
            if faltantes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"KPIs inexistentes: {faltantes}.",
                )

            try:
                doc = _get_or_create_doc_summary(db, request.id_instrumento)
                for d in aceptados:
                    # Upsert de kpi_inferido (PK compuesta id_procesado+kpi_id).
                    inferido = db.get(
                        KPIInferido, (request.id_instrumento, d.kpi_id)
                    )
                    if inferido is None:
                        inferido = KPIInferido(
                            id_procesado=request.id_instrumento,
                            kpi_id=d.kpi_id,
                            razon="Aceptado por el usuario (similitud semántica).",
                        )
                        db.add(inferido)
                        db.flush()

                    # Evidencia: enlazar al chunk del summary con su score.
                    evidencia = db.get(
                        KpiInferidoChunk,
                        (
                            request.id_instrumento,
                            d.kpi_id,
                            doc.documento_vectorizado_id,
                        ),
                    )
                    if evidencia is None:
                        db.add(
                            KpiInferidoChunk(
                                id_procesado=request.id_instrumento,
                                kpi_id=d.kpi_id,
                                documento_vectorizado_id=doc.documento_vectorizado_id,
                                score=d.score,
                            )
                        )
                    else:
                        evidencia.score = d.score

                    kpis_agregados.append(
                        KpiAgregado(
                            kpi_id=d.kpi_id,
                            nombre_kpi=kpis[d.kpi_id].nombre_kpi,
                            score=d.score,
                        )
                    )

                db.commit()
            except SQLAlchemyError as exc:
                db.rollback()
                logger.exception("Error al persistir los KPIs inferidos.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudieron registrar los KPIs aceptados.",
                ) from exc

        # Enriquecer el JSON (copia profunda para no mutar el request).
        enriquecido = copy.deepcopy(request.json_instrumento)
        enriquecido[INFERRED_KPIS_KEY] = [
            {"kpi_id": k.kpi_id, "nombre_kpi": k.nombre_kpi, "score": k.score}
            for k in kpis_agregados
        ]

        return ConfirmarResponse(
            id_instrumento=request.id_instrumento,
            kpis_agregados=kpis_agregados,
            json_enriquecido=enriquecido,
        )
