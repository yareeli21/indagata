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


def _modelo():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(textos: list[str]) -> list[list[float]]:
    """Vectoriza textos con el modelo de settings.EMBEDDING_MODEL."""
    if not textos:
        return []
    vectores = _modelo().encode(textos, normalize_embeddings=True, convert_to_numpy=True)
    return [v.tolist() for v in vectores]


def max_tokens() -> int:
    """Tokens que el modelo de embeddings lee de cada texto (`max_seq_length`, 128 en el modelo actual)."""
    return int(_modelo().max_seq_length)


def contar_tokens(texto: str) -> int:
    """Tokens de un texto con el tokenizador del modelo, incluidos los especiales (7 nov 2026: lo que pasa de
    `max_tokens()` no se embebe, así que los chunks se miden en tokens y no en caracteres)."""
    return len(_modelo().tokenizer(texto, add_special_tokens=True)["input_ids"])
