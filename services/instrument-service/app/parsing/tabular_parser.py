"""Parser tabular — lee CSV y XLSX a un RawTable.

Casos reales cubiertos (exportaciones de Google Forms, Microsoft Forms, LimeSurvey):
  - CSV con BOM UTF-8, Latin-1/CP1252, delimitador coma o punto y coma.
  - XLSX con fechas nativas (se serializan a ISO) y selección de hoja.
  - Saltos de línea embebidos en encabezados (se normalizan).
  - Filas vacías o más cortas que el encabezado (se omiten o rellenan).

Autocontenido: no depende de survey_intelligence ni de ninguna capa de análisis.
"""
from __future__ import annotations

import csv
import datetime as _dt
import io

from app.parsing.header_utils import normalize_cell, normalize_header
from app.parsing.raw_table import RawTable

# Orden de intentos de codificación. utf-8-sig consume el BOM si está presente.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class TabularParseError(Exception):
    """El contenido no pudo interpretarse como CSV/XLSX."""


# ─────────────────────────────── CSV ─────────────────────────────────────────

def _decode(data: bytes) -> tuple[str, str]:
    """Intenta decodificar los bytes; devuelve (texto, encoding_usado)."""
    last_error: Exception | None = None
    for enc in _ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError as exc:
            last_error = exc
    raise TabularParseError(f"No se pudo decodificar el CSV: {last_error}")


def read_csv(data: bytes) -> RawTable:
    """Lee bytes CSV y devuelve un RawTable."""
    if not data:
        raise TabularParseError("El archivo CSV está vacío.")

    text, encoding = _decode(data)
    notes: list[str] = []
    if encoding not in ("utf-8-sig", "utf-8"):
        notes.append(f"Codificación de respaldo usada: {encoding}")

    # Detectar delimitador (coma/; /tab) con el Sniffer; fallback a coma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = [row for row in reader]
    if not all_rows:
        raise TabularParseError("El CSV no contiene filas.")

    headers = [normalize_header(h) for h in all_rows[0]]
    n_cols = len(headers)

    data_rows: list[list[str]] = []
    for row in all_rows[1:]:
        if not any(cell.strip() for cell in row):
            if len(row) >= n_cols and any(row):
                data_rows.append([normalize_cell(c) for c in row[:n_cols]])
            continue
        normalized = [normalize_cell(c) for c in row]
        if len(normalized) < n_cols:
            normalized += [""] * (n_cols - len(normalized))
        elif len(normalized) > n_cols:
            normalized = normalized[:n_cols]
        data_rows.append(normalized)

    return RawTable(headers=headers, rows=data_rows, encoding=encoding, sheet=None, notes=notes)


# ─────────────────────────────── XLSX ────────────────────────────────────────

def _cell_to_str(value: object) -> str:
    """Serializa una celda XLSX a str, normalizando fechas a ISO."""
    if value is None:
        return ""
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return normalize_cell(value)


def read_xlsx(data: bytes, sheet: str | None = None) -> RawTable:
    """Lee bytes XLSX y devuelve un RawTable.

    Args:
        data:  Contenido del archivo .xlsx/.xls (OOXML).
        sheet: Nombre de hoja; None = primera hoja.
    """
    if not data:
        raise TabularParseError("El archivo XLSX está vacío.")

    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise TabularParseError("openpyxl no está disponible.") from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise TabularParseError(f"No se pudo abrir el XLSX: {exc}") from exc

    try:
        if sheet is not None:
            if sheet not in wb.sheetnames:
                raise TabularParseError(
                    f"La hoja '{sheet}' no existe. Hojas: {wb.sheetnames}"
                )
            ws = wb[sheet]
        else:
            ws = wb[wb.sheetnames[0]]
        raw_rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
        sheet_title = ws.title
    finally:
        wb.close()

    if not raw_rows:
        raise TabularParseError("La hoja no contiene filas.")

    headers = [normalize_header(_cell_to_str(h)) for h in raw_rows[0]]
    n_cols = len(headers)

    data_rows: list[list[str]] = []
    for row in raw_rows[1:]:
        cells = [_cell_to_str(c) for c in row]
        if not any(c.strip() for c in cells):
            continue
        if len(cells) < n_cols:
            cells += [""] * (n_cols - len(cells))
        elif len(cells) > n_cols:
            cells = cells[:n_cols]
        data_rows.append(cells)

    return RawTable(headers=headers, rows=data_rows, encoding=None, sheet=sheet_title, notes=[])


def read_tabular(data: bytes, extension: str, sheet: str | None = None) -> RawTable:
    """Enruta a read_csv/read_xlsx según la extensión (.csv/.xlsx/.xls)."""
    ext = extension.lower()
    if ext == ".csv":
        return read_csv(data)
    if ext in (".xlsx", ".xls"):
        return read_xlsx(data, sheet=sheet)
    raise TabularParseError(f"Extensión tabular no soportada: {extension}")
