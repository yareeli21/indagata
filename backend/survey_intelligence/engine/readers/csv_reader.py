# survey_intelligence/engine/readers/csv_reader.py
"""
Reader de CSV.

Maneja los casos reales observados en las plataformas:
  - BOM UTF-8 (LimeSurvey).
  - Latin-1/CP1252 (exportaciones de Microsoft Forms con acentos).
  - Comillas y celdas con separadores internos (';', ', ').
  - Filas vacías y filas más cortas que el encabezado (se rellenan).
  - Saltos de línea embebidos en encabezados (se normalizan).

La detección de codificación es por intento en orden, no por suposición.
"""
from __future__ import annotations

import csv
import io

from survey_intelligence.engine.readers.header_utils import (
    normalize_cell,
    normalize_header,
)
from survey_intelligence.engine.readers.raw_table import RawTable

# Orden de intentos de codificación. utf-8-sig consume el BOM si está presente.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class CsvReadError(Exception):
    """El contenido no pudo interpretarse como CSV."""


def _decode(data: bytes) -> tuple[str, str]:
    """Intenta decodificar los bytes; devuelve (texto, encoding_usado)."""
    last_error: Exception | None = None
    for enc in _ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError as exc:
            last_error = exc
    # latin-1 nunca falla, pero por seguridad:
    raise CsvReadError(f"No se pudo decodificar el CSV: {last_error}")


def read_csv(data: bytes) -> RawTable:
    """
    Lee bytes CSV y devuelve un RawTable.

    Raises:
        CsvReadError: si no hay contenido o no puede parsearse.
    """
    if not data:
        raise CsvReadError("El archivo CSV está vacío.")

    text, encoding = _decode(data)
    notes: list[str] = []
    if encoding not in ("utf-8-sig", "utf-8"):
        notes.append(f"Codificación de respaldo usada: {encoding}")

    # Detectar el delimitador (coma vs punto y coma) con el Sniffer, con fallback a coma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = [row for row in reader]

    if not all_rows:
        raise CsvReadError("El CSV no contiene filas.")

    headers = [normalize_header(h) for h in all_rows[0]]
    n_cols = len(headers)

    data_rows: list[list[str]] = []
    for row in all_rows[1:]:
        # Ignorar filas totalmente vacías (comunes al final de exportaciones).
        if not any(cell.strip() for cell in row):
            # Se conserva como fila vacía real solo si tiene la longitud esperada;
            # de lo contrario se omite (ruido de exportación).
            if len(row) >= n_cols and any(row):
                data_rows.append([normalize_cell(c) for c in row[:n_cols]])
            continue
        normalized = [normalize_cell(c) for c in row]
        # Rellenar o truncar a la longitud del encabezado.
        if len(normalized) < n_cols:
            normalized += [""] * (n_cols - len(normalized))
        elif len(normalized) > n_cols:
            normalized = normalized[:n_cols]
        data_rows.append(normalized)

    return RawTable(
        headers=headers,
        rows=data_rows,
        encoding=encoding,
        sheet=None,
        notes=notes,
    )
