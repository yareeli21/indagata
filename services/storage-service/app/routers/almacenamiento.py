"""Router — almacenamiento de artefactos (autoridad de archivos/JSON).

Prefijo: /almacenamiento. Ver design.md §3.3–§3.6.

El servicio decide dónde guardar cada artefacto (ruteo por tipo), lo persiste
con una clave versionada estable y devuelve dónde quedó guardado
(ruta absoluta + relativa + key).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from shared.db.core.config import settings

from app.core import index, store
from app.schemas.almacenamiento import (
    ArtefactoDetalle,
    ArtefactoRef,
    GuardarJsonRequest,
)

logger = logging.getLogger("storage-service")

router = APIRouter(prefix="/almacenamiento", tags=["almacenamiento"])

# Límite blando para binarios (50 MB).
_MAX_BYTES = 50 * 1024 * 1024


def _ruta_relativa(ruta_abs: Path) -> str:
    """Ruta relativa a la raíz de storage (settings.raw_path_abs.parent)."""
    root = settings.raw_path_abs.parent
    try:
        return str(ruta_abs.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(ruta_abs)


def _construir_key(tipo: str, instrumento_id: str, version: int, slug: str) -> str:
    return f"{tipo}/{instrumento_id}/{version}__{slug}"


def _persistir(
    *,
    tipo: str,
    instrumento_id: str,
    slug: str,
    nombre_original: str,
    escribir,
) -> ArtefactoRef:
    """Resuelve versión, key y ruta; escribe de forma atómica y registra en el índice.

    `escribir(destino: Path) -> int` realiza la escritura y devuelve size_bytes.
    """
    with index._lock:
        try:
            version = index.proxima_version(tipo, instrumento_id)
        except index.IndexError_ as exc:
            logger.error("Índice corrupto al calcular versión: %s", exc)
            raise HTTPException(status_code=500, detail="Índice de artefactos corrupto.")

        key = _construir_key(tipo, instrumento_id, version, slug)
        try:
            destino = store.ruta_de_key(tipo, key)
        except store.RutaInseguraError as exc:
            logger.error("Ruta insegura rechazada: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc))

        try:
            size_bytes = escribir(destino)
        except store.StoreError as exc:
            logger.error("Fallo al almacenar artefacto: %s", exc)
            raise HTTPException(status_code=500, detail="No se pudo almacenar el artefacto.")

        creado = datetime.now(timezone.utc)
        entrada = {
            "key": key,
            "tipo": tipo,
            "instrumentoId": instrumento_id,
            "version": version,
            "ruta_absoluta": str(destino),
            "ruta_relativa": _ruta_relativa(destino),
            "size_bytes": size_bytes,
            "nombre_original": nombre_original,
            "creado": creado.isoformat(),
        }
        try:
            index.registrar(entrada)
        except index.IndexError_ as exc:
            logger.error("Índice corrupto al registrar: %s", exc)
            raise HTTPException(status_code=500, detail="Índice de artefactos corrupto.")

    return ArtefactoRef(
        key=key,
        tipo=tipo,
        instrumentoId=instrumento_id,
        version=version,
        ruta_absoluta=str(destino),
        ruta_relativa=_ruta_relativa(destino),
        size_bytes=size_bytes,
        nombre_original=nombre_original,
        creado=creado,
    )


@router.post("/json", response_model=ArtefactoRef, summary="Guardar un JSON (metadata o analysis)")
async def guardar_json(payload: GuardarJsonRequest) -> ArtefactoRef:
    if not payload.instrumentoId or not payload.instrumentoId.strip():
        raise HTTPException(status_code=422, detail="El instrumentoId es obligatorio.")
    if not isinstance(payload.contenido, dict) or not payload.contenido:
        raise HTTPException(
            status_code=422, detail="El contenido debe ser un objeto JSON no vacío."
        )

    nombre_original = payload.nombre or "instrumento.json"
    base_slug = index.slug(payload.nombre or "instrumento")
    slug = base_slug if base_slug.lower().endswith(".json") else f"{base_slug}.json"

    return _persistir(
        tipo=payload.tipo,
        instrumento_id=payload.instrumentoId,
        slug=slug,
        nombre_original=nombre_original,
        escribir=lambda destino: store.guardar_json(destino, payload.contenido),
    )


@router.post("/archivo", response_model=ArtefactoRef, summary="Guardar un binario (raw/sav/temp)")
async def guardar_archivo(
    archivo: UploadFile = File(..., description="Archivo binario a almacenar."),
    tipo: str = Form(..., description="raw | sav | temp"),
    instrumentoId: str | None = Form(default=None),
) -> ArtefactoRef:
    if tipo not in store.TIPOS_VALIDOS:
        raise HTTPException(
            status_code=422, detail=f"Tipo de artefacto no soportado: {tipo}"
        )

    contenido = await archivo.read()
    if len(contenido) > _MAX_BYTES:
        raise HTTPException(
            status_code=413, detail="El archivo excede el tamaño permitido (50 MB)."
        )

    instrumento_id = instrumentoId if (instrumentoId and instrumentoId.strip()) else "_"
    nombre_original = archivo.filename or "archivo"
    slug = index.slug(nombre_original)

    return _persistir(
        tipo=tipo,
        instrumento_id=instrumento_id,
        slug=slug,
        nombre_original=nombre_original,
        escribir=lambda destino: (store.guardar_bytes(destino, contenido) or len(contenido)),
    )


@router.get(
    "/artefacto/{tipo}/{instrumentoId}",
    response_model=ArtefactoDetalle,
    summary="Recuperar un artefacto por clave",
)
async def obtener_artefacto(
    tipo: str, instrumentoId: str, version: int | None = None
) -> ArtefactoDetalle:
    if tipo not in store.TIPOS_VALIDOS:
        raise HTTPException(
            status_code=422, detail=f"Tipo de artefacto no soportado: {tipo}"
        )

    try:
        entrada = index.buscar(tipo, instrumentoId, version)
    except index.IndexError_ as exc:
        logger.error("Índice corrupto al buscar: %s", exc)
        raise HTTPException(status_code=500, detail="Índice de artefactos corrupto.")

    if entrada is None:
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")

    contenido = None
    if tipo in ("metadata", "analysis"):
        ruta = Path(entrada["ruta_absoluta"])
        if not ruta.exists():
            raise HTTPException(status_code=404, detail="Artefacto no encontrado.")
        try:
            contenido = store.leer_json(ruta)
        except store.StoreError as exc:
            logger.error("JSON almacenado inválido: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="El artefacto almacenado no es un JSON válido.",
            )

    return ArtefactoDetalle(**_entrada_a_ref(entrada), contenido=contenido)


@router.get(
    "/artefactos",
    response_model=list[ArtefactoRef],
    summary="Listar/filtrar artefactos",
)
async def listar_artefactos(
    instrumentoId: str | None = None, tipo: str | None = None
) -> list[ArtefactoRef]:
    if tipo is not None and tipo not in store.TIPOS_VALIDOS:
        raise HTTPException(
            status_code=422, detail=f"Tipo de artefacto no soportado: {tipo}"
        )
    try:
        entradas = index.listar(instrumento_id=instrumentoId, tipo=tipo)
    except index.IndexError_ as exc:
        logger.error("Índice corrupto al listar: %s", exc)
        raise HTTPException(status_code=500, detail="Índice de artefactos corrupto.")
    return [ArtefactoRef(**_entrada_a_ref(e)) for e in entradas]


def _entrada_a_ref(entrada: dict) -> dict:
    """Normaliza una entrada del manifiesto a los campos de ArtefactoRef."""
    return {
        "key": entrada["key"],
        "tipo": entrada["tipo"],
        "instrumentoId": entrada.get("instrumentoId"),
        "version": entrada["version"],
        "ruta_absoluta": entrada["ruta_absoluta"],
        "ruta_relativa": entrada["ruta_relativa"],
        "size_bytes": entrada["size_bytes"],
        "nombre_original": entrada["nombre_original"],
        "creado": entrada["creado"],
    }
