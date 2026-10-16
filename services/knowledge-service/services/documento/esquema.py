"""Validación del documento final contra su JSON Schema formal (draft 2020-12).

Un archivo por tipo (`esquemas/documento_<tipo>.json`) más `comun.json` con las
definiciones compartidas. Cada documento se valida al construirlo: si no cumple,
no se guarda (es un error de programación, no del investigador).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ESQUEMA_VERSION = "1.0"
_DIR = Path(__file__).resolve().parents[2] / "esquemas"


class DocumentoInvalido(ValueError):
    """El documento construido no cumple su JSON Schema."""


def _cargar(nombre: str) -> dict[str, Any]:
    return json.loads((_DIR / nombre).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def validador(tipo: str) -> Draft202012Validator:
    comun = _cargar("comun.json")
    registro = Registry().with_resource("comun.json", Resource.from_contents(comun))
    esquema = _cargar(f"documento_{tipo}.json")
    Draft202012Validator.check_schema(esquema)
    return Draft202012Validator(esquema, registry=registro)


def errores(documento: dict[str, Any]) -> list[str]:
    tipo = (documento.get("instrumento") or {}).get("tipo") or ""
    try:
        v = validador(tipo)
    except FileNotFoundError:
        return [f"Tipo de instrumento sin esquema: {tipo!r}"]
    return [f"/{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in sorted(v.iter_errors(documento), key=lambda e: list(e.absolute_path))]


def validar(documento: dict[str, Any]) -> None:
    """Lanza DocumentoInvalido con los primeros errores si el documento no cumple."""
    lista = errores(documento)
    if lista:
        raise DocumentoInvalido("; ".join(lista[:5]) + (f" (y {len(lista) - 5} más)" if len(lista) > 5 else ""))
