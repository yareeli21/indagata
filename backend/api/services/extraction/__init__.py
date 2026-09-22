# api/services/extraction/__init__.py
"""
Módulo Unificado de Extracción documental.

Extrae texto de un archivo **según su formato** (CSV, XLSX, PDF, DOCX, TXT, SAV,
y formatos futuros), de forma DESACOPLADA del tipo de instrumento. El tipo de
instrumento (encuesta / entrevista / prueba_estandarizada) NO influye aquí: es el
SIS quien, más adelante, decide cómo procesar el contenido extraído.

Superficie pública:
    from api.services.extraction import (
        extraer_texto,            # dispatch por formato
        limpiar_texto,            # limpieza tradicional (preserva estructura)
        extraer_texto_con_cache,  # extracción + caché por hash de contenido
        FORMATOS_SOPORTADOS,
    )
"""
from __future__ import annotations

from api.services.extraction.extractor import (
    FORMATOS_SOPORTADOS,
    extraer_texto,
    extraer_texto_con_cache,
    limpiar_texto,
)

__all__ = [
    "extraer_texto",
    "limpiar_texto",
    "extraer_texto_con_cache",
    "FORMATOS_SOPORTADOS",
]
