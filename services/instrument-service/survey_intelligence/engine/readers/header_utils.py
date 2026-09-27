# survey_intelligence/engine/readers/header_utils.py
"""
Utilidades de normalización de encabezados, compartidas por los readers.

Los encabezados de encuesta traen ruido de plataforma: saltos de línea embebidos
(Microsoft Forms), espacios de borde y espacios internos múltiples. Aquí se limpian
de forma consistente SIN perder el texto de la pregunta.
"""
from __future__ import annotations

import re

_WS_RUN = re.compile(r"\s+")


def normalize_header(raw: str | None) -> str:
    """
    Normaliza un encabezado:
      - None -> "".
      - reemplaza saltos de línea/tabs por espacio.
      - colapsa espacios múltiples en uno.
      - recorta espacios de los bordes.

    Preserva el contenido textual (no elimina corchetes, puntos ni signos).
    """
    if raw is None:
        return ""
    text = str(raw).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = _WS_RUN.sub(" ", text)
    return text.strip()


def normalize_cell(raw: object) -> str:
    """
    Normaliza una celda a str.

    - None -> "".
    - datetime/valores no str -> str(valor) (los readers pueden pre-serializar).
    - str -> recorta bordes, preserva separadores internos (';', ', ').
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    return str(raw)
