"""Cliente HTTP del storage-service.

cleaning-service no toca el disco: lee el archivo crudo y guarda el CSV limpio a
través del storage-service (único dueño del almacenamiento), autenticándose con
un token de servicio.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from shared.auth import cabeceras_servicio
from shared.db.core.config import settings

logger = logging.getLogger("cleaning-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)


class StorageError(Exception):
    """Fallo al hablar con el storage-service (status_code=None si no respondió)."""

    def __init__(self, mensaje: str, status_code: int | None = None) -> None:
        super().__init__(mensaje)
        self.status_code = status_code


def _pedir(metodo: str, ruta: str, **kwargs: Any) -> httpx.Response:
    url = f"{settings.STORAGE_SERVICE_URL.rstrip('/')}{ruta}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as cliente:
            resp = cliente.request(metodo, url, headers=cabeceras_servicio(), **kwargs)
    except httpx.HTTPError as exc:
        logger.warning("storage-service no disponible (%s %s): %s", metodo, ruta, exc)
        raise StorageError("El servicio de almacenamiento no está disponible.") from exc
    if resp.status_code >= 400:
        try:
            detalle = resp.json().get("detail")
        except ValueError:
            detalle = resp.text[:200]
        raise StorageError(str(detalle), resp.status_code)
    return resp


def descargar(ruta: str) -> bytes:
    """Bytes de un artefacto (el crudo o la clave de respuestas) tal cual se subió."""
    return _pedir("GET", "/almacenamiento/descarga", params={"ruta": ruta}).content


def guardar_limpio(id_crudo: int, nombre: str, contenido: bytes) -> str:
    """Guarda el CSV limpio como artefacto `clean` del instrumento y devuelve su key."""
    resp = _pedir(
        "POST",
        "/almacenamiento/archivo",
        files={"archivo": (nombre, contenido, "text/csv")},
        data={"tipo": "clean", "instrumentoId": str(id_crudo)},
    )
    return str(resp.json()["key"])
