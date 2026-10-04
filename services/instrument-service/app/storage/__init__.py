"""Almacenamiento de archivos del instrument-service (puerto + fábrica).

PUNTO ÚNICO DE CAMBIO para delegar al storage-service.

El servicio obtiene el almacenamiento llamando a `get_storage()`, que devuelve
una implementación de `StoragePort`. Hoy devuelve el backend LOCAL provisional.

Cuando exista el storage-service, basta con:
  1. Crear `app/storage/http_backend.py` con `HttpStorageBackend(StoragePort)`
     que llame a su API (p. ej. settings.STORAGE_SERVICE_URL).
  2. Cambiar la línea marcada abajo para devolver ese backend.
Nada más del servicio cambia: upload y delete dependen solo de `StoragePort`.
"""
from __future__ import annotations

from functools import lru_cache

from app.storage.local_backend import LocalStorageBackend
from app.storage.port import StoragePort, StoredRef, StorageError

__all__ = ["get_storage", "StoragePort", "StoredRef", "StorageError"]


@lru_cache(maxsize=1)
def get_storage() -> StoragePort:
    """Devuelve el almacenamiento activo.

    👉 CUANDO EXISTA EL STORAGE-SERVICE: reemplazar esta línea por
       `return HttpStorageBackend()` (y nada más).
    """
    return LocalStorageBackend()
