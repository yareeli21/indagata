"""Capa de parseo del instrument-service.

Punto de entrada único: `parse_file(content, extension, parser_family)`. Lee el
contenido real del archivo para saber con qué estructura se va a trabajar:

  - TABULAR  (encuesta):            columnas + nº de filas  → ParsedContent tabular.
  - DOCUMENTO (entrevista/prueba):  texto extraído + métricas → ParsedContent documento.

Es autocontenida: no depende de survey_intelligence ni de ninguna capa de
análisis (LLM, KPIs, vectorización). Solo identifica y extrae el contenido crudo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config.constants import ParserFamily
from app.parsing.document_parser import DocumentParseError, read_document
from app.parsing.tabular_parser import TabularParseError, read_tabular

# Nº de filas de muestra que se incluyen como preview en la respuesta.
_PREVIEW_ROWS = 5
# Nº de caracteres de texto que se incluyen como preview documental.
_PREVIEW_CHARS = 500


class ParseError(Exception):
    """El contenido no pudo parsearse según su familia."""


@dataclass(frozen=True)
class ParsedContent:
    """Resultado uniforme del parseo, independiente del formato de origen.

    Campos tabulares (parser_family == TABULAR):
        headers:      Nombres de columna detectados.
        n_columns:    Nº de columnas.
        n_rows:       Nº de filas de datos.
        preview_rows: Primeras filas (muestra) para inspección.
        sheet:        Hoja leída (XLSX) o None.
        encoding:     Codificación detectada (CSV) o None.

    Campos documentales (parser_family == DOCUMENTO):
        n_chars:      Nº de caracteres del texto extraído.
        n_words:      Nº de palabras.
        n_pages:      Nº de páginas (PDF) o None.
        text_preview: Primeros caracteres del texto extraído.

    Comunes:
        parser_family: Familia que produjo el resultado.
        notes:         Observaciones del parser (encoding de respaldo, PDF escaneado…).
    """

    parser_family: ParserFamily

    # Tabular
    headers: list[str] | None = None
    n_columns: int | None = None
    n_rows: int | None = None
    preview_rows: list[list[str]] | None = None
    sheet: str | None = None

    # Documento
    n_chars: int | None = None
    n_words: int | None = None
    n_pages: int | None = None
    text_preview: str | None = None

    # Comunes
    encoding: str | None = None
    notes: list[str] = field(default_factory=list)


def parse_file(
    content: bytes,
    extension: str,
    parser_family: ParserFamily,
    *,
    sheet: str | None = None,
) -> ParsedContent:
    """Parsea el contenido según la familia y devuelve un ParsedContent.

    Args:
        content:       Bytes del archivo.
        extension:     Extensión en minúsculas con punto (p. ej. ".csv").
        parser_family: Familia de parser a aplicar (del detector de tipo).
        sheet:         Hoja XLSX a leer (opcional; None = primera).

    Raises:
        ParseError: si el contenido no puede parsearse.
    """
    if parser_family is ParserFamily.TABULAR:
        try:
            table = read_tabular(content, extension, sheet=sheet)
        except TabularParseError as exc:
            raise ParseError(str(exc)) from exc

        if table.n_columns == 0:
            raise ParseError("El archivo no tiene columnas.")

        return ParsedContent(
            parser_family=ParserFamily.TABULAR,
            headers=table.headers,
            n_columns=table.n_columns,
            n_rows=table.n_rows,
            preview_rows=table.rows[:_PREVIEW_ROWS],
            sheet=table.sheet,
            encoding=table.encoding,
            notes=list(table.notes),
        )

    # DOCUMENTO
    try:
        doc = read_document(content, extension)
    except DocumentParseError as exc:
        raise ParseError(str(exc)) from exc

    text = doc.text
    return ParsedContent(
        parser_family=ParserFamily.DOCUMENTO,
        n_chars=len(text),
        n_words=len(text.split()),
        n_pages=doc.n_pages,
        text_preview=text[:_PREVIEW_CHARS],
        encoding=doc.encoding,
        notes=list(doc.notes),
    )
