"""Almacenamiento de archivos crudos (RAW DATA).

Responsabilidad única: persistir en disco los bytes de un archivo subido dentro
de `storage/raw`, con un nombre único y seguro, y devolver la ruta RELATIVA que
se guarda en la columna correspondiente de `raw_data`.

Convención de rutas en BD
--------------------------
Guardamos rutas RELATIVAS a la raíz de storage (p. ej. "raw/<uuid>__<nombre>.csv")
en lugar de rutas absolutas. Así el registro es portable entre entornos
(local vs. contenedor, donde storage se monta en /app/storage). Para operar
sobre el archivo se reconstruye con `settings.raw_path_abs` / la raíz de storage.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

from shared.db.core.config import settings

# Carpeta lógica dentro de storage/ donde viven los crudos. Debe coincidir con
# el último segmento de settings.RAW_PATH ("storage/raw" -> "raw").
_RAW_SUBDIR = "raw"

# Caracteres permitidos en el nombre saneado (sin la extensión).
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class StoredFile:
    """Resultado de almacenar un archivo.

    Attributes:
        original_name: Nombre original tal como lo subió el usuario.
        stored_name:   Nombre único con el que se guardó en disco.
        relative_path: Ruta relativa a la raíz de storage (lo que va a la BD).
        absolute_path: Ruta absoluta en disco (para operaciones locales).
        size_bytes:    Tamaño del archivo escrito.
    """

    original_name: str
    stored_name: str
    relative_path: str
    absolute_path: Path
    size_bytes: int


def _sanitize_filename(filename: str) -> str:
    """Normaliza y sanea un nombre de archivo preservando su extensión.

    - Toma solo el nombre base (descarta cualquier componente de ruta).
    - Translitera a ASCII y reemplaza caracteres no seguros por "_".
    - Evita nombres vacíos.
    """
    base = Path(filename).name  # descarta "../", separadores, etc.
    stem = Path(base).stem
    suffix = Path(base).suffix.lower()

    # Transliterar acentos/unicode a ASCII.
    stem_ascii = (
        unicodedata.normalize("NFKD", stem)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    stem_safe = _SAFE_CHARS.sub("_", stem_ascii).strip("._-")
    if not stem_safe:
        stem_safe = "archivo"

    # Limitar longitud del stem para no exceder límites del sistema de archivos.
    stem_safe = stem_safe[:120]
    return f"{stem_safe}{suffix}"


def _raw_dir() -> Path:
    """Devuelve (creándolo si falta) el directorio absoluto storage/raw."""
    raw_dir = settings.raw_path_abs
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def save(content: bytes, original_filename: str) -> StoredFile:
    """Guarda `content` en storage/raw con un nombre único y seguro.

    Args:
        content:           Bytes del archivo a persistir.
        original_filename: Nombre original (para derivar el nombre y la extensión).

    Returns:
        StoredFile con la ruta relativa (para BD) y la absoluta (para disco).

    Raises:
        OSError: si falla la escritura en disco.
    """
    safe_name = _sanitize_filename(original_filename)
    unique_name = f"{uuid.uuid4().hex}__{safe_name}"

    raw_dir = _raw_dir()
    absolute_path = raw_dir / unique_name

    # Escritura atómica: primero a un .part y luego rename.
    tmp_path = absolute_path.with_suffix(absolute_path.suffix + ".part")
    try:
        tmp_path.write_bytes(content)
        tmp_path.replace(absolute_path)
    except OSError:
        # Limpieza de parcial si algo falló.
        tmp_path.unlink(missing_ok=True)
        raise

    relative_path = f"{_RAW_SUBDIR}/{unique_name}"
    return StoredFile(
        original_name=original_filename,
        stored_name=unique_name,
        relative_path=relative_path,
        absolute_path=absolute_path,
        size_bytes=len(content),
    )


def delete(relative_path: str) -> None:
    """Elimina un archivo previamente almacenado (para rollback).

    Acepta la ruta relativa a storage (lo que se guardó en BD). No falla si el
    archivo ya no existe.
    """
    if not relative_path:
        return
    # La raíz de storage es el padre de storage/raw.
    storage_root = settings.raw_path_abs.parent
    target = (storage_root / relative_path).resolve()

    # Defensa en profundidad: no borrar fuera de storage/.
    storage_root_resolved = storage_root.resolve()
    if storage_root_resolved not in target.parents and target != storage_root_resolved:
        return
    Path(target).unlink(missing_ok=True)
