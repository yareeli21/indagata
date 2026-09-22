# api/services/extraction/extractor.py
"""
Extractor documental unificado, con dispatch por FORMATO (no por tipo de instrumento).

Arquitectura:
    extraer_texto(ruta)         -> elige el lector por extensión (.pdf/.docx/.xlsx/.csv/.txt/.sav)
    limpiar_texto(texto)        -> limpieza tradicional que preserva la estructura
    extraer_texto_con_cache(ru) -> extracción con caché por hash de contenido (storage/data)

Para añadir un formato nuevo basta con registrar un lector en `_LECTORES`.
El comportamiento (librerías, fallbacks y caché) se conserva 1:1 respecto a la
implementación previa que vivía en services_carga.py (_extract_text_placeholder,
_limpiar_texto_extraido, _extraer_texto_con_cache).
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Callable

from api.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lectores por formato (cada uno recibe la ruta y devuelve texto)
# ---------------------------------------------------------------------------

def _leer_pdf(ruta: Path) -> str:
    try:
        import PyPDF2
        texto = []
        with open(ruta, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for pagina in reader.pages:
                texto.append(pagina.extract_text())
        return "\n".join(texto)
    except ImportError:
        # Fallback si PyPDF2 no está instalado.
        try:
            import pdfplumber
            texto = []
            with pdfplumber.open(ruta) as pdf:
                for pagina in pdf.pages:
                    texto.append(pagina.extract_text() or "")
            return "\n".join(texto)
        except ImportError:
            return "[PyPDF2 o pdfplumber no instalado. Instalar: pip install PyPDF2]"


def _leer_docx(ruta: Path) -> str:
    try:
        from docx import Document
        doc = Document(ruta)
        texto = [parrafo.text for parrafo in doc.paragraphs]
        return "\n".join(texto)
    except ImportError:
        return "[python-docx no instalado. Instalar: pip install python-docx]"


def _leer_xlsx(ruta: Path) -> str:
    try:
        import pandas as pd
        excel = pd.ExcelFile(ruta)
        texto_completo = []
        for nombre_hoja in excel.sheet_names:
            df = pd.read_excel(excel, sheet_name=nombre_hoja)
            texto_completo.append(f"=== Hoja: {nombre_hoja} ===")
            texto_completo.append(df.to_string(index=False))
        return "\n\n".join(texto_completo)
    except ImportError:
        return "[pandas no instalado. Instalar: pip install pandas openpyxl]"


def _leer_csv(ruta: Path) -> str:
    try:
        import pandas as pd
        df = pd.read_csv(ruta, encoding="utf-8")
        return df.to_string(index=False)
    except UnicodeDecodeError:
        import pandas as pd
        df = pd.read_csv(ruta, encoding="latin1")
        return df.to_string(index=False)
    except ImportError:
        # Fallback sin pandas.
        return ruta.read_text(encoding="utf-8", errors="ignore")


def _leer_txt(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8", errors="ignore")


def _leer_sav(ruta: Path) -> str:
    try:
        import pyreadstat
        df, meta = pyreadstat.read_sav(str(ruta))
        texto = [
            "=== Metadatos SPSS ===",
            f"Variables: {len(meta.column_names)}",
            f"Casos: {len(df)}",
            "",
            "=== Etiquetas de variables ===",
            "\n".join([f"{var}: {label}" for var, label in meta.column_labels.items()]),
            "",
            "=== Datos ===",
            df.head(100).to_string(index=False),
        ]
        return "\n".join(texto)
    except ImportError:
        return "[pyreadstat no instalado. Instalar: pip install pyreadstat]"


# Registro de lectores por extensión. Añadir formatos futuros aquí.
_LECTORES: dict[str, Callable[[Path], str]] = {
    ".pdf": _leer_pdf,
    ".docx": _leer_docx,
    ".xlsx": _leer_xlsx,
    ".csv": _leer_csv,
    ".txt": _leer_txt,
    ".sav": _leer_sav,
}

FORMATOS_SOPORTADOS: tuple[str, ...] = tuple(_LECTORES.keys())


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def extraer_texto(ruta: Path, extension: str | None = None) -> str:
    """
    Extrae texto de un archivo eligiendo el lector por su formato (extensión).

    Desacoplado del tipo de instrumento: solo importa el formato del archivo.
    Devuelve un texto de diagnóstico entre corchetes si el formato no está
    soportado o si ocurre un error (mismo contrato que la versión previa).
    """
    try:
        ext = (extension or ruta.suffix).lower()
        lector = _LECTORES.get(ext)
        if lector is None:
            return (
                f"[Formato {ext} no soportado. Formatos válidos: "
                f"{', '.join(FORMATOS_SOPORTADOS)}]"
            )
        return lector(ruta)
    except Exception as e:  # noqa: BLE001
        return f"[Error al extraer texto de {ruta.suffix}: {str(e)}]"


def limpiar_texto(texto: str) -> str:
    """
    Limpieza tradicional de ciencia de datos para texto extraído.

    Aplica: normalización de espacios/saltos de línea, eliminación de caracteres
    de control, colapso de líneas vacías. NO aplica lower(), ni elimina puntuación
    ni tildes (preserva la estructura significativa del instrumento).
    """
    # Eliminar caracteres de control excepto \n y \t.
    texto = "".join(char for char in texto if char.isprintable() or char in "\n\t")

    # Normalizar saltos de línea (Windows \r\n -> Unix \n).
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    # Colapsar líneas vacías múltiples (máx 2 consecutivas).
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # Quitar espacios al final de cada línea.
    lineas = [linea.rstrip() for linea in texto.split("\n")]
    texto = "\n".join(lineas)

    # Normalizar espacios múltiples en la misma línea.
    texto = re.sub(r"[ \t]+", " ", texto)

    # Eliminar espacios antes de puntuación.
    texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)

    return texto.strip()


def extraer_texto_con_cache(ruta_archivo: Path) -> tuple[str, bool, Path]:
    """
    Extrae texto usando un caché por hash de contenido (storage/data/{sha256}.txt).

    Si el archivo ya se procesó (mismo hash), devuelve el texto cacheado; si no,
    lo extrae, lo cachea y lo devuelve.

    Returns:
        (texto_extraido, desde_cache, ruta_cache)
    """
    # Hash SHA256 del contenido del archivo.
    sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)
    hash_archivo = sha256.hexdigest()

    cache_dir = settings.data_path_abs
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{hash_archivo}.txt"

    # Cache hit.
    if cache_path.exists():
        try:
            texto = cache_path.read_text(encoding="utf-8")
            return texto, True, cache_path
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error al leer caché {cache_path.name}: {e}. Extrayendo del archivo...")

    # Cache miss: extraer y cachear.
    texto = extraer_texto(ruta_archivo, ruta_archivo.suffix.lower())
    try:
        cache_path.write_text(texto, encoding="utf-8")
        logger.info(f"Texto guardado en caché: {cache_path.name}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"No se pudo guardar caché: {e}")

    return texto, False, cache_path
