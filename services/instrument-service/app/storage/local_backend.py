"""Backend de almacenamiento LOCAL — PROVISIONAL.

⚠️  Implementación temporal mientras el **storage-service** no existe. Escribe los
    bytes en disco (`storage/raw`). Cuando el storage-service esté disponible, se
    creará un `HttpStorageBackend` que delegue en su API y se cambiará la fábrica
    en `app/storage/__init__.py`. Este archivo es la ÚNICA pieza que conoce el
    disco; el resto del servicio solo habla con `StoragePort`.

La escritura en disco aquí NO es una decisión de negocio del instrument-service:
es un detalle de infraestructura encapsulado tras el puerto, a la espera del
servicio que le corresponde esta tarea.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path

from shared.db.core.config import settings

from app.storage.port import StoragePort, StoredRef, StorageError

# Carpeta lógica dentro de storage/ donde viven los crudos ("storage/raw" -> "raw").
_RAW_SUBDIR = "raw"
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


class LocalStorageBackend(StoragePort):
    """Guarda archivos en el filesystem local (provisional)."""

    def guardar(self, content: bytes, nombre_original: str) -> StoredRef:
        unique_name = f"{uuid.uuid4().hex}__{_sanitize_filename(nombre_original)}"
        raw_dir = settings.raw_path_abs
        raw_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = raw_dir / unique_name

        # Escritura atómica: escribe a .part y renombra.
        tmp_path = absolute_path.with_suffix(absolute_path.suffix + ".part")
        try:
            tmp_path.write_bytes(content)
            tmp_path.replace(absolute_path)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise StorageError(f"No se pudo almacenar el archivo: {exc}") from exc

        return StoredRef(
            nombre_original=nombre_original,
            ruta=f"{_RAW_SUBDIR}/{unique_name}",
            size_bytes=len(content),
        )

    def eliminar(self, ruta: str) -> None:
        if not ruta:
            return
        storage_root = settings.raw_path_abs.parent
        target = (storage_root / ruta).resolve()
        # Defensa en profundidad: no borrar fuera de storage/.
        root = storage_root.resolve()
        if root not in target.parents and target != root:
            return
        Path(target).unlink(missing_ok=True)
