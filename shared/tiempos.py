"""Tiempo de cómputo de cada paso del procesamiento de un instrumento (tabla `tiempo_proceso`).

Uso, en el servicio que hace el trabajo:

    with medir(db, id_crudo, "cleaning", "limpieza_automatica") as detalle:
        ...                       # el trabajo (incluido su commit)
        detalle["filas"] = 160    # datos opcionales para interpretar la duración

Solo se registra si el bloque termina bien: una operación que falla no deja una duración engañosa.
El registro es de mejor esfuerzo: si no se puede guardar, se anota en el log y la operación sigue.

Regla no obvia: el registro se hace con la MISMA sesión del servicio, al salir del bloque, cuando el
trabajo ya hizo su commit; así no hace falta otra conexión (las pruebas usan SQLite en memoria).
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("tiempos")


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # columnas TIMESTAMP en UTC, como el resto


def registrar(sesion: Any, id_crudo: int, servicio: str, paso: str, inicio: datetime, fin: datetime,
              duracion_ms: int, detalle: dict[str, Any] | None = None) -> None:
    """Guarda una fila de tiempo_proceso (nunca lanza)."""
    from shared.models.tiempo_proceso import TiempoProceso

    try:
        sesion.add(TiempoProceso(id_crudo=int(id_crudo), servicio=servicio, paso=paso, inicio=inicio, fin=fin,
                                 duracion_ms=int(duracion_ms), detalle=detalle or {}))
        sesion.commit()
    except Exception as exc:  # noqa: BLE001 — medir nunca rompe el procesamiento
        logger.warning("No se pudo registrar el tiempo de %s/%s (id_crudo=%s): %s", servicio, paso, id_crudo, exc)
        try:
            sesion.rollback()
        except Exception:  # noqa: BLE001
            pass


@contextmanager
def medir(sesion: Any, id_crudo: int | None, servicio: str, paso: str,
          detalle: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Mide el bloque y lo registra al terminar bien. `id_crudo` puede fijarse dentro del bloque."""
    extra: dict[str, Any] = dict(detalle or {})
    inicio, t0 = _ahora(), time.perf_counter()
    yield extra
    id_final = extra.pop("_id_crudo", None) or id_crudo
    if id_final is None:
        logger.warning("Tiempo de %s/%s sin id_crudo: no se registra.", servicio, paso)
        return
    registrar(sesion, id_final, servicio, paso, inicio, _ahora(), round((time.perf_counter() - t0) * 1000), extra)
