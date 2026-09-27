# survey_intelligence/pipeline/stages/s1_ingestion.py
"""
Etapa S1 — Ingesta.

Decodifica el archivo (base64), elige el reader según MIME/extensión, produce un
RawTable y detecta la plataforma de origen. Es una de las dos etapas FATALES:
si el archivo no puede parsearse, el pipeline retorna status='failed'.

No conoce el orquestador ni el PipelineContext (se cablearán en la Tarea 13);
expone una función pura ingest() que devuelve un IngestionResult.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field

from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.engine.heuristics.platform_columns import (
    PlatformDetection,
    detect_platform,
)
from survey_intelligence.engine.readers.csv_reader import CsvReadError, read_csv
from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.readers.xlsx_reader import XlsxReadError, read_xlsx

# MIME types y extensiones reconocidos.
_XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
_CSV_MIMES = {"text/csv", "application/csv", "text/plain"}


class IngestionError(Exception):
    """Error fatal de ingesta (archivo corrupto o formato no soportado)."""


@dataclass(frozen=True)
class IngestionResult:
    """Salida de S1: la tabla cruda + la detección de plataforma."""
    raw_table: RawTable
    platform: PlatformDetection
    notes: list[str] = field(default_factory=list)


def _decode_b64(b64: str) -> bytes:
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise IngestionError(f"file_bytes_b64 no es base64 válido: {exc}") from exc


def _choose_format(file_name: str, mime_type: str) -> str:
    """Devuelve 'xlsx' o 'csv' según MIME o extensión. Extensión tiene prioridad."""
    name = file_name.lower().strip()
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        return "xlsx"
    if name.endswith(".csv") or name.endswith(".txt"):
        return "csv"
    mime = (mime_type or "").lower().strip()
    if mime in _XLSX_MIMES:
        return "xlsx"
    if mime in _CSV_MIMES:
        return "csv"
    raise IngestionError(
        f"Formato no soportado: file_name='{file_name}', mime='{mime_type}'. "
        f"Se admite CSV y XLSX."
    )


def ingest(request: SurveyIngestionRequest) -> IngestionResult:
    """
    Ejecuta S1 sobre la petición.

    Raises:
        IngestionError: si el archivo es corrupto o de formato no soportado (fatal).
    """
    data = _decode_b64(request.survey.file_bytes_b64)
    if not data:
        raise IngestionError("El archivo está vacío.")

    fmt = _choose_format(request.survey.file_name, request.survey.mime_type)

    try:
        if fmt == "xlsx":
            raw = read_xlsx(data, sheet=request.survey.sheet)
        else:
            raw = read_csv(data)
    except (CsvReadError, XlsxReadError) as exc:
        raise IngestionError(str(exc)) from exc

    if raw.n_columns == 0:
        raise IngestionError("El archivo no tiene columnas.")

    platform = detect_platform(raw.headers)

    notes = list(raw.notes)
    if platform.platform_guess:
        notes.append(f"Plataforma detectada: {platform.platform_guess}")
    else:
        notes.append("Plataforma no identificada; columnas administrativas por forma.")

    return IngestionResult(raw_table=raw, platform=platform, notes=notes)
