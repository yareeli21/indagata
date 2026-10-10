"""Acceso de SOLO LECTURA a ChromaDB y modelo de embeddings.

El visualization-service nunca escribe vectores: la colección `instrumentos` la
escribe el storage-service y la colección `kpis` el analysis-service. Aquí solo
se consultan (chat RAG, preguntas que miden un KPI, instrumentos parecidos).

Mismo modelo multilingüe (768 dim) y distancia coseno que los servicios que
escriben, para que los vectores sean comparables. Carga perezosa y thread-safe.
"""
from __future__ import annotations

import threading
from typing import Any

from shared.db.core.config import settings

_client = None
_model = None
_lock = threading.Lock()


def get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                import chromadb

                _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client


def coleccion_existente(nombre: str):
    """La colección si existe; None si todavía no se ha creado."""
    cliente = get_client()
    nombres = {c if isinstance(c, str) else c.name for c in cliente.list_collections()}
    if nombre not in nombres:
        return None
    return cliente.get_or_create_collection(name=nombre, metadata={"hnsw:space": "cosine"})


def embed_texts(textos: list[str]) -> list[list[float]]:
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


def embed_text(texto: str) -> list[float]:
    return embed_texts([texto])[0]


def a_lista(vector: Any) -> list[float] | None:
    """Normaliza un embedding de Chroma (lista o ndarray) a lista de floats."""
    if vector is None:
        return None
    return [float(x) for x in vector]
