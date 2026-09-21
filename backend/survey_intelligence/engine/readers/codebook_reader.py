# survey_intelligence/engine/readers/codebook_reader.py
"""
Lector y parser determinístico de codebooks (diccionarios de datos de microdatos).

Convierte archivos de codebook en un CodebookModel estructurado.
Formatos admitidos: CSV/TSV, XLSX/XLS, JSON, TXT y PDF.
Soporta:
  1. Diccionarios tabulares con valores en línea (ej. '1=Sí, 2=No').
  2. Diccionarios tabulares multi-fila (filas repetidas por cada opción de valor).
  3. Archivos JSON (diccionarios o listas de variables).
  4. Texto plano con sintaxis clave-valor (ej. 'P01 = Enunciado [1=A, 2=B]').
  5. PDF: se extrae el texto y se parsea como clave-valor / tabla.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from survey_intelligence.contracts.codebook import CodebookEntry, CodebookModel

# Patrones para detectar columnas clave en tablas
_RE_NAME_COL = re.compile(
    r"^(variable|var|campo|columna|codigo|code|name|id|pregunta_id|identificador|num|nro)$",
    re.IGNORECASE,
)
_RE_LABEL_COL = re.compile(
    r"^(etiqueta|label|descripcion|description|pregunta|texto|enunciado|nombre_variable|definicion|pregunta_texto)$",
    re.IGNORECASE,
)
_RE_VALUES_COL = re.compile(
    r"^(valores|values|categorias|categories|etiquetas_valores|value_labels|codigos|codes|opciones|catalogo|respuestas)$",
    re.IGNORECASE,
)
_RE_VAL_CODE_COL = re.compile(r"^(valor|code|codigo|val|clave)$", re.IGNORECASE)
_RE_VAL_LABEL_COL = re.compile(r"^(etiqueta_valor|valor_etiqueta|significado|categoria|cat)$", re.IGNORECASE)


def _parse_inline_values(text: str) -> dict[str, str]:
    """
    Parsea cadenas con pares código=etiqueta.
    Ejemplos soportados:
      - '1=Sí, 2=No, 9=No sabe'
      - '1: Primaria | 2: Secundaria'
      - '1 - Totalmente de acuerdo; 2 - De acuerdo'
    """
    if not text or not text.strip():
        return {}
    
    text = text.strip()
    # Si es JSON directo
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            pass

    values_dict: dict[str, str] = {}
    
    # Separadores de pares: comas, puntos y comas, barras o saltos de línea
    tokens = re.split(r"[\n;|]+|,(?=\s*\d+[\s=:–\-])", text)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        # Buscar separador clave-valor (=, :, -, –)
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*[:=–\-]\s*(.+)$", token)
        if m:
            code = m.group(1).strip()
            val_label = m.group(2).strip()
            values_dict[code] = val_label

    return values_dict


def _parse_tabular_rows(headers: list[str], rows: list[list[str]]) -> CodebookModel:
    """Parsea filas de tabla (CSV o Excel) detectando columnas."""
    if not headers or not rows:
        return CodebookModel()

    norm_headers = [re.sub(r"[^\w]+", "_", h.strip().lower()).strip("_") for h in headers]

    name_idx: int | None = None
    label_idx: int | None = None
    values_idx: int | None = None
    val_code_idx: int | None = None
    val_label_idx: int | None = None

    for i, nh in enumerate(norm_headers):
        if name_idx is None and _RE_NAME_COL.search(nh):
            name_idx = i
        elif label_idx is None and _RE_LABEL_COL.search(nh):
            label_idx = i
        elif values_idx is None and _RE_VALUES_COL.search(nh):
            values_idx = i
        elif val_code_idx is None and _RE_VAL_CODE_COL.search(nh):
            val_code_idx = i
        elif val_label_idx is None and _RE_VAL_LABEL_COL.search(nh):
            val_label_idx = i

    matched_any = any(
        _RE_NAME_COL.search(nh) or _RE_LABEL_COL.search(nh) or _RE_VALUES_COL.search(nh)
        for nh in norm_headers
    )
    if not matched_any:
        # Si ningún header coincidió con palabras clave de diccionario,
        # la primera fila podría ser un registro de datos.
        rows = [headers] + rows

    # Fallbacks posicionales si no se reconocieron por nombre
    if name_idx is None and len(headers) >= 1:
        name_idx = 0
    if label_idx is None:
        if len(headers) >= 2:
            label_idx = 1
        elif len(headers) == 1:
            label_idx = 0
    if values_idx is None and len(headers) >= 3 and val_code_idx is None:
        values_idx = 2

    is_multi_row = val_code_idx is not None and val_label_idx is not None

    entries: dict[str, CodebookEntry] = {}

    for row in rows:
        if name_idx >= len(row):
            continue
        name = row[name_idx].strip()
        if not name:
            continue

        label = row[label_idx].strip() if (label_idx is not None and label_idx < len(row)) else name
        if not label:
            label = name

        if is_multi_row:
            code = row[val_code_idx].strip() if val_code_idx < len(row) else ""
            vlabel = row[val_label_idx].strip() if val_label_idx < len(row) else ""
            if name in entries:
                existing = entries[name]
                new_vals = dict(existing.value_labels)
                if code:
                    new_vals[code] = vlabel or code
                entries[name] = CodebookEntry(
                    name=existing.name,
                    label=existing.label or label,
                    value_labels=new_vals,
                )
            else:
                initial_vals = {code: vlabel or code} if code else {}
                entries[name] = CodebookEntry(
                    name=name,
                    label=label,
                    value_labels=initial_vals,
                )
        else:
            raw_vals = row[values_idx].strip() if (values_idx is not None and values_idx < len(row)) else ""
            val_labels = _parse_inline_values(raw_vals) if raw_vals else {}
            
            if name in entries:
                existing = entries[name]
                merged_vals = dict(existing.value_labels)
                merged_vals.update(val_labels)
                entries[name] = CodebookEntry(
                    name=existing.name,
                    label=existing.label or label,
                    value_labels=merged_vals,
                )
            else:
                entries[name] = CodebookEntry(
                    name=name,
                    label=label,
                    value_labels=val_labels,
                )

    return CodebookModel(entries=entries)


def _read_csv_content(text: str) -> CodebookModel:
    """Lee CSV detectando delimitador (coma, punto y coma, tabulación)."""
    try:
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ";" if text.count(";") > text.count(",") else ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not rows:
            return CodebookModel()
        return _parse_tabular_rows(rows[0], rows[1:])
    except Exception:
        return CodebookModel()


def _read_json_content(text: str) -> CodebookModel:
    """Lee diccionario JSON."""
    try:
        data = json.loads(text)
    except Exception:
        return CodebookModel()

    entries: dict[str, CodebookEntry] = {}

    if isinstance(data, dict):
        for k, v in data.items():
            name = str(k).strip()
            if isinstance(v, str):
                entries[name] = CodebookEntry(name=name, label=v.strip())
            elif isinstance(v, dict):
                label = str(v.get("label") or v.get("descripcion") or v.get("etiqueta") or name).strip()
                raw_values = v.get("values") or v.get("valores") or v.get("categorias") or {}
                if isinstance(raw_values, str):
                    val_labels = _parse_inline_values(raw_values)
                elif isinstance(raw_values, dict):
                    val_labels = {str(code): str(lbl) for code, lbl in raw_values.items()}
                else:
                    val_labels = {}
                entries[name] = CodebookEntry(name=name, label=label, value_labels=val_labels)
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("variable") or item.get("campo") or "").strip()
            if not name:
                continue
            label = str(item.get("label") or item.get("descripcion") or item.get("etiqueta") or name).strip()
            raw_values = item.get("values") or item.get("valores") or item.get("categorias") or {}
            if isinstance(raw_values, str):
                val_labels = _parse_inline_values(raw_values)
            elif isinstance(raw_values, dict):
                val_labels = {str(code): str(lbl) for code, lbl in raw_values.items()}
            else:
                val_labels = {}
            entries[name] = CodebookEntry(name=name, label=label, value_labels=val_labels)

    return CodebookModel(entries=entries)


def _read_text_lines(text: str) -> CodebookModel:
    """Lee formato de líneas de texto (ej. P01 = Pregunta [1=Sí, 2=No])."""
    entries: dict[str, CodebookEntry] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        
        # Buscar patrón: IDENTIFICADOR = o : ETIQUETA [VALORES]
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*[:=]\s*(.+)$", line)
        if m:
            name = m.group(1).strip()
            rest = m.group(2).strip()
            
            # Chequear si tiene corchetes con valores [1=A, 2=B]
            val_labels = {}
            bracket_match = re.search(r"\[(.*)\]\s*$", rest)
            if bracket_match:
                val_labels = _parse_inline_values(bracket_match.group(1))
                label = rest[:bracket_match.start()].strip()
            else:
                label = rest
                
            entries[name] = CodebookEntry(name=name, label=label, value_labels=val_labels)
            
    return CodebookModel(entries=entries)


def _extract_pdf_text(data: bytes) -> str:
    """
    Extrae texto de un PDF (PyPDF2 con fallback a pdfplumber).

    Devuelve "" si no hay librería disponible o si falla la extracción, de modo
    que read_codebook degrade a un CodebookModel vacío sin lanzar excepción.
    """
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError:
        pass
    except Exception:
        return ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        return ""


def read_codebook(data: bytes | str, file_name: str = "") -> CodebookModel:
    """
    Función principal de lectura y parsing de codebook.

    Args:
        data: contenido en bytes o string del archivo.
        file_name: nombre del archivo opcional para identificar extensión.
    """
    ext = Path(file_name).suffix.lower() if file_name else ""

    # Caso PDF: extraer texto y parsearlo como líneas clave-valor / tabla.
    if ext == ".pdf" and isinstance(data, bytes):
        pdf_text = _extract_pdf_text(data)
        if pdf_text.strip():
            model = _read_text_lines(pdf_text.strip())
            if model.entries:
                return model
            model = _read_csv_content(pdf_text.strip())
            if model.entries:
                return model
        return CodebookModel()

    # Caso Excel (.xlsx, .xls)
    if ext in {".xlsx", ".xls"} and isinstance(data, bytes):
        try:
            import pandas as pd
            excel = pd.ExcelFile(io.BytesIO(data))
            # Usar la primera hoja
            df = pd.read_excel(excel, sheet_name=excel.sheet_names[0])
            headers = [str(c) for c in df.columns]
            rows = [[str(val) if not pd.isna(val) else "" for val in row] for row in df.itertuples(index=False)]
            return _parse_tabular_rows(headers, rows)
        except Exception:
            pass

    # Convertir bytes a string si aplica
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin1")
            except Exception:
                return CodebookModel()
    else:
        text = str(data)

    text_stripped = text.strip()
    if not text_stripped:
        return CodebookModel()

    # 1. Si es JSON explícito o empieza con sintaxis JSON
    if ext == ".json" or (text_stripped.startswith("{") and text_stripped.endswith("}")) or (text_stripped.startswith("[") and text_stripped.endswith("]")):
        model = _read_json_content(text_stripped)
        if model.entries:
            return model

    # 2. Si es archivo de texto plano explícito (.txt, .text)
    if ext in {".txt", ".text"}:
        model = _read_text_lines(text_stripped)
        if model.entries:
            return model
        model = _read_csv_content(text_stripped)
        if model.entries:
            return model

    # 3. Si es CSV / TSV explícito (.csv, .tsv)
    if ext in {".csv", ".tsv"}:
        model = _read_csv_content(text_stripped)
        if model.entries:
            return model

    # 4. Auto-detección por contenido si la extensión es desconocida o no dada:
    # ¿Tiene mayoría de líneas en formato clave-valor ("ID = ..." o "ID: ...")?
    lines = [l.strip() for l in text_stripped.splitlines() if l.strip() and not l.strip().startswith(("#", "//"))]
    kv_matches = sum(1 for l in lines if re.match(r"^[A-Za-z0-9_.\-]+\s*[:=]\s*.+$", l))
    if lines and (kv_matches / len(lines) >= 0.5):
        model = _read_text_lines(text_stripped)
        if model.entries:
            return model

    # ¿Tiene delimitadores tabulares comunes?
    if "," in text_stripped or ";" in text_stripped or "\t" in text_stripped:
        model = _read_csv_content(text_stripped)
        if model.entries:
            return model

    # Fallback final a líneas de texto
    return _read_text_lines(text_stripped)
