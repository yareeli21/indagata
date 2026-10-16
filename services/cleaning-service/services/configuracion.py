"""Carga de la configuración editable (`config/*.yaml`).

Los archivos se leen una vez por proceso (caché). La ruta de la carpeta puede
cambiarse con la variable de entorno CLEANING_CONFIG_DIR (útil en pruebas).

El diccionario de escalas Likert vive en `shared/config/escalas_likert.yaml`
(lo comparte con knowledge-service); si CLEANING_CONFIG_DIR trae su propia copia,
esa tiene prioridad.
"""
from __future__ import annotations

import os
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DIR_DEFECTO = Path(__file__).resolve().parents[1] / "config"


def _directorio() -> Path:
    return Path(os.getenv("CLEANING_CONFIG_DIR", str(_DIR_DEFECTO)))


def _leer(nombre: str) -> dict[str, Any]:
    ruta = _directorio() / nombre
    with ruta.open(encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo) or {}
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta} debe contener un diccionario YAML.")
    return datos


@lru_cache(maxsize=1)
def reglas() -> dict[str, Any]:
    """Reglas generales (`limpieza.yaml`): tokens de vacío, umbrales, opciones de prueba…"""
    return _leer("limpieza.yaml")


def _ruta_escalas() -> Path:
    propia = _directorio() / "escalas_likert.yaml"
    if propia.exists():
        return propia
    import shared

    return Path(shared.__file__).resolve().parent / "config" / "escalas_likert.yaml"


@lru_cache(maxsize=1)
def escalas_likert() -> dict[str, Any]:
    """Diccionario de escalas Likert (`shared/config/escalas_likert.yaml`)."""
    ruta = _ruta_escalas()
    with ruta.open(encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo) or {}
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta} debe contener un diccionario YAML.")
    return datos


def recargar() -> None:
    """Olvida la caché (tras editar los YAML en caliente o en pruebas)."""
    reglas.cache_clear()
    escalas_likert.cache_clear()


def normalizar_texto(valor: str) -> str:
    """Minúsculas, sin acentos y con espacios colapsados (para comparar con los diccionarios)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", valor) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_acentos.lower().split())
