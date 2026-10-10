"""Cliente HTTP del storage-service (autoridad de archivos e índice vectorial).

El metadata-service nunca lee el disco: pide al storage-service el contenido del
instrumento (tabla o texto), guarda ahí el JSON estandarizado y le solicita la
ingesta al RAG. Se autentica con un token de servicio (shared.auth.servicio).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from shared.auth import cabeceras_servicio
from shared.db.core.config import settings

logger = logging.getLogger("metadata-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=60.0, pool=5.0)
# La primera ingesta carga el modelo de embeddings: se le da más margen.
_TIMEOUT_INDICE = httpx.Timeout(connect=5.0, read=300.0, write=60.0, pool=5.0)


class StorageError(Exception):
    """El storage-service no respondió o devolvió un error."""

    def __init__(self, mensaje: str, status_code: int | None = None) -> None:
        super().__init__(mensaje)
        self.status_code = status_code


def _url(ruta: str) -> str:
    return f"{settings.STORAGE_SERVICE_URL.rstrip('/')}{ruta}"


def _detalle(resp: httpx.Response) -> str:
    try:
        datos = resp.json()
    except ValueError:
        return resp.text[:200]
    return str(datos.get("detail")) if isinstance(datos, dict) else str(datos)[:200]


def _pedir(metodo: str, ruta: str, *, timeout: httpx.Timeout = _TIMEOUT, **kwargs: Any) -> httpx.Response:
    try:
        with httpx.Client(timeout=timeout) as cliente:
            resp = cliente.request(metodo, _url(ruta), headers=cabeceras_servicio(), **kwargs)
    except httpx.HTTPError as exc:
        logger.warning("storage-service no disponible (%s %s): %s", metodo, ruta, exc)
        raise StorageError("El servicio de almacenamiento no está disponible.") from exc
    if resp.status_code >= 400:
        raise StorageError(_detalle(resp), resp.status_code)
    return resp


def tabla(ruta: str, max_filas: int = 20000) -> dict[str, Any]:
    return _pedir("GET", "/almacenamiento/tabla", params={"ruta": ruta, "max_filas": max_filas}).json()


def texto(ruta: str) -> dict[str, Any]:
    return _pedir("GET", "/almacenamiento/texto", params={"ruta": ruta}).json()


def descargar(ruta: str) -> bytes:
    return _pedir("GET", "/almacenamiento/descarga", params={"ruta": ruta}).content


def guardar_json(id_crudo: int, tipo: str, contenido: dict[str, Any], nombre: str) -> dict[str, Any]:
    return _pedir(
        "POST",
        "/almacenamiento/json",
        json={"instrumentoId": str(id_crudo), "tipo": tipo, "contenido": contenido, "nombre": nombre},
    ).json()


def obtener_json(id_crudo: int, tipo: str) -> dict[str, Any] | None:
    """Contenido del último artefacto JSON (`metadata`/`analysis`) o None si no hay."""
    try:
        detalle = _pedir("GET", f"/almacenamiento/artefacto/{tipo}/{id_crudo}").json()
    except StorageError as exc:
        if exc.status_code == 404:
            return None
        raise
    contenido = detalle.get("contenido")
    return contenido if isinstance(contenido, dict) else None


def indexar(id_crudo: int, reindexar: bool = True) -> dict[str, Any]:
    return _pedir(
        "POST",
        f"/almacenamiento/indice/instrumentos/{id_crudo}",
        json={"reindexar": reindexar},
        timeout=_TIMEOUT_INDICE,
    ).json()


def desindexar(id_crudo: int) -> dict[str, Any]:
    return _pedir("DELETE", f"/almacenamiento/indice/instrumentos/{id_crudo}").json()
