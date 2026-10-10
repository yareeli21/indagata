"""Cliente de ChromaDB y modelo de embeddings del storage-service.

Copia del patrón de analysis-service / visualization-service (los servicios no
comparten código de aplicación): mismo modelo multilingüe (768 dim) y distancia
coseno, para que los vectores que escribe este servicio sean comparables con los
que consultan los demás.

Ambos recursos se cargan de forma perezosa y thread-safe: ni el arranque ni las
pruebas que no los usan pagan su costo.
"""
from __future__ import annotations

import threading
from typing import Any

from shared.db.core.config import settings

_client = None
_model = None
_lock = threading.Lock()


def get_client():
    """HttpClient de Chroma reutilizable."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                import chromadb

                _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client


def coleccion(nombre: str, client: Any | None = None):
    """Obtiene (o crea) una colección con distancia coseno."""
    return (client or get_client()).get_or_create_collection(
        name=nombre, metadata={"hnsw:space": "cosine"}
    )


def embed_texts(textos: list[str]) -> list[list[float]]:
    """Vectoriza textos con el modelo de settings.EMBEDDING_MODEL."""
    global _model
    if not textos:
        return []
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    vectores = _model.encode(textos, normalize_embeddings=True, convert_to_numpy=True)
    return [v.tolist() for v in vectores]
