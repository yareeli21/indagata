"""Modelo de embeddings (sentence-transformers), compartido por el módulo.

COPIA 1:1 de services/analysis-service/app/vectorization/core/embeddings.py
(diseño §1, §4.1). Los servicios no comparten código de aplicación entre
carpetas `services/*` (solo `shared/`), por lo que este módulo se duplica aquí
sin cambios para reusar el mismo modelo/dimensión (768) y asegurar que los
vectores de ambas apps sean compatibles.

Carga perezosa: el modelo (varios cientos de MB) se instancia la primera vez que
se usa, no al importar. Así los tests que no tocan embeddings y el arranque del
servicio no pagan ese costo.

El modelo se toma de settings.EMBEDDING_MODEL (multilingüe por defecto).
"""
from __future__ import annotations

import threading

from shared.db.core.config import settings

_model = None
_lock = threading.Lock()


def _get_model():
    """Devuelve el SentenceTransformer, cargándolo una sola vez (thread-safe)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Vectoriza una lista de textos. Devuelve una lista de vectores (floats)."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    """Vectoriza un solo texto."""
    return embed_texts([text])[0]
