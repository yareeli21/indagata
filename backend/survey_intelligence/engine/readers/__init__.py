# survey_intelligence/engine/readers/__init__.py
"""Readers de formatos de entrada (CSV, XLSX) -> RawTable."""
from __future__ import annotations

from survey_intelligence.engine.readers.csv_reader import CsvReadError, read_csv
from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.readers.xlsx_reader import XlsxReadError, read_xlsx

__all__ = ["RawTable", "read_csv", "read_xlsx", "CsvReadError", "XlsxReadError"]
