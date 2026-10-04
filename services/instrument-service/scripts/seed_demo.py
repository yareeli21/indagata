"""Seed idempotente de la demo (diseño §2.8 (a)).

Por cada `storage/raw/inst_XX.v1.json` asegura:
  1. una fila `raw_data`  (id_owner=settings.DEV_USER_ID, tipo_instrumento="encuesta",
     nombre_archivo="inst_XX.v1.json", rutas apuntando al archivo);
  2. su `instrumento_procesado` (estado="estandarizado",
     ruta_json="storage/raw/inst_XX.v1.json").
Persiste el mapeo `inst_XX -> id_crudo` en `storage/raw/_seed_map.json`.

Idempotente: si `inst_XX` ya está mapeado (y su fila existe), no duplica.
Usa los modelos ORM de `shared` (schema tt_rag), NO SQL crudo contra public.

NO forma parte del runtime de los servicios: es parte de la EJECUCIÓN de la
demo y requiere Postgres levantado (`docker compose up -d postgres`).

Ejecutar desde la carpeta del servicio:
    python scripts/seed_demo.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

# ── Resolver import de `shared` también en ejecución local ────────────────────
# scripts/seed_demo.py -> parents[3] = raíz del repo (donde vive `shared/`).
if not (Path(__file__).resolve().parents[1] / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from shared.db.core.config import settings  # noqa: E402
from shared.db.session import SessionLocal  # noqa: E402
from shared.models.instrumento_procesado import InstrumentoProcesado  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_demo")

_SEED_MAP_NOMBRE = "_seed_map.json"
# Nombre canónico de los artefactos de la demo: inst_01.v1.json … inst_21.v1.json.
_PATRON_INST = re.compile(r"^inst_(\d{2})\.v1\.json$")


def _cargar_seed_map(ruta: Path) -> dict[str, int]:
    """Lee `_seed_map.json` (`{"inst_01": 1, ...}`) o {} si no existe/corrupto."""
    if not ruta.is_file():
        return {}
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo leer %s (%s); se regenera.", ruta, exc)
        return {}
    if not isinstance(data, dict):
        return {}
    mapa: dict[str, int] = {}
    for clave, valor in data.items():
        try:
            mapa[str(clave)] = int(valor)
        except (TypeError, ValueError):
            continue
    return mapa


def _guardar_seed_map(ruta: Path, mapa: dict[str, int]) -> None:
    """Escritura atómica (.part + replace) del manifiesto."""
    tmp = ruta.with_suffix(ruta.suffix + ".part")
    ordenado = {inst: mapa[inst] for inst in sorted(mapa)}
    tmp.write_text(json.dumps(ordenado, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ruta)


def main() -> int:
    raw_dir = settings.raw_path_abs
    archivos = sorted(p for p in raw_dir.glob("inst_*.v1.json") if _PATRON_INST.match(p.name))
    if not archivos:
        logger.warning("No se encontraron artefactos inst_XX.v1.json en %s", raw_dir)
        return 0

    seed_map_path = raw_dir / _SEED_MAP_NOMBRE
    seed_map = _cargar_seed_map(seed_map_path)

    nuevos = 0
    db = SessionLocal()
    try:
        for archivo in archivos:
            inst = archivo.stem.split(".", 1)[0]  # "inst_01.v1" -> "inst_01"
            ruta_rel = f"storage/raw/{archivo.name}"

            # Idempotencia: si ya está mapeado y la fila existe, no se duplica.
            id_crudo = seed_map.get(inst)
            if id_crudo is not None and db.get(RawData, id_crudo) is not None:
                continue

            raw = RawData(
                id_owner=settings.DEV_USER_ID,
                tipo_instrumento="encuesta",
                nombre_archivo=archivo.name,
                raw_archivo=ruta_rel,
                raw_archivo_original=ruta_rel,
            )
            db.add(raw)
            db.flush()  # obtiene raw.id_crudo

            procesado = InstrumentoProcesado(
                id_crudo=raw.id_crudo,
                estado="estandarizado",
                ruta_json=ruta_rel,
            )
            db.add(procesado)
            db.commit()

            seed_map[inst] = raw.id_crudo
            nuevos += 1
            logger.info("Sembrado %s -> id_crudo=%s", inst, raw.id_crudo)
    except Exception:  # noqa: BLE001  (en seed se re-lanza tras rollback)
        db.rollback()
        logger.exception("Fallo al sembrar la demo; se revierte la transacción.")
        raise
    finally:
        db.close()

    _guardar_seed_map(seed_map_path, seed_map)
    logger.info(
        "Seed completo: %d nuevos, %d en total en %s",
        nuevos,
        len(seed_map),
        seed_map_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
