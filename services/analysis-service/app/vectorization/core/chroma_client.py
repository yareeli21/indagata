"""Cliente de ChromaDB (servidor en contenedor).

Conexión por HTTP al servicio `chromadb` (DNS interno en Docker) usando
settings.CHROMA_HOST / CHROMA_PORT. Expone utilidades mínimas para obtener/crear
colecciones y hacer upsert/consulta con vectores ya calculados (los embeddings se
calculan en embeddings.py, no aquí: Chroma solo almacena e indexa).
"""
from __future__ import annotations

import threading
from typing import Any

from shared.db.core.config import settings

_client = None
_lock = threading.Lock()


def get_client():
    """Devuelve un HttpClient de Chroma, reutilizando la conexión (thread-safe)."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                import chromadb

                _client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                )
    return _client


def get_or_create_collection(name: str, client: Any | None = None):
    """Obtiene (o crea) una colección por nombre.

    Usa distancia coseno para que la similitud sea comparable entre vectores
    normalizados. `client` permite inyectar un cliente alterno (p. ej. efímero en
    pruebas).
    """
    cli = client or get_client()
    return cli.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def delete_collection(name: str, *, client: Any | None = None) -> None:
    """Borra una colección por nombre (idempotente).

    No lanza si la colección no existe. `client` permite inyectar un cliente
    alterno (p. ej. efímero en pruebas), igual que `get_or_create_collection`.
    """
    cli = client or get_client()
    try:
        cli.delete_collection(name)
    except Exception:  # noqa: BLE001 -- "no existe" varía por backend; es idempotente
        pass


def upsert(
    collection,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    """Inserta o actualiza puntos en una colección."""
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query(
    collection,
    query_embedding: list[float],
    top_k: int,
) -> dict[str, Any]:
    """Consulta los `top_k` vecinos más cercanos a un vector."""
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )


def get_point(collection, point_id: str) -> dict[str, Any] | None:
    """Lee un punto por id, incluyendo su embedding.

    Devuelve {document, metadata, embedding} o None si no existe. Chroma no
    devuelve el vector salvo que se pida explícitamente con include=["embeddings"].
    """
    res = collection.get(
        ids=[point_id],
        include=["documents", "metadatas", "embeddings"],
    )
    ids = res.get("ids") or []
    if not ids:
        return None

    documents = res.get("documents") or [None]
    metadatas = res.get("metadatas") or [None]
    embeddings = res.get("embeddings")
    # El embedding puede venir como ndarray; normalizar a lista.
    vector = None
    if embeddings is not None and len(embeddings) > 0 and embeddings[0] is not None:
        vector = list(embeddings[0])

    return {
        "document": documents[0],
        "metadata": metadatas[0],
        "embedding": vector,
    }
