"""Paso 1 — Proponer KPIs por similitud semántica.

Flujo:
  1. Parsea el tipo de instrumento y el JSON recibido.
  2. Extrae los metadatos clave del JSON (según el tipo).
  3. Construye el summary (metadatos clave + instrumento original en texto).
  4. Vectoriza el summary y lo guarda en la colección `summary_instrument`.
  5. Busca en la colección `kpis` los top_k más cercanos y los devuelve con score.

No modifica el JSON (eso ocurre en el paso 2, tras la decisión del usuario).
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException, status

from app.vectorization.config.constants import TipoInstrumento
from app.vectorization.core import embeddings, kpi_search
from app.vectorization.core.metadata_extractor import extract_key_metadata
from app.vectorization.core.summary_builder import build_summary
from app.vectorization.schemas.vectorizacion import PropuestaKPI, PropuestasResponse

logger = logging.getLogger(__name__)


def _parse_tipo(valor: str) -> TipoInstrumento:
    try:
        return TipoInstrumento(valor.strip().lower())
    except ValueError:
        validos = ", ".join(t.value for t in TipoInstrumento)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo_instrumento inválido. Valores aceptados: {validos}.",
        )


def _parse_json(raw: bytes) -> dict:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El archivo JSON no es válido: {exc}",
        )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El JSON raíz debe ser un objeto.",
        )
    return data


class ProposalService:
    """Caso de uso del paso 1: proponer KPIs para un instrumento."""

    @staticmethod
    def propose(
        id_instrumento: int,
        tipo_instrumento_raw: str,
        json_bytes: bytes,
        instrumento_original: str,
    ) -> tuple[PropuestasResponse, dict]:
        """Genera las propuestas de KPIs.

        Returns:
            (respuesta, json_instrumento) — el JSON parseado se devuelve también
            para que el frontend lo reenvíe tal cual en el paso 2.
        """
        tipo = _parse_tipo(tipo_instrumento_raw)
        data = _parse_json(json_bytes)

        # 2-3. Metadatos clave + summary.
        metadatos = extract_key_metadata(data, tipo)
        summary_text = build_summary(metadatos, instrumento_original)
        if not summary_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se pudo construir el summary (sin metadatos ni instrumento original).",
            )

        # 4. Vectorizar el summary e indexarlo.
        try:
            summary_vector = embeddings.embed_text(summary_text)
            kpi_search.index_summary(
                id_instrumento, tipo.value, summary_text, summary_vector
            )
            # 5. Buscar KPIs cercanos.
            matches = kpi_search.search_kpis(summary_vector)
        except Exception as exc:  # Chroma/embeddings no disponibles
            logger.exception("Fallo en la vectorización o búsqueda de KPIs.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Servicio de vectorización no disponible: {exc}",
            ) from exc

        propuestas = [
            PropuestaKPI(
                kpi_id=m.kpi_id,
                nombre_kpi=m.nombre_kpi,
                categoria=m.categoria or None,
                ambito=m.ambito or None,
                score=m.score,
            )
            for m in matches
        ]

        respuesta = PropuestasResponse(
            id_instrumento=id_instrumento,
            tipo_instrumento=tipo.value,
            metadatos_clave=metadatos,
            propuestas=propuestas,
        )
        return respuesta, data
