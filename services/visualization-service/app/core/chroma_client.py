"""Cliente de ChromaDB (servidor en contenedor).

COPIA de services/analysis-service/app/vectorization/core/chroma_client.py
(diseño §1, §4.3). Única desviación respecto del original, ADITIVA y
retrocompatible: `query(...)` recibe un parámetro opcional
`where: dict | None = None` que se pasa a `collection.query`; con `None` el
comportamiento es idéntico al original (Chroma ignora el filtro). Permite al
chat filtrar por `where={"instrumentoId": {"$in": [...]}}` (§4.3). También se
añade el helper `nombre_coleccion(inv_id)` (§4.4), inexistente en el original.

El resto (`get_client`, `get_or_create_collection` con `hnsw:space=cosine`,
`upsert`, `get_point`, el `_lock`) se copia sin cambios.

Conexión por HTTP al servicio `chromadb` (DNS interno en Docker) usando
settings.CHROMA_HOST / CHROMA_PORT. Los embeddings se calculan en embeddings.py,
no aquí: Chroma solo almacena e indexa.
"""
from __future__ import annotations

import re
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


def nombre_coleccion(investigacion_id: str) -> str:
    """Nombre de colección por investigación: `investigacion_<slug>` (§4.4).

    AÑADIDO respecto del original de analysis-service. Chroma restringe los
    nombres de colección, así que el `investigacionId` opaco del frontend se
    sanea a `[a-z0-9_-]` (minúsculas; cualquier otro carácter -> `_`).
    """
    slug = re.sub(r"[^a-z0-9_-]+", "_", (investigacion_id or "").strip().lower())
    slug = slug.strip("_") or "default"
    return f"investigacion_{slug}"


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
    where: dict | None = None,
) -> dict[str, Any]:
    """Consulta los `top_k` vecinos más cercanos a un vector.

    Única desviación aditiva respecto del original: `where` opcional. Con `None`
    el resultado es idéntico al original (Chroma ignora el filtro).
    """
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
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
