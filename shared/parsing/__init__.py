"""Lectores de archivos compartidos entre servicios.

  - tabular_parser:  CSV (con detección de codificación y delimitador), XLSX y XLS.
  - document_parser: TXT, PDF (pypdf) y DOCX (python-docx).
  - header_utils:    normalización de encabezados y celdas.

Las librerías de formato (openpyxl, xlrd, pypdf, python-docx) se importan dentro
de cada función: un servicio que no lee ese formato no necesita instalarlas.
"""
from shared.parsing.document_parser import DocumentParseError, ExtractedDocument, read_document
from shared.parsing.header_utils import normalize_cell, normalize_header
from shared.parsing.raw_table import RawTable
from shared.parsing.tabular_parser import TabularParseError, read_csv, read_tabular, read_xls, read_xlsx

__all__ = [
    "DocumentParseError",
    "ExtractedDocument",
    "RawTable",
    "TabularParseError",
    "normalize_cell",
    "normalize_header",
    "read_csv",
    "read_document",
    "read_tabular",
    "read_xls",
    "read_xlsx",
]
