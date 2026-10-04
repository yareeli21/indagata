"""Resolución del JSON del instrumento por `id_crudo` (diseño §2.8 (b)).

Orden de resolución (sin requerir storage-service corriendo):
  1. `instrumento_procesado.ruta_json` si el archivo existe en disco.
  2. Fallback a `storage/raw/`: traducir `id_crudo -> inst_XX` por el manifiesto
     `_seed_map.json` (si existe) o por el mapeo directo `N -> inst_{N:02d}`, y
     abrir la última versión con `glob("inst_<NN>.v*.json")` bajo
     `settings.raw_path_abs`.

Devuelve el `dict` del JSON o `None` si no se puede resolver. Lectura
defensiva: cualquier error de E/S o de parseo se registra y devuelve `None`.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from shared.db.core.config import settings

logger = logging.getLogger(__name__)

_SEED_MAP_NOMBRE = "_seed_map.json"


def _leer_json(ruta: Path) -> dict[str, Any] | None:
    """Carga un JSON como dict; None ante error o si no es objeto."""
    try:
        with ruta.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo leer el JSON %s: %s", ruta, exc)
        return None
    if not isinstance(data, dict):
        logger.warning("El JSON %s no es un objeto.", ruta)
        return None
    return data


def _resolver_por_ruta_json(procesado: Any) -> dict[str, Any] | None:
    """(1) Carga `procesado.ruta_json` si existe en disco."""
    if procesado is None:
        return None
    ruta_json = getattr(procesado, "ruta_json", None)
    if not ruta_json:
        return None
    ruta = Path(ruta_json)
    if not ruta.is_absolute():
        ruta = settings.PROJECT_ROOT / ruta_json
    if not ruta.is_file():
        logger.debug("ruta_json no existe en disco: %s", ruta)
        return None
    return _leer_json(ruta)


def _cargar_seed_map() -> dict[str, int]:
    """Lee `storage/raw/_seed_map.json` (`{"inst_01": 1, ...}`) o {}."""
    ruta = settings.raw_path_abs / _SEED_MAP_NOMBRE
    data = _leer_json(ruta) if ruta.is_file() else None
    if not data:
        return {}
    mapa: dict[str, int] = {}
    for clave, valor in data.items():
        try:
            mapa[str(clave)] = int(valor)
        except (TypeError, ValueError):
            continue
    return mapa


def _slug_por_id_crudo(id_crudo: int) -> str | None:
    """Traduce `id_crudo -> inst_XX` por _seed_map.json o `N -> inst_{N:02d}`."""
    seed_map = _cargar_seed_map()
    for inst, cid in seed_map.items():
        if cid == id_crudo:
            return inst
    if id_crudo >= 1:
        return f"inst_{id_crudo:02d}"
    return None


def _resolver_fallback_raw(id_crudo: int) -> dict[str, Any] | None:
    """(2) Fallback a `storage/raw/inst_<NN>.v*.json` (última versión)."""
    slug = _slug_por_id_crudo(id_crudo)
    if slug is None:
        return None
    candidatos = sorted(settings.raw_path_abs.glob(f"{slug}.v*.json"))
    if not candidatos:
        logger.debug("Sin artefacto en storage/raw para %s", slug)
        return None
    # `sorted` deja la última versión al final (v1 < v2 < ... lexicográfico).
    return _leer_json(candidatos[-1])


def resolver_json_por_id_crudo(
    id_crudo: int, procesado: Any = None
) -> dict[str, Any] | None:
    """Resuelve el JSON del instrumento en el orden §2.8 (b).

    Args:
        id_crudo:  PK de `raw_data` (= id canónico del instrumento).
        procesado: fila `InstrumentoProcesado` opcional (para `ruta_json`).

    Returns:
        dict del JSON o None si no se pudo resolver.
    """
    desde_ruta = _resolver_por_ruta_json(procesado)
    if desde_ruta is not None:
        return desde_ruta
    return _resolver_fallback_raw(id_crudo)
