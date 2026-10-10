"""Backend de almacenamiento HTTP — delega en el storage-service.

El archivo se envía tal cual (bytes intactos) a `POST /almacenamiento/archivo`
con tipo `raw`; la referencia que se persiste en `raw_data` es la clave que
devuelve el storage-service (`raw/_/<versión>__<nombre>`), que es también su ruta
relativa dentro de storage. Se autentica con un token de servicio.
"""
from __future__ import annotations

import logging

import httpx

from shared.auth import cabeceras_servicio
from shared.db.core.config import settings

from app.storage.port import StoragePort, StoredRef, StorageError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)


class HttpStorageBackend(StoragePort):
    """Guarda y elimina archivos a través del storage-service."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or settings.STORAGE_SERVICE_URL).rstrip("/")

    def guardar(self, content: bytes, nombre_original: str) -> StoredRef:
        try:
            with httpx.Client(timeout=_TIMEOUT) as cliente:
                resp = cliente.post(
                    f"{self._base}/almacenamiento/archivo",
                    headers=cabeceras_servicio(),
                    files={"archivo": (nombre_original, content, "application/octet-stream")},
                    data={"tipo": "raw"},
                )
        except httpx.HTTPError as exc:
            raise StorageError(f"El storage-service no está disponible: {exc}") from exc
        if resp.status_code != 200:
            raise StorageError(f"El storage-service rechazó el archivo (HTTP {resp.status_code}): {resp.text[:200]}")
        datos = resp.json()
        return StoredRef(nombre_original=nombre_original, ruta=datos["key"], size_bytes=datos["size_bytes"])

    def eliminar(self, ruta: str) -> None:
        if not ruta:
            return
        try:
            with httpx.Client(timeout=_TIMEOUT) as cliente:
                cliente.delete(
                    f"{self._base}/almacenamiento/archivo",
                    headers=cabeceras_servicio(),
                    params={"ruta": ruta},
                )
        except httpx.HTTPError as exc:  # idempotente: no se propaga
            logger.warning("No se pudo eliminar %s en el storage-service: %s", ruta, exc)

    def purgar_instrumento(self, id_crudo: int) -> None:
        try:
            with httpx.Client(timeout=_TIMEOUT) as cliente:
                cliente.delete(f"{self._base}/almacenamiento/instrumentos/{id_crudo}", headers=cabeceras_servicio())
        except httpx.HTTPError as exc:
            logger.warning("No se pudieron purgar los artefactos de %s: %s", id_crudo, exc)
