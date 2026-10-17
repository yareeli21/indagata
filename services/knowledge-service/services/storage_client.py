"""Cliente HTTP del storage-service.

knowledge-service no toca el disco: lee el CSV limpio, el instrumento original y
el JSON técnico (y en fases siguientes guarda el documento final) a través del
storage-service, autenticándose con un token de servicio.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from shared.auth import cabeceras_servicio
from shared.db.core.config import settings

logger = logging.getLogger("knowledge-service")

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0)


class StorageError(Exception):
    """Fallo al hablar con el storage-service (status_code=None si no respondió)."""

    def __init__(self, mensaje: str, status_code: int | None = None) -> None:
        super().__init__(mensaje)
        self.status_code = status_code


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


def tabla(ruta: str, max_filas: int = 50000) -> dict[str, Any]:
    """CSV/XLSX como `{headers, rows, n_filas, …}` (detecta separador y BOM)."""
    return _pedir("GET", "/almacenamiento/tabla", params={"ruta": ruta, "max_filas": max_filas}).json()


def texto(ruta: str) -> str:
    """Texto plano de un PDF, DOCX o TXT (el instrumento original)."""
    return str(_pedir("GET", "/almacenamiento/texto", params={"ruta": ruta}).json().get("texto") or "")


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


def guardar_json(id_crudo: int, tipo: str, contenido: dict[str, Any], nombre: str) -> dict[str, Any]:
    """Guarda un JSON versionado (p. ej. tipo `documento`) y devuelve su referencia (key, sha256…)."""
    return _pedir(
        "POST",
        "/almacenamiento/json",
        json={"instrumentoId": str(id_crudo), "tipo": tipo, "contenido": contenido, "nombre": nombre},
    ).json()


def descargar_json(ruta: str) -> dict[str, Any]:
    """Contenido de un artefacto JSON por su key (verifica la huella en storage)."""
    import json

    return json.loads(_pedir("GET", "/almacenamiento/descarga", params={"ruta": ruta}).content.decode("utf-8"))


def indexar(id_crudo: int) -> dict[str, Any]:
    """Pide a storage-service (único escritor de Chroma) reingerir el instrumento al RAG."""
    # Vectorizar cientos de respondentes en CPU tarda minutos (corre en segundo plano).
    largo = httpx.Timeout(connect=5.0, read=1800.0, write=60.0, pool=5.0)
    return _pedir("POST", f"/almacenamiento/indice/instrumentos/{id_crudo}", json={"reindexar": True}, timeout=largo).json()
