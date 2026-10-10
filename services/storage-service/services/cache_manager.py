"""Caché en proceso y mantenimiento de archivos temporales.

- `CacheTTL`: caché LRU con expiración, thread-safe. El storage-service la usa
  para no re-parsear el mismo archivo (tablas/texto) ni releer JSON en cada
  petición. Las claves incluyen la huella del archivo (sha256 o mtime), de modo
  que una nueva versión nunca devuelve contenido viejo; aun así, toda mutación
  invalida por prefijo.
- `limpiar_temporales`: borra los artefactos `temp` más viejos que N horas.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class CacheTTL:
    """Caché LRU con TTL por entrada."""

    def __init__(self, max_entradas: int = 256, ttl_segundos: float = 600.0) -> None:
        self._max = max_entradas
        self._ttl = ttl_segundos
        self._datos: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._aciertos = 0
        self._fallos = 0

    def get(self, clave: str) -> Any | None:
        with self._lock:
            entrada = self._datos.get(clave)
            if entrada is None:
                self._fallos += 1
                return None
            expira, valor = entrada
            if expira < time.monotonic():
                del self._datos[clave]
                self._fallos += 1
                return None
            self._datos.move_to_end(clave)
            self._aciertos += 1
            return valor

    def set(self, clave: str, valor: Any) -> None:
        with self._lock:
            self._datos[clave] = (time.monotonic() + self._ttl, valor)
            self._datos.move_to_end(clave)
            while len(self._datos) > self._max:
                self._datos.popitem(last=False)

    def invalidar(self, prefijo: str = "") -> int:
        """Elimina las entradas cuya clave empieza por `prefijo` ('' = todas)."""
        with self._lock:
            claves = [c for c in self._datos if c.startswith(prefijo)]
            for c in claves:
                del self._datos[c]
            return len(claves)

    def estadisticas(self) -> dict[str, int]:
        with self._lock:
            return {
                "entradas": len(self._datos),
                "aciertos": self._aciertos,
                "fallos": self._fallos,
            }


# Caché única del proceso.
cache = CacheTTL()


def limpiar_temporales(max_edad_horas: float = 24.0) -> int:
    """Elimina los artefactos `temp` con más de `max_edad_horas`. Devuelve cuántos."""
    from datetime import datetime, timedelta, timezone

    from services import file_manager

    limite = datetime.now(timezone.utc) - timedelta(hours=max_edad_horas)
    eliminados = 0
    for entrada in file_manager.listar(tipo="temp"):
        try:
            creado = datetime.fromisoformat(entrada["creado"])
        except (KeyError, ValueError):
            continue
        if creado.tzinfo is None:
            creado = creado.replace(tzinfo=timezone.utc)
        if creado < limite and file_manager.eliminar(entrada["key"]):
            eliminados += 1
    return eliminados
