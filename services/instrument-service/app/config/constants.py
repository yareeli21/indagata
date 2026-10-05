"""Constantes del módulo de carga.

Vocabularios cerrados de tipos de instrumento y formatos aceptados por tipo.
Son la fuente única de verdad para la validación de archivos en el upload.
"""
from __future__ import annotations

from enum import Enum


class TipoInstrumento(str, Enum):
    """Tipos de instrumento soportados.

    Alineado con `raw_data.tipo_instrumento` (VARCHAR) y con el vocabulario que
    consume el Survey Intelligence Service (encuesta | entrevista | prueba).
    """

    ENCUESTA = "encuesta"
    ENTREVISTA = "entrevista"
    PRUEBA_ESTANDARIZADA = "prueba_estandarizada"


class ParserFamily(str, Enum):
    """Familia de parser a la que se enruta un archivo según su formato.

    - TABULAR:   datos en filas/columnas (.csv, .xlsx, .xls). Vía encuesta.
    - DOCUMENTO: texto narrativo (.pdf, .txt, .docx). Vía entrevista/prueba.
    """

    TABULAR = "tabular"
    DOCUMENTO = "documento"


# ── Extensiones aceptadas por familia de parser ──────────────────────────────
# En minúsculas y con el punto incluido.
TABULAR_EXTENSIONS: frozenset[str] = frozenset({".csv", ".xlsx", ".xls"})
DOCUMENTO_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".txt", ".docx"})


# ── Formatos aceptados por tipo de instrumento ───────────────────────────────
# El archivo RESPONDIDO (raw_archivo) debe pertenecer a la familia esperada por
# el tipo de instrumento. El archivo ORIGINAL (raw_archivo_original) es, por su
# naturaleza (el instrumento sin respuestas), siempre un DOCUMENTO.
FORMATOS_POR_TIPO: dict[TipoInstrumento, frozenset[str]] = {
    TipoInstrumento.ENCUESTA: TABULAR_EXTENSIONS,
    TipoInstrumento.ENTREVISTA: DOCUMENTO_EXTENSIONS,
    TipoInstrumento.PRUEBA_ESTANDARIZADA: DOCUMENTO_EXTENSIONS,
}

# Familia de parser esperada para el archivo RESPONDIDO de cada tipo.
FAMILIA_POR_TIPO: dict[TipoInstrumento, ParserFamily] = {
    TipoInstrumento.ENCUESTA: ParserFamily.TABULAR,
    TipoInstrumento.ENTREVISTA: ParserFamily.DOCUMENTO,
    TipoInstrumento.PRUEBA_ESTANDARIZADA: ParserFamily.DOCUMENTO,
}


# ── Mapeo extensión -> MIME canónico ─────────────────────────────────────────
# Se usa para enriquecer la respuesta y validar coherencia extensión/contenido.
EXTENSION_TO_MIME: dict[str, str] = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Todas las extensiones aceptadas por el servicio (unión de las anteriores).
EXTENSIONES_ACEPTADAS: frozenset[str] = TABULAR_EXTENSIONS | DOCUMENTO_EXTENSIONS

# Límite de tamaño por archivo (bytes). 100 MB por defecto.
MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024
