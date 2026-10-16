"""Casos de uso del documento final: generarlo (borrador), leerlo y publicarlo (vigente).

El archivo vive en storage-service (artefacto JSON tipo `documento`, versionado y con
SHA-256); su registro, en la MISMA fila de `version_conocimiento` del perfil:
`ruta_documento`, `esquema_version`, `avisos`, `sha256` y las fechas.

    perfil_aprobado / kpis_confirmados ──generar──▶ borrador ──publicar──▶ vigente
    (al publicar, la versión vigente anterior pasa a `reemplazado`)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

from services import documento, fuentes, storage_client, versiones

logger = logging.getLogger("knowledge-service")

_GENERABLE = ("perfil_aprobado", "kpis_confirmados", "borrador")
_MUESTRA = 3


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _error_storage(exc: storage_client.StorageError) -> HTTPException:
    if exc.status_code is None:
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo guardar o leer el documento final: {exc}")


def _fila_actual(db: Session, id_crudo: int) -> VersionConocimiento:
    fila = versiones.actual(db, id_crudo)
    if fila is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento aún no tiene perfil semántico: aprueba sus metadatos.")
    return fila


def generar(db: Session, usuario: Usuario, id_crudo: int) -> tuple[VersionConocimiento, dict[str, Any]]:
    """Construye, valida y guarda el documento final de la versión actual (queda en borrador)."""
    ctx = fuentes.cargar(db, usuario, id_crudo)
    fila = _fila_actual(db, id_crudo)
    if fila.estado not in _GENERABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta versión ya está publicada; para cambiarla vuelve a aprobar los metadatos.")
    est = fuentes.estructura_de(ctx)
    reporte = (ctx.limpieza.reporte or {}) if ctx.limpieza else {}
    filas = fuentes.filas_limpias(ctx)
    try:
        doc = documento.construir(fila.perfil, est, reporte, filas, est.avisos)
    except documento.DocumentoInvalido as exc:
        logger.exception("Documento final inválido para id_crudo=%s", id_crudo)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"El documento final generado no es válido: {exc}") from exc
    try:
        ref = storage_client.guardar_json(id_crudo, "documento", doc, f"v{fila.version}_documento_final")
    except storage_client.StorageError as exc:
        raise _error_storage(exc) from exc

    fila.ruta_documento = ref["key"]
    fila.esquema_version = doc["esquema_version"]
    fila.sha256 = ref.get("sha256")
    # Se conservan los avisos del perfil y se reemplazan los del documento anterior.
    fila.avisos = [a for a in (fila.avisos or []) if a.get("origen") == "perfil"] + [dict(a, origen="documento") for a in doc["avisos"]]
    fila.estado = "borrador"
    fila.fecha_documento = _ahora()
    db.commit()
    db.refresh(fila)
    return fila, doc


def leer(db: Session, usuario: Usuario, id_crudo: int) -> tuple[VersionConocimiento, dict[str, Any]]:
    """Documento final de la versión actual (el último generado)."""
    fuentes.cargar(db, usuario, id_crudo)  # autoría
    fila = _fila_actual(db, id_crudo)
    if not fila.ruta_documento:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La versión actual aún no tiene documento final.")
    try:
        return fila, storage_client.descargar_json(fila.ruta_documento)
    except storage_client.StorageError as exc:
        raise _error_storage(exc) from exc


def publicar(db: Session, usuario: Usuario, id_crudo: int, version: int) -> VersionConocimiento:
    """Marca el documento como vigente; la versión vigente anterior pasa a reemplazado."""
    fuentes.cargar(db, usuario, id_crudo)
    fila = (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.version == version)
        .one_or_none()
    )
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la versión {version} del conocimiento.")
    if fila.estado == "vigente":
        return fila
    if fila.estado != "borrador" or not fila.ruta_documento:
        raise HTTPException(status.HTTP_409_CONFLICT, "Primero genera el documento final de esta versión.")
    (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.estado == "vigente")
        .update({"estado": "reemplazado"}, synchronize_session=False)
    )
    fila.estado = "vigente"
    fila.fecha_publicacion = _ahora()
    db.commit()
    db.refresh(fila)
    return fila


def vista(doc: dict[str, Any]) -> dict[str, Any]:
    """Versión ligera para la interfaz: todo menos las respuestas individuales (con una muestra)."""
    salida = {k: v for k, v in doc.items() if k not in ("respondentes", "alumnos", "entrevistas")}
    for clave in ("respondentes", "alumnos", "entrevistas"):
        if clave in doc:
            salida["n_" + clave] = len(doc[clave])
            salida["muestra_" + clave] = doc[clave][:_MUESTRA]
    return salida
