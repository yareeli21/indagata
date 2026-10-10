"""Router — archivos (subida, descarga, lectura y borrado).

Prefijo /almacenamiento. Todos los endpoints son internos (token de servicio o
administrador, ver dependencies.py).

  POST   /almacenamiento/json                  guardar un JSON (metadata | analysis)
  POST   /almacenamiento/archivo               guardar un binario (raw | clean | sav | temp)
  GET    /almacenamiento/artefacto/{tipo}/{id} recuperar un artefacto (+ contenido si es JSON)
  GET    /almacenamiento/artefactos            listar/filtrar artefactos
  GET    /almacenamiento/descarga?ruta=        bytes del archivo (con SHA-256 en cabecera)
  GET    /almacenamiento/tabla?ruta=           contenido tabular (CSV/XLSX/JSON v1)
  GET    /almacenamiento/texto?ruta=           texto plano (PDF/DOCX/TXT/MD/JSON)
  DELETE /almacenamiento/archivo?ruta=         eliminar un archivo
  DELETE /almacenamiento/instrumentos/{id}     purgar archivos + vectores de un instrumento
  GET    /almacenamiento/estadisticas          uso del almacenamiento y de la caché
  POST   /almacenamiento/mantenimiento/limpiar-temporales
"""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status

from dependencies import DBSession, Interno
from models import (
    ArtefactoDetalle,
    ArtefactoRef,
    EliminarResultado,
    EstadisticasAlmacenamiento,
    GuardarJsonRequest,
    LimpiezaTemporales,
    PurgaResultado,
    TablaResponse,
    TextoResponse,
    TIPOS_BINARIOS,
    TIPOS_JSON,
)
from services import cache_manager, chroma_indexer, file_manager, lectura
from services.cache_manager import cache

logger = logging.getLogger("storage-service")

router = APIRouter(prefix="/almacenamiento", tags=["archivos"])

# Igual que el límite del instrument-service (100 MB por archivo).
_MAX_BYTES = 100 * 1024 * 1024
# Máximo de filas que se devuelven en /tabla (las demás se cuentan en n_filas).
_MAX_FILAS_DEFECTO = 20000


def _a_http(exc: Exception) -> HTTPException:
    """Traduce los errores del gestor de archivos a respuestas HTTP."""
    if isinstance(exc, file_manager.NoEncontradoError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, file_manager.RutaInseguraError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if isinstance(exc, file_manager.TipoInvalidoError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, lectura.LecturaError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    logger.error("Fallo de almacenamiento: %s", exc)
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc) or "Error de almacenamiento.")


_ERRORES = (
    file_manager.NoEncontradoError,
    file_manager.RutaInseguraError,
    file_manager.TipoInvalidoError,
    file_manager.AlmacenamientoError,
    file_manager.IndiceCorruptoError,
    lectura.LecturaError,
)


def _content_disposition(nombre: str) -> str:
    ascii_ = nombre.encode("ascii", "ignore").decode("ascii").replace('"', "") or "archivo"
    return f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"


@router.post("/json", response_model=ArtefactoRef, summary="Guardar un JSON (metadata o analysis)")
def guardar_json(payload: GuardarJsonRequest, _: Interno) -> ArtefactoRef:
    if not payload.instrumentoId.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El instrumentoId es obligatorio.")
    if not payload.contenido:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El contenido debe ser un objeto JSON no vacío.")
    try:
        entrada = file_manager.guardar_json(
            payload.tipo, payload.instrumentoId.strip(), payload.contenido, payload.nombre
        )
    except _ERRORES as exc:
        raise _a_http(exc)
    return ArtefactoRef(**entrada)


@router.post("/archivo", response_model=ArtefactoRef, summary="Guardar un binario (raw/clean/sav/temp)")
async def guardar_archivo(
    _: Interno,
    archivo: UploadFile = File(..., description="Archivo a almacenar (se guarda sin cambios)."),
    tipo: str = Form(..., description="raw | clean | sav | temp"),
    instrumentoId: str | None = Form(default=None),
) -> ArtefactoRef:
    if tipo not in TIPOS_BINARIOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Tipo de artefacto no soportado: {tipo}")
    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo está vacío.")
    if len(contenido) > _MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "El archivo excede el tamaño permitido (100 MB).")
    try:
        entrada = file_manager.guardar(tipo, instrumentoId, archivo.filename or "archivo", contenido)
    except _ERRORES as exc:
        raise _a_http(exc)
    return ArtefactoRef(**entrada)


@router.get(
    "/artefacto/{tipo}/{instrumentoId}",
    response_model=ArtefactoDetalle,
    summary="Recuperar un artefacto (la última versión si no se indica)",
)
def obtener_artefacto(tipo: str, instrumentoId: str, _: Interno, version: int | None = None) -> ArtefactoDetalle:
    if tipo not in file_manager.TIPOS_VALIDOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Tipo de artefacto no soportado: {tipo}")
    try:
        entrada = file_manager.obtener(tipo, instrumentoId, version)
        if entrada is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Artefacto no encontrado.")
        contenido = file_manager.leer_json(entrada) if tipo in TIPOS_JSON else None
    except _ERRORES as exc:
        raise _a_http(exc)
    return ArtefactoDetalle(**entrada, contenido=contenido)


@router.get("/artefactos", response_model=list[ArtefactoRef], summary="Listar/filtrar artefactos")
def listar_artefactos(_: Interno, instrumentoId: str | None = None, tipo: str | None = None) -> list[ArtefactoRef]:
    if tipo is not None and tipo not in file_manager.TIPOS_VALIDOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Tipo de artefacto no soportado: {tipo}")
    try:
        entradas = file_manager.listar(instrumento_id=instrumentoId, tipo=tipo)
    except _ERRORES as exc:
        raise _a_http(exc)
    return [ArtefactoRef(**e) for e in entradas]


@router.get("/descarga", summary="Descargar un archivo almacenado (bytes intactos)")
def descargar(_: Interno, ruta: str = Query(..., description="Clave del artefacto o ruta guardada en la BD.")) -> Response:
    try:
        archivo = file_manager.leer(ruta)
    except _ERRORES as exc:
        raise _a_http(exc)
    esperado = (archivo.entrada or {}).get("sha256")
    if esperado and esperado != archivo.sha256:
        logger.error("Integridad comprometida en %s: %s != %s", ruta, archivo.sha256, esperado)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "El archivo almacenado no coincide con su huella original.")
    return Response(
        content=archivo.contenido,
        media_type=archivo.mime_type,
        headers={
            "Content-Disposition": _content_disposition(archivo.nombre),
            "X-Checksum-SHA256": archivo.sha256,
            "X-Nombre-Archivo": quote(archivo.nombre),
        },
    )


@router.get("/tabla", response_model=TablaResponse, summary="Contenido tabular de un archivo")
def leer_tabla(
    _: Interno,
    ruta: str = Query(...),
    max_filas: int = Query(_MAX_FILAS_DEFECTO, ge=0, le=200000),
) -> TablaResponse:
    try:
        archivo = file_manager.leer(ruta)
        clave = f"tabla:{archivo.sha256}"
        tabla = cache.get(clave)
        if tabla is None:
            tabla = lectura.leer_tabla(archivo.contenido, Path(archivo.nombre).suffix or archivo.path.suffix)
            cache.set(clave, tabla)
    except _ERRORES as exc:
        raise _a_http(exc)
    return TablaResponse(
        headers=tabla.headers,
        rows=tabla.rows[:max_filas],
        n_filas=len(tabla.rows),
        n_columnas=len(tabla.headers),
        hoja=tabla.hoja,
        encoding=tabla.encoding,
        notas=tabla.notas,
        truncado=len(tabla.rows) > max_filas,
    )


@router.get("/texto", response_model=TextoResponse, summary="Texto plano de un archivo")
def leer_texto(_: Interno, ruta: str = Query(...)) -> TextoResponse:
    try:
        archivo = file_manager.leer(ruta)
        clave = f"texto:{archivo.sha256}"
        documento = cache.get(clave)
        if documento is None:
            documento = lectura.extraer_texto(archivo.contenido, Path(archivo.nombre).suffix or archivo.path.suffix)
            cache.set(clave, documento)
    except _ERRORES as exc:
        raise _a_http(exc)
    return TextoResponse(
        texto=documento.texto,
        n_caracteres=len(documento.texto),
        n_paginas=documento.n_paginas,
        notas=documento.notas,
    )


@router.delete("/archivo", response_model=EliminarResultado, summary="Eliminar un archivo")
def eliminar_archivo(_: Interno, ruta: str = Query(...)) -> EliminarResultado:
    try:
        eliminado = file_manager.eliminar(ruta)
    except _ERRORES as exc:
        raise _a_http(exc)
    return EliminarResultado(ruta=ruta, eliminado=eliminado)


@router.delete(
    "/instrumentos/{instrumentoId}",
    response_model=PurgaResultado,
    summary="Purgar todos los archivos y vectores de un instrumento",
)
def purgar_instrumento(instrumentoId: str, _: Interno, db: DBSession) -> PurgaResultado:
    try:
        artefactos = file_manager.purgar_instrumento(instrumentoId)
    except _ERRORES as exc:
        raise _a_http(exc)
    vectores = 0
    if instrumentoId.isdigit():
        try:
            vectores = chroma_indexer.desindexar_instrumento(db, int(instrumentoId))
        except chroma_indexer.IndiceError as exc:
            logger.warning("No se pudieron purgar los vectores de %s: %s", instrumentoId, exc)
    return PurgaResultado(instrumentoId=instrumentoId, artefactos_eliminados=artefactos, vectores_eliminados=vectores)


@router.get("/estadisticas", response_model=EstadisticasAlmacenamiento, summary="Uso del almacenamiento")
def estadisticas(_: Interno) -> EstadisticasAlmacenamiento:
    try:
        return EstadisticasAlmacenamiento(**file_manager.estadisticas())
    except _ERRORES as exc:
        raise _a_http(exc)


@router.post(
    "/mantenimiento/limpiar-temporales",
    response_model=LimpiezaTemporales,
    summary="Eliminar artefactos temporales antiguos",
)
def limpiar_temporales(_: Interno, max_edad_horas: float = Query(24.0, gt=0)) -> LimpiezaTemporales:
    try:
        return LimpiezaTemporales(eliminados=cache_manager.limpiar_temporales(max_edad_horas))
    except _ERRORES as exc:
        raise _a_http(exc)
