"""Configuración de la interpretación: reglas propias y diccionario de escalas compartido."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_REGLAS = Path(__file__).resolve().parents[2] / "config" / "conocimiento.yaml"
_SEPARADORES = re.compile(r"[_.\-/()¿?¡!,:;]+")


def _leer(ruta: Path) -> dict[str, Any]:
    with ruta.open(encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo) or {}
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta} debe contener un diccionario YAML.")
    return datos


@lru_cache(maxsize=1)
def reglas() -> dict[str, Any]:
    """`config/conocimiento.yaml`: datos personales, formas binarias, separadores, unidades."""
    return _leer(_REGLAS)


@lru_cache(maxsize=1)
def escalas() -> dict[str, Any]:
    """`shared/config/escalas_likert.yaml` (el mismo diccionario que usa la limpieza)."""
    import shared

    return _leer(Path(shared.__file__).resolve().parent / "config" / "escalas_likert.yaml")


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios colapsados."""
    sin = "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def palabras(texto: str) -> str:
    """Texto normalizado con los signos convertidos en espacios y rodeado de espacios,
    para buscar PALABRAS COMPLETAS con `f" {palabra} " in palabras(texto)`."""
    return " " + " ".join(_SEPARADORES.sub(" ", normalizar(texto)).split()) + " "
