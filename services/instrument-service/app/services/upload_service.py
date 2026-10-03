"""Servicio de carga (upload) de instrumentos.

Orquesta el Paso 1 del pipeline:

  1. Valida el tipo de instrumento declarado.
  2. Identifica el tipo de cada archivo (respondido y, opcional, original) y lo
     enruta a su familia de parser.
  3. Valida que el archivo RESPONDIDO sea coherente con el tipo de instrumento.
  4. Almacena ambos archivos en RAW DATA (storage/raw).
  5. Registra el instrumento en `raw_data` (padre) y crea su
     `instrumento_procesado` en estado 'recibido'.

Transaccional: si la persistencia en BD falla, se borran los archivos ya
escritos en disco para no dejar huérfanos.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.constants import MAX_FILE_SIZE_BYTES, TipoInstrumento
from app.core import file_type_detector as detector
from app.core import raw_storage
from app.core.file_type_detector import FileType, FileTypeError
from app.core.raw_storage import StoredFile
from app.parsing import ParsedContent, ParseError, parse_file
from app.schemas.upload import ArchivoRegistrado, ParseoArchivo, UploadResponse
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData

logger = logging.getLogger(__name__)

# Bytes de cabecera que se leen para validar la firma del archivo.
_MAGIC_HEAD_BYTES = 8


def _parse_tipo(tipo_instrumento: str) -> TipoInstrumento:
    """Convierte el string del form al enum, o lanza 422."""
    try:
        return TipoInstrumento(tipo_instrumento.strip().lower())
    except ValueError:
        validos = ", ".join(t.value for t in TipoInstrumento)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo_instrumento inválido. Valores aceptados: {validos}.",
        )


async def _read_and_identify(
    archivo: UploadFile, *, rol: str
) -> tuple[bytes, FileType]:
    """Lee los bytes de un UploadFile y los identifica.

    Args:
        archivo: El UploadFile de FastAPI.
        rol:     Etiqueta para los mensajes de error ("respondido"/"original").

    Returns:
        (content, FileType)

    Raises:
        HTTPException 400/413/422 ante archivos vacíos, grandes o no soportados.
    """
    filename = archivo.filename or ""
    content = await archivo.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo {rol} '{filename}' está vacío.",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        limite_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo {rol} '{filename}' supera el límite de {limite_mb} MB.",
        )

    try:
        file_type = detector.identify(filename, head=content[:_MAGIC_HEAD_BYTES])
    except FileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Archivo {rol}: {exc}",
        )

    return content, file_type


def _to_parseo(parsed: ParsedContent | None) -> ParseoArchivo | None:
    """Convierte el ParsedContent del parser al DTO de respuesta."""
    if parsed is None:
        return None
    return ParseoArchivo(
        parser_family=parsed.parser_family,
        headers=parsed.headers,
        n_columns=parsed.n_columns,
        n_rows=parsed.n_rows,
        preview_rows=parsed.preview_rows,
        sheet=parsed.sheet,
        n_chars=parsed.n_chars,
        n_words=parsed.n_words,
        n_pages=parsed.n_pages,
        text_preview=parsed.text_preview,
        encoding=parsed.encoding,
        notes=parsed.notes,
    )


def _to_archivo_registrado(
    stored: StoredFile, file_type: FileType, parsed: ParsedContent | None = None
) -> ArchivoRegistrado:
    """Construye el DTO de un archivo almacenado."""
    return ArchivoRegistrado(
        nombre_original=stored.original_name,
        ruta_relativa=stored.relative_path,
        extension=file_type.extension,
        mime_type=file_type.mime_type,
        parser_family=file_type.parser_family,
        size_bytes=stored.size_bytes,
        parseo=_to_parseo(parsed),
    )


class UploadService:
    """Caso de uso: subir un instrumento (archivo respondido + opcional original)."""

    @staticmethod
    async def upload(
        db: Session,
        usuario_id: int,
        tipo_instrumento_raw: str,
        archivo: UploadFile,
        archivo_original: UploadFile | None = None,
    ) -> UploadResponse:
        """Ejecuta el flujo completo de carga.

        Args:
            db:                   Sesión de BD.
            usuario_id:           Propietario (id_owner) del instrumento.
            tipo_instrumento_raw: "encuesta" | "entrevista" | "prueba_estandarizada".
            archivo:              Archivo RESPONDIDO (raw_archivo), obligatorio.
            archivo_original:     Instrumento ORIGINAL sin respuestas, opcional.

        Returns:
            UploadResponse con id_crudo, id_instrumento y el resumen de archivos.
        """
        tipo = _parse_tipo(tipo_instrumento_raw)

        # ── 1. Leer e identificar el archivo RESPONDIDO ──────────────────────
        content, file_type = await _read_and_identify(archivo, rol="respondido")

        # El archivo respondido debe ser coherente con el tipo de instrumento.
        try:
            detector.validate_for_instrument(file_type, tipo)
        except FileTypeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        # ── 2. PARSEAR el archivo respondido ─────────────────────────────────
        # Se lee el contenido real para saber con qué estructura se va a trabajar
        # (columnas de la encuesta tabular, o texto del documento). Es obligatorio:
        # si no se puede parsear, el archivo no sirve como instrumento → 422.
        try:
            parsed_resp = parse_file(content, file_type.extension, file_type.parser_family)
        except ParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No se pudo parsear el archivo respondido: {exc}",
            )

        # ── 3. Leer, identificar y parsear el archivo ORIGINAL (opcional) ────
        original_content: bytes | None = None
        original_type: FileType | None = None
        parsed_orig: ParsedContent | None = None
        if archivo_original is not None and (archivo_original.filename or "").strip():
            original_content, original_type = await _read_and_identify(
                archivo_original, rol="original"
            )
            # El original es best-effort: su parseo no debe bloquear la carga.
            try:
                parsed_orig = parse_file(
                    original_content, original_type.extension, original_type.parser_family
                )
            except ParseError as exc:
                logger.warning("No se pudo parsear el archivo original: %s", exc)

        # ── 4. Persistir en disco (RAW DATA) ─────────────────────────────────
        stored_resp: StoredFile | None = None
        stored_orig: StoredFile | None = None
        try:
            stored_resp = raw_storage.save(content, file_type.filename)
            if original_content is not None and original_type is not None:
                stored_orig = raw_storage.save(original_content, original_type.filename)

            # ── 5. Persistir en BD: raw_data (padre) ─────────────────────────
            raw = RawData(
                id_owner=usuario_id,
                tipo_instrumento=tipo.value,
                nombre_archivo=file_type.filename,
                raw_archivo=stored_resp.relative_path,
                raw_archivo_original=(
                    stored_orig.relative_path if stored_orig is not None else None
                ),
            )
            db.add(raw)
            db.flush()  # obtiene raw.id_crudo sin cerrar la transacción

            # ── 6. Persistir instrumento_procesado (hija), estado 'recibido' ─
            procesado = InstrumentoProcesado(
                id_crudo=raw.id_crudo,
                estado="recibido",
            )
            db.add(procesado)
            db.commit()
            db.refresh(raw)
            db.refresh(procesado)
        except SQLAlchemyError as exc:
            db.rollback()
            # Limpieza de archivos ya escritos para no dejar huérfanos.
            if stored_resp is not None:
                raw_storage.delete(stored_resp.relative_path)
            if stored_orig is not None:
                raw_storage.delete(stored_orig.relative_path)
            logger.exception("Error al registrar el instrumento en la base de datos.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo registrar el instrumento. Intenta de nuevo.",
            ) from exc
        except OSError as exc:
            db.rollback()
            if stored_resp is not None:
                raw_storage.delete(stored_resp.relative_path)
            if stored_orig is not None:
                raw_storage.delete(stored_orig.relative_path)
            logger.exception("Error de almacenamiento al guardar los archivos crudos.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudieron almacenar los archivos del instrumento.",
            ) from exc

        # ── 7. Construir la respuesta ────────────────────────────────────────
        return UploadResponse(
            id_crudo=raw.id_crudo,
            id_instrumento=procesado.id_instrumento,
            id_owner=raw.id_owner,
            tipo_instrumento=tipo,
            estado=procesado.estado,
            fecha_carga=raw.fecha_carga,
            archivo_respondido=_to_archivo_registrado(stored_resp, file_type, parsed_resp),
            archivo_original=(
                _to_archivo_registrado(stored_orig, original_type, parsed_orig)
                if stored_orig is not None and original_type is not None
                else None
            ),
        )
