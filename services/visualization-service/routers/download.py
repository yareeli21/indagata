"""Router — descargas de instrumentos.

  GET /visualizacion/descargas/{id_crudo}?formato=crudo|json|sav&archivo=respondido|original

Regla de propiedad (la misma que muestra la UI):
  - crudo: cualquier investigador (el archivo tal cual lo subió su autor).
  - json / sav: solo el autor o un administrador.

Los bytes vienen del storage-service. El .sav sale de la última limpieza confirmada: su CSV limpio y su
reporte (texto de cada pregunta, tipo, escala con sus etiquetas y significado de los códigos), así que se puede
descargar en cuanto se confirma la limpieza. Se guarda en el storage-service con la versión de la limpieza en el
nombre: al confirmar una limpieza nueva se genera otro. Los instrumentos anteriores al paso de limpieza usan el
archivo limpio o el crudo con las reglas generales.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status

from dependencies import DBSession, Investigador, es_admin
from shared.conocimiento import significados
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.models.raw_data import RawData

from services import query_engine, sav_export, storage_client

logger = logging.getLogger("visualization-service")

_VERSION_SAV = 3  # súbela cuando cambie cómo se arma el .sav, para no servir los guardados con la versión anterior

router = APIRouter(prefix="/visualizacion", tags=["descargas"])


def _nombre_seguro(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_).strip("._") or "instrumento"


def _respuesta(contenido: bytes, nombre: str, mime: str) -> Response:
    ascii_ = nombre.encode("ascii", "ignore").decode("ascii").replace('"', "") or "archivo"
    return Response(
        content=contenido,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"},
    )


def _error_storage(exc: storage_client.StorageError) -> HTTPException:
    if exc.status_code == 404:
        return HTTPException(status.HTTP_404_NOT_FOUND, "El archivo ya no está en el almacenamiento.")
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"Almacenamiento no disponible: {exc}")


@router.get("/descargas/{id_crudo}", summary="Descargar un instrumento (crudo, JSON o .sav)")
def descargar(
    id_crudo: int,
    usuario: Investigador,
    db: DBSession,
    formato: Literal["crudo", "json", "sav"] = Query("crudo"),
    archivo: Literal["respondido", "original"] = Query("respondido"),
) -> Response:
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrumento no encontrado.")
    es_dueno = es_admin(usuario) or raw.id_owner == usuario.usuario_id
    if formato != "crudo" and not es_dueno:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes descargar el instrumento en crudo.")

    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )

    try:
        if formato == "crudo":
            ruta = raw.raw_archivo_original if archivo == "original" else raw.raw_archivo
            if not ruta:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "El instrumento no tiene archivo original.")
            descarga = storage_client.descargar(ruta)
            nombre = raw.nombre_archivo if archivo == "respondido" else descarga.nombre
            return _respuesta(descarga.contenido, nombre, descarga.mime_type)

        if formato == "json":
            data = (
                storage_client.obtener_json(id_crudo, "analysis")
                or storage_client.obtener_json(id_crudo, "metadata")
                or query_engine.leer_json(procesado.ruta_json if procesado else None)
            )
            if data is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    "El instrumento aún no tiene JSON estandarizado: aprueba primero sus metadatos.",
                )
            titulo = ((data.get("instrument") or {}).get("title")) or f"instrumento_{id_crudo}"
            contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            return _respuesta(contenido, f"{_nombre_seguro(titulo)}.json", "application/json")

        # formato == "sav"
        if (raw.tipo_instrumento or "").lower() != "encuesta":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El formato .sav solo está disponible para encuestas.")
        nombre = f"{_nombre_seguro(raw.nombre_archivo.rsplit('.', 1)[0])}.sav"
        limpieza = (
            db.query(LimpiezaEjecucion)
            .filter(LimpiezaEjecucion.id_crudo == id_crudo, LimpiezaEjecucion.estado == "confirmada")
            .order_by(LimpiezaEjecucion.version.desc())
            .first()
        )
        guardado = f"limpieza{limpieza.version if limpieza else 0}_sav{_VERSION_SAV}__{nombre}"
        existente = storage_client.ultimo_artefacto(id_crudo, "sav")
        if existente is not None and existente.get("nombre_original") == guardado:
            return _respuesta(storage_client.descargar(existente["key"]).contenido, nombre, "application/x-spss-sav")
        ruta_datos = (
            (limpieza.ruta_csv_limpio if limpieza else None)
            or (procesado.ruta_de_archivo_limpio if procesado else None)
            or raw.raw_archivo
        )
        tabla = storage_client.tabla(ruta_datos)
    except storage_client.StorageError as exc:
        raise _error_storage(exc) from exc

    reporte = limpieza.reporte if limpieza else None
    try:
        contenido = sav_export.generar_sav(
            tabla["headers"], tabla["rows"], raw.nombre_archivo,
            significados.de_reporte(reporte, "encuesta"), sav_export.columnas_de_reporte(reporte),
        )
    except ImportError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "La exportación a .sav no está instalada.") from exc
    try:
        storage_client.guardar_archivo(id_crudo, "sav", guardado, contenido)
    except storage_client.StorageError as exc:
        logger.warning("No se pudo guardar el .sav generado de %s: %s", id_crudo, exc)
    return _respuesta(contenido, nombre, "application/x-spss-sav")
