"""Índice ligero de artefactos (manifiesto JSON) + saneo de nombres.

Ver design.md §3.2 y §3.6. El manifiesto vive en
`settings.json_path_abs/_index/artefactos.json`, se lee/escribe de forma
atómica (`.part` + `replace`) y toda mutación se serializa con un
`threading.Lock` de módulo. La versión es autoincremental por
`(tipo, instrumentoId)` empezando en 1.
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from pathlib import Path

from shared.db.core.config import settings

# ── Saneo de nombre de archivo (copiado 1:1 de instrument-service local_backend) ──
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str) -> str:
    """Sanea un nombre de archivo preservando su extensión (sin componentes de ruta)."""
    base = Path(filename).name
    stem = Path(base).stem
    suffix = Path(base).suffix.lower()
    stem_ascii = (
        unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    )
    stem_safe = _SAFE_CHARS.sub("_", stem_ascii).strip("._-") or "archivo"
    return f"{stem_safe[:120]}{suffix}"


def slug(nombre: str | None) -> str:
    """Devuelve un slug de nombre de archivo saneado (fallback 'archivo')."""
    return _sanitize_filename(nombre or "archivo")


# ── Índice (manifiesto JSON) ──────────────────────────────────────────────────
_lock = threading.Lock()


class IndexError_(Exception):
    """Error del índice de artefactos (p.ej. manifiesto corrupto)."""


def _index_path() -> Path:
    return settings.json_path_abs / "_index" / "artefactos.json"


def _leer_manifiesto() -> list[dict]:
    """Lee el manifiesto. Ausente -> lista vacía. Corrupto -> IndexError_."""
    ruta = _index_path()
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IndexError_("Índice de artefactos corrupto.") from exc
    if not isinstance(datos, list):
        raise IndexError_("Índice de artefactos corrupto.")
    return datos


def _escribir_manifiesto(entradas: list[dict]) -> None:
    """Escribe el manifiesto de forma atómica (.part + replace)."""
    ruta = _index_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".part")
    tmp.write_text(json.dumps(entradas, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ruta)


def proxima_version(tipo: str, instrumento_id: str) -> int:
    """Siguiente versión para (tipo, instrumentoId); empieza en 1."""
    entradas = _leer_manifiesto()
    versiones = [
        e.get("version", 0)
        for e in entradas
        if e.get("tipo") == tipo and e.get("instrumentoId") == instrumento_id
    ]
    return (max(versiones) + 1) if versiones else 1


def registrar(entrada: dict) -> None:
    """Añade una entrada al manifiesto (lectura + escritura atómica)."""
    entradas = _leer_manifiesto()
    entradas.append(entrada)
    _escribir_manifiesto(entradas)


def listar(
    *, instrumento_id: str | None = None, tipo: str | None = None
) -> list[dict]:
    """Lista entradas del manifiesto filtrando por instrumentoId y/o tipo."""
    entradas = _leer_manifiesto()
    if instrumento_id is not None:
        entradas = [e for e in entradas if e.get("instrumentoId") == instrumento_id]
    if tipo is not None:
        entradas = [e for e in entradas if e.get("tipo") == tipo]
    return entradas


def buscar(tipo: str, instrumento_id: str, version: int | None = None) -> dict | None:
    """Busca una entrada por (tipo, instrumentoId); sin versión -> la última."""
    candidatas = [
        e
        for e in _leer_manifiesto()
        if e.get("tipo") == tipo and e.get("instrumentoId") == instrumento_id
    ]
    if not candidatas:
        return None
    if version is not None:
        for e in candidatas:
            if e.get("version") == version:
                return e
        return None
    return max(candidatas, key=lambda e: e.get("version", 0))
