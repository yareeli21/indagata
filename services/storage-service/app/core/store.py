"""Decisión de ruta + lectura/escritura atómica de artefactos.

Ver design.md §3.4 (ruteo por tipo) y §3.6 (errores). La raíz de storage se
deriva como `settings.raw_path_abs.parent` (igual que local_backend del
instrument-service), y toda key resuelta se verifica DENTRO de esa raíz
(defensa path-traversal).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.db.core.config import settings

# Tipos de artefacto válidos (sin 'json' genérico; §3.2).
TIPOS_VALIDOS = {"raw", "sav", "metadata", "analysis", "temp"}


class StoreError(Exception):
    """Error de almacenamiento (escritura/lectura a disco)."""


class TipoInvalidoError(Exception):
    """Tipo de artefacto no soportado."""


class RutaInseguraError(Exception):
    """La ruta resuelta queda fuera de la raíz de storage (path traversal)."""


def _storage_root() -> Path:
    """Raíz de storage (p.ej. .../storage), padre de RAW_PATH."""
    return settings.raw_path_abs.parent


def resolver_directorio(tipo: str) -> Path:
    """Mapea el tipo de artefacto a su directorio base absoluto."""
    if tipo == "raw":
        return settings.raw_path_abs
    if tipo == "sav":
        return settings.sav_path_abs
    if tipo in ("metadata", "analysis"):
        return settings.json_path_abs
    if tipo == "temp":
        return settings.temp_path_abs
    raise TipoInvalidoError(f"Tipo de artefacto no soportado: {tipo}")


def _verificar_dentro_de_raiz(destino: Path) -> None:
    """Defensa path-traversal: destino debe quedar dentro de la raíz de storage."""
    root = _storage_root().resolve()
    try:
        resuelto = destino.resolve()
    except OSError as exc:  # pragma: no cover - resolución defensiva
        raise RutaInseguraError("Ruta de artefacto inválida.") from exc
    if root != resuelto and root not in resuelto.parents:
        raise RutaInseguraError("Ruta de artefacto fuera del almacenamiento.")


def ruta_de_key(tipo: str, key: str) -> Path:
    """Ruta absoluta de una key relativa (<tipo>/<id>/<version>__<slug>.<ext>)."""
    base_dir = resolver_directorio(tipo)
    # La key empieza por "<tipo>/..."; el resto cuelga del directorio base.
    resto = key.split("/", 1)[1] if "/" in key else key
    destino = base_dir / resto
    _verificar_dentro_de_raiz(destino)
    return destino


def guardar_bytes(destino: Path, contenido: bytes) -> None:
    """Escritura atómica de bytes (.part + replace)."""
    _verificar_dentro_de_raiz(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    try:
        tmp.write_bytes(contenido)
        tmp.replace(destino)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise StoreError("No se pudo almacenar el artefacto.") from exc


def guardar_json(destino: Path, contenido: dict[str, Any]) -> int:
    """Serializa y escribe un JSON de forma atómica. Devuelve el tamaño en bytes."""
    datos = json.dumps(contenido, ensure_ascii=False, indent=2).encode("utf-8")
    guardar_bytes(destino, datos)
    return len(datos)


def leer_json(ruta: Path) -> dict[str, Any]:
    """Lee y parsea un JSON almacenado. Corrupto -> StoreError."""
    try:
        texto = ruta.read_text(encoding="utf-8")
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise StoreError("El artefacto almacenado no es un JSON válido.") from exc
    except OSError as exc:
        raise StoreError("No se pudo almacenar el artefacto.") from exc
