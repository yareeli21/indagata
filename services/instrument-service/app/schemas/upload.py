"""Schemas Pydantic del endpoint de carga (upload).

El DTO de salida resume lo que se registró en `raw_data` + lo que se creó en
`instrumento_procesado`, incluyendo la familia de parser detectada para cada
archivo (información útil para el frontend y para la etapa de parsing posterior).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.config.constants import ParserFamily, TipoInstrumento


class ParseoArchivo(BaseModel):
    """Resumen del contenido parseado: con qué estructura se va a trabajar.

    Según la familia de parser, se llenan los campos tabulares o los documentales.
    """

    parser_family: ParserFamily = Field(..., description="Familia de parser aplicada.")

    # ── Tabular (encuesta) ───────────────────────────────────────────────────
    headers: list[str] | None = Field(
        default=None, description="Nombres de columna detectados (tabular)."
    )
    n_columns: int | None = Field(default=None, description="Nº de columnas (tabular).")
    n_rows: int | None = Field(default=None, description="Nº de filas de datos (tabular).")
    preview_rows: list[list[str]] | None = Field(
        default=None, description="Primeras filas de muestra (tabular)."
    )
    sheet: str | None = Field(default=None, description="Hoja leída (XLSX).")

    # ── Documento (entrevista / prueba) ───────────────────────────────────────
    n_chars: int | None = Field(default=None, description="Nº de caracteres del texto (documento).")
    n_words: int | None = Field(default=None, description="Nº de palabras del texto (documento).")
    n_pages: int | None = Field(default=None, description="Nº de páginas (PDF).")
    text_preview: str | None = Field(
        default=None, description="Primeros caracteres del texto extraído (documento)."
    )

    # ── Comunes ───────────────────────────────────────────────────────────────
    encoding: str | None = Field(default=None, description="Codificación detectada (CSV/TXT).")
    notes: list[str] = Field(default_factory=list, description="Observaciones del parser.")


class ArchivoRegistrado(BaseModel):
    """Resumen de un archivo que quedó almacenado en RAW DATA."""

    nombre_original: str = Field(..., description="Nombre con el que se subió el archivo.")
    ruta_relativa: str = Field(
        ..., description="Ruta relativa dentro de storage (lo persistido en raw_data)."
    )
    extension: str = Field(..., description="Extensión detectada, p. ej. '.xlsx'.")
    mime_type: str = Field(..., description="MIME canónico derivado de la extensión.")
    parser_family: ParserFamily = Field(
        ..., description="Familia de parser a la que se enruta el archivo."
    )
    size_bytes: int = Field(..., description="Tamaño del archivo almacenado en bytes.")
    parseo: ParseoArchivo | None = Field(
        default=None,
        description="Resumen del contenido parseado (estructura con la que se trabajará).",
    )


class UploadResponse(BaseModel):
    """Respuesta del Paso 1 — subida del instrumento.

    Devuelve `id_crudo` (PK de raw_data) e `id_instrumento` (PK de
    instrumento_procesado) para los pasos siguientes del wizard.
    """

    model_config = ConfigDict(from_attributes=True)

    id_crudo: int = Field(..., description="PK de raw_data (tabla padre del pipeline).")
    id_instrumento: int = Field(
        ..., description="PK de instrumento_procesado (estado inicial 'recibido')."
    )
    id_owner: int = Field(..., description="Usuario propietario del instrumento.")
    tipo_instrumento: TipoInstrumento = Field(..., description="Tipo declarado del instrumento.")
    estado: str = Field(default="recibido", description="Estado del instrumento procesado.")
    fecha_carga: datetime | None = Field(default=None, description="Marca temporal de la carga.")

    archivo_respondido: ArchivoRegistrado = Field(
        ..., description="El archivo con las respuestas (raw_archivo)."
    )
    archivo_original: ArchivoRegistrado | None = Field(
        default=None,
        description="El instrumento original sin respuestas (raw_archivo_original), si se subió.",
    )

    mensaje: str = Field(
        default="Instrumento recibido y almacenado en crudo.",
        description="Mensaje legible para el frontend.",
    )
