"""Detección e identificación del tipo de archivo del instrumento.

Responsabilidad única: dado un archivo subido, decir
  - qué extensión/formato tiene,
  - a qué familia de parser pertenece (tabular vs. documento),
  - qué MIME le corresponde,
  - si es coherente (extensión vs. contenido real) y si es válido para el
    tipo de instrumento declarado.

NO parsea el contenido: solo lo identifica y lo enruta. El parsing real (lectura
tabular o documental) es una etapa posterior del pipeline, en otro servicio, y
queda fuera del alcance de la carga. Este servicio no depende de ella.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from app.config.constants import (
    EXTENSION_TO_MIME,
    EXTENSIONES_ACEPTADAS,
    FAMILIA_POR_TIPO,
    FORMATOS_POR_TIPO,
    ParserFamily,
    TipoInstrumento,
)


class FileTypeError(ValueError):
    """El archivo no se puede identificar o no es válido para el tipo dado."""


@dataclass(frozen=True)
class FileType:
    """Resultado de la identificación de un archivo.

    Attributes:
        filename:       Nombre original (saneado del path) del archivo.
        extension:      Extensión en minúsculas, con punto (p. ej. ".csv").
        mime_type:      MIME canónico derivado de la extensión.
        parser_family:  Familia de parser a la que se enruta el archivo.
    """

    filename: str
    extension: str
    mime_type: str
    parser_family: ParserFamily


# ── Firmas (magic numbers) para validar coherencia extensión/contenido ───────
# Solo validamos formatos binarios con firma estable. CSV/TXT son texto plano y
# no tienen firma fiable, así que se aceptan por extensión.
#   - ZIP based (xlsx, docx): "PK\x03\x04"
#   - XLS (OLE2 compound): "\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
#   - PDF: "%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"
_OLE2_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
_PDF_MAGIC = b"%PDF-"

# Extensiones basadas en contenedor ZIP (OOXML).
_ZIP_BASED_EXTENSIONS = frozenset({".xlsx", ".docx"})


def _normalize_extension(filename: str) -> str:
    """Devuelve la extensión en minúsculas (con punto) del nombre dado."""
    # PurePosixPath evita sorpresas con separadores; el nombre ya viene saneado.
    suffix = PurePosixPath(filename).suffix.lower()
    return suffix


def _validate_magic_bytes(extension: str, head: bytes) -> None:
    """Valida que el inicio del archivo sea coherente con su extensión.

    Lanza FileTypeError si hay una incoherencia clara (p. ej. un .pdf que no
    empieza por %PDF-). Para texto plano (.csv/.txt) no hay validación de firma.
    """
    if not head:
        raise FileTypeError("El archivo está vacío.")

    if extension in _ZIP_BASED_EXTENSIONS:
        if not head.startswith(_ZIP_MAGIC):
            raise FileTypeError(
                f"El contenido no corresponde a un archivo {extension} válido "
                f"(se esperaba un contenedor OOXML/ZIP)."
            )
    elif extension == ".xls":
        if not head.startswith(_OLE2_MAGIC):
            raise FileTypeError(
                "El contenido no corresponde a un archivo .xls válido "
                "(se esperaba un documento OLE2)."
            )
    elif extension == ".pdf":
        if not head.startswith(_PDF_MAGIC):
            raise FileTypeError(
                "El contenido no corresponde a un archivo .pdf válido "
                "(se esperaba la firma %PDF-)."
            )
    # .csv y .txt: texto plano, sin firma binaria fiable → se aceptan.


def identify(filename: str, head: bytes | None = None) -> FileType:
    """Identifica un archivo por su nombre (extensión) y, si se provee, su cabecera.

    Args:
        filename: Nombre del archivo (p. ej. "respuestas.xlsx").
        head:     Primeros bytes del archivo para validar coherencia (opcional
                  pero recomendado). Con ~8 bytes basta para las firmas usadas.

    Returns:
        FileType con extensión, MIME y familia de parser.

    Raises:
        FileTypeError: si no hay extensión, la extensión no está soportada o el
                       contenido es incoherente con la extensión.
    """
    if not filename or not filename.strip():
        raise FileTypeError("El archivo no tiene nombre.")

    extension = _normalize_extension(filename)
    if not extension:
        raise FileTypeError(
            f"El archivo '{filename}' no tiene extensión; no se puede identificar su tipo."
        )

    if extension not in EXTENSIONES_ACEPTADAS:
        aceptadas = ", ".join(sorted(EXTENSIONES_ACEPTADAS))
        raise FileTypeError(
            f"Formato '{extension}' no soportado. Formatos aceptados: {aceptadas}."
        )

    if head is not None:
        _validate_magic_bytes(extension, head)

    family = (
        ParserFamily.TABULAR
        if extension in {".csv", ".xlsx", ".xls"}
        else ParserFamily.DOCUMENTO
    )

    return FileType(
        filename=filename,
        extension=extension,
        mime_type=EXTENSION_TO_MIME[extension],
        parser_family=family,
    )


def validate_for_instrument(
    file_type: FileType, tipo_instrumento: TipoInstrumento
) -> None:
    """Valida que el archivo RESPONDIDO sea del formato esperado para el tipo.

    - encuesta             → tabular (.csv, .xlsx, .xls)
    - entrevista / prueba  → documento (.pdf, .txt, .docx)

    Raises:
        FileTypeError: si la extensión no es válida para ese tipo de instrumento.
    """
    permitidas = FORMATOS_POR_TIPO[tipo_instrumento]
    if file_type.extension not in permitidas:
        esperadas = ", ".join(sorted(permitidas))
        raise FileTypeError(
            f"El tipo de instrumento '{tipo_instrumento.value}' no acepta archivos "
            f"'{file_type.extension}'. Formatos válidos: {esperadas}."
        )

    esperada = FAMILIA_POR_TIPO[tipo_instrumento]
    if file_type.parser_family is not esperada:
        raise FileTypeError(
            f"El archivo se enruta al parser '{file_type.parser_family.value}' "
            f"pero '{tipo_instrumento.value}' requiere '{esperada.value}'."
        )
