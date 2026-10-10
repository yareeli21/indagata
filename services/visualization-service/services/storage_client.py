"""Cliente HTTP del storage-service (archivos e índice vectorial).

El visualization-service no lee archivos de otros servicios directamente: las
descargas, las tablas para exportar a .sav y la ingesta al RAG pasan por el
storage-service, autenticándose con un token de servicio.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import httpx

from shared.auth import cabeceras_servicio
from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)
_TIMEOUT_INDICE = httpx.Timeout(connect=5.0, read=300.0, write=60.0, pool=5.0)


class StorageError(Exception):
    def __init__(self, mensaje: str, status_code: int | None = None) -> None:
        super().__init__(mensaje)
        self.status_code = status_code


@dataclass
class Descarga:
    contenido: bytes
    nombre: str
    mime_type: str
    sha256: str | None


def _pedir(metodo: str, ruta: str, *, timeout: httpx.Timeout = _TIMEOUT, **kwargs: Any) -> httpx.Response:
    url = f"{settings.STORAGE_SERVICE_URL.rstrip('/')}{ruta}"
    try:
        with httpx.Client(timeout=timeout) as cliente:
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


def descargar(ruta: str) -> Descarga:
    resp = _pedir("GET", "/almacenamiento/descarga", params={"ruta": ruta})
    return Descarga(
        contenido=resp.content,
        nombre=unquote(resp.headers.get("x-nombre-archivo", "")) or ruta.rsplit("/", 1)[-1],
        mime_type=resp.headers.get("content-type", "application/octet-stream"),
        sha256=resp.headers.get("x-checksum-sha256"),
    )


def tabla(ruta: str, max_filas: int = 200000) -> dict[str, Any]:
    return _pedir("GET", "/almacenamiento/tabla", params={"ruta": ruta, "max_filas": max_filas}).json()


def obtener_json(id_crudo: int, tipo: str) -> dict[str, Any] | None:
    try:
        detalle = _pedir("GET", f"/almacenamiento/artefacto/{tipo}/{id_crudo}").json()
    except StorageError as exc:
        if exc.status_code == 404:
            return None
        raise
    contenido = detalle.get("contenido")
    return contenido if isinstance(contenido, dict) else None


def ultimo_artefacto(id_crudo: int, tipo: str) -> dict[str, Any] | None:
    lista = _pedir("GET", "/almacenamiento/artefactos", params={"instrumentoId": str(id_crudo), "tipo": tipo}).json()
    return max(lista, key=lambda e: e.get("version", 0)) if lista else None


def guardar_archivo(id_crudo: int, tipo: str, nombre: str, contenido: bytes) -> dict[str, Any]:
    return _pedir(
        "POST",
        "/almacenamiento/archivo",
        files={"archivo": (nombre, contenido, "application/octet-stream")},
        data={"tipo": tipo, "instrumentoId": str(id_crudo)},
    ).json()


def estado_indice(id_crudo: int) -> dict[str, Any]:
    return _pedir("GET", f"/almacenamiento/indice/instrumentos/{id_crudo}").json()


def indexar(id_crudo: int, reindexar: bool = True) -> dict[str, Any]:
    return _pedir(
        "POST",
        f"/almacenamiento/indice/instrumentos/{id_crudo}",
        json={"reindexar": reindexar},
        timeout=_TIMEOUT_INDICE,
    ).json()
