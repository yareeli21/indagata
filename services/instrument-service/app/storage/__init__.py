"""Almacenamiento de archivos del instrument-service (puerto + fábrica).

PUNTO ÚNICO DE CAMBIO para delegar al storage-service.

`get_storage()` devuelve una implementación de `StoragePort` según la variable
de entorno STORAGE_BACKEND:
  - "http"  → HttpStorageBackend: el storage-service guarda el archivo crudo sin
              cambios (es el valor que usa docker-compose).
  - "local" → LocalStorageBackend: escribe en storage/raw (desarrollo sin el
              storage-service levantado). Es el valor por defecto.
Upload y delete dependen solo de `StoragePort`.
"""
from __future__ import annotations

import os
from functools import lru_cache

from app.storage.local_backend import LocalStorageBackend
from app.storage.port import StoragePort, StoredRef, StorageError

__all__ = ["get_storage", "StoragePort", "StoredRef", "StorageError"]


@lru_cache(maxsize=1)
def get_storage() -> StoragePort:
    """Devuelve el almacenamiento activo (ver STORAGE_BACKEND)."""
    if os.getenv("STORAGE_BACKEND", "local").strip().lower() == "http":
        from app.storage.http_backend import HttpStorageBackend

        return HttpStorageBackend()
    return LocalStorageBackend()
