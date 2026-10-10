"""Gestión de archivos: ruteo por tipo, versionado, integridad y borrado.

Cada artefacto se guarda bajo una clave estable y versionada
`<tipo>/<instrumentoId>/<version>__<slug>` y se registra en un manifiesto JSON
(`<JSON_PATH>/_index/artefactos.json`) con su tamaño, nombre original, MIME y
SHA-256. La escritura es atómica (`.part` + `replace`) y toda mutación del
manifiesto se serializa con un lock de módulo.

El archivo crudo se guarda tal cual llega (bytes intactos); el SHA-256 permite
comprobar en cualquier momento que no cambió.

`resolver()` acepta tanto claves del manifiesto como rutas heredadas guardadas en
la BD (`raw/<uuid>__x.csv` del backend local, `storage/raw/inst_01.v1.json` del
seed de la demo) y siempre verifica que el destino quede DENTRO de la raíz de
storage (defensa contra path traversal).
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.db.core.config import settings

from services.cache_manager import cache

TIPOS_VALIDOS: frozenset[str] = frozenset({"raw", "clean", "sav", "metadata", "analysis", "temp"})

_MIME_EXTRA = {
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".json": "application/json",
    ".sav": "application/x-spss-sav",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}

# Prefijos que los backends ponen delante del nombre real ("3__" o "<uuid hex>__").
_PREFIJO_NOMBRE = re.compile(r"^(?:\d+|[0-9a-f]{32})__")
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

_lock = threading.RLock()


# ── Errores ────────────────────────────────────────────────────────────────────


class AlmacenamientoError(Exception):
    """Fallo de E/S al leer o escribir un artefacto."""


class TipoInvalidoError(Exception):
    """Tipo de artefacto no soportado."""


class RutaInseguraError(Exception):
    """La ruta resuelta queda fuera de la raíz de storage."""


class NoEncontradoError(Exception):
    """El artefacto o archivo no existe."""


class IndiceCorruptoError(Exception):
    """El manifiesto de artefactos no es un JSON válido."""


# ── Rutas ──────────────────────────────────────────────────────────────────────


def raiz() -> Path:
    """Raíz de storage (padre de RAW_PATH, p. ej. /app/storage)."""
    return settings.raw_path_abs.parent


def directorio(tipo: str) -> Path:
    """Directorio base absoluto de cada tipo de artefacto."""
    if tipo == "raw":
        return settings.raw_path_abs
    if tipo == "clean":
        return settings.clean_path_abs
    if tipo == "sav":
        return settings.sav_path_abs
    if tipo in ("metadata", "analysis"):
        return settings.json_path_abs
    if tipo == "temp":
        return settings.temp_path_abs
    raise TipoInvalidoError(f"Tipo de artefacto no soportado: {tipo}")


def preparar_directorios() -> None:
    for tipo in ("raw", "clean", "sav", "metadata", "temp"):
        directorio(tipo).mkdir(parents=True, exist_ok=True)
    _ruta_manifiesto().parent.mkdir(parents=True, exist_ok=True)


def _verificar_dentro_de_raiz(destino: Path) -> Path:
    base = raiz().resolve()
    try:
        resuelto = destino.resolve()
    except OSError as exc:  # pragma: no cover - resolución defensiva
        raise RutaInseguraError("Ruta de artefacto inválida.") from exc
    if resuelto != base and base not in resuelto.parents:
        raise RutaInseguraError("Ruta de artefacto fuera del almacenamiento.")
    return resuelto


def ruta_relativa(ruta_abs: Path) -> str:
    try:
        return str(ruta_abs.resolve().relative_to(raiz().resolve())).replace("\\", "/")
    except ValueError:
        return str(ruta_abs)


def slug(nombre: str | None) -> str:
    """Nombre de archivo seguro preservando la extensión."""
    base = Path(nombre or "archivo").name
    raiz_nombre = Path(base).stem
    extension = Path(base).suffix.lower()
    ascii_ = unicodedata.normalize("NFKD", raiz_nombre).encode("ascii", "ignore").decode("ascii")
    seguro = _SAFE_CHARS.sub("_", ascii_).strip("._-") or "archivo"
    return f"{seguro[:120]}{extension}"


def mime_de(nombre: str) -> str:
    extension = Path(nombre).suffix.lower()
    return _MIME_EXTRA.get(extension) or mimetypes.guess_type(nombre)[0] or "application/octet-stream"


def nombre_legible(path: Path) -> str:
    """Nombre del archivo sin el prefijo de versión/uuid que añade el backend."""
    return _PREFIJO_NOMBRE.sub("", path.name)


def sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


# ── Manifiesto ─────────────────────────────────────────────────────────────────


def _ruta_manifiesto() -> Path:
    return settings.json_path_abs / "_index" / "artefactos.json"


def _leer_manifiesto() -> list[dict[str, Any]]:
    ruta = _ruta_manifiesto()
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IndiceCorruptoError("Índice de artefactos corrupto.") from exc
    if not isinstance(datos, list):
        raise IndiceCorruptoError("Índice de artefactos corrupto.")
    return datos


def _escribir_manifiesto(entradas: list[dict[str, Any]]) -> None:
    ruta = _ruta_manifiesto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".part")
    tmp.write_text(json.dumps(entradas, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ruta)


def _escribir_atomico(destino: Path, contenido: bytes) -> None:
    _verificar_dentro_de_raiz(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    try:
        tmp.write_bytes(contenido)
        tmp.replace(destino)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise AlmacenamientoError("No se pudo almacenar el artefacto.") from exc


def _ruta_de_key(tipo: str, key: str) -> Path:
    resto = key.split("/", 1)[1] if "/" in key else key
    return directorio(tipo) / resto


# ── API del módulo ─────────────────────────────────────────────────────────────


def guardar(
    tipo: str,
    instrumento_id: str | None,
    nombre_original: str,
    contenido: bytes,
    *,
    nombre_archivo: str | None = None,
) -> dict[str, Any]:
    """Guarda `contenido` como nueva versión de (tipo, instrumentoId)."""
    if tipo not in TIPOS_VALIDOS:
        raise TipoInvalidoError(f"Tipo de artefacto no soportado: {tipo}")
    instrumento = (instrumento_id or "").strip() or "_"
    nombre_seguro = slug(nombre_archivo or nombre_original)

    with _lock:
        entradas = _leer_manifiesto()
        versiones = [
            e.get("version", 0)
            for e in entradas
            if e.get("tipo") == tipo and e.get("instrumentoId") == instrumento
        ]
        version = (max(versiones) + 1) if versiones else 1
        key = f"{tipo}/{instrumento}/{version}__{nombre_seguro}"
        destino = _ruta_de_key(tipo, key)
        _escribir_atomico(destino, contenido)

        entrada = {
            "key": key,
            "tipo": tipo,
            "instrumentoId": instrumento,
            "version": version,
            "ruta_absoluta": str(destino),
            "ruta_relativa": ruta_relativa(destino),
            "size_bytes": len(contenido),
            "nombre_original": nombre_original,
            "creado": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256(contenido),
            "mime_type": mime_de(nombre_original or nombre_seguro),
        }
        entradas.append(entrada)
        _escribir_manifiesto(entradas)
    cache.invalidar(f"art:{tipo}:{instrumento}")
    return entrada


def guardar_json(
    tipo: str, instrumento_id: str, contenido: dict[str, Any], nombre: str | None = None
) -> dict[str, Any]:
    """Serializa y guarda un JSON (metadata | analysis)."""
    nombre_base = slug(nombre or "instrumento")
    if not nombre_base.lower().endswith(".json"):
        nombre_base = f"{Path(nombre_base).stem}.json"
    datos = json.dumps(contenido, ensure_ascii=False, indent=2).encode("utf-8")
    return guardar(tipo, instrumento_id, nombre or nombre_base, datos, nombre_archivo=nombre_base)


def listar(*, instrumento_id: str | None = None, tipo: str | None = None) -> list[dict[str, Any]]:
    entradas = _leer_manifiesto()
    if instrumento_id is not None:
        entradas = [e for e in entradas if e.get("instrumentoId") == instrumento_id]
    if tipo is not None:
        entradas = [e for e in entradas if e.get("tipo") == tipo]
    return entradas


def obtener(tipo: str, instrumento_id: str, version: int | None = None) -> dict[str, Any] | None:
    """Entrada de (tipo, instrumentoId); sin versión devuelve la más reciente."""
    candidatas = listar(instrumento_id=instrumento_id, tipo=tipo)
    if version is not None:
        return next((e for e in candidatas if e.get("version") == version), None)
    return max(candidatas, key=lambda e: e.get("version", 0)) if candidatas else None


def buscar_por_key(key: str) -> dict[str, Any] | None:
    return next((e for e in _leer_manifiesto() if e.get("key") == key), None)


@dataclass
class Archivo:
    path: Path
    contenido: bytes
    nombre: str
    mime_type: str
    sha256: str
    entrada: dict[str, Any] | None


def resolver(ruta_o_key: str) -> tuple[Path, dict[str, Any] | None]:
    """Ruta absoluta segura de una clave del manifiesto o de una ruta heredada."""
    valor = (ruta_o_key or "").strip().replace("\\", "/")
    if not valor:
        raise NoEncontradoError("Ruta vacía.")

    entrada = buscar_por_key(valor)
    if entrada is not None:
        return _verificar_dentro_de_raiz(_ruta_de_key(entrada["tipo"], entrada["key"])), entrada

    candidatos: list[Path] = []
    p = Path(valor)
    if p.is_absolute():
        candidatos.append(p)
    else:
        relativo = valor.lstrip("/")
        candidatos.append(raiz() / relativo)
        if relativo.startswith("storage/"):
            candidatos.append(raiz() / relativo[len("storage/"):])
        candidatos.append(settings.PROJECT_ROOT / relativo)

    for candidato in candidatos:
        try:
            seguro = _verificar_dentro_de_raiz(candidato)
        except RutaInseguraError:
            continue
        if seguro.is_file():
            # Si la ruta corresponde a un artefacto registrado, devolver su entrada.
            relativo = ruta_relativa(seguro)
            entrada = next(
                (e for e in _leer_manifiesto() if e.get("ruta_relativa") == relativo), None
            )
            return seguro, entrada

    # Ningún candidato existe: distinguir "fuera de la raíz" de "no existe".
    if all(_fuera_de_raiz(c) for c in candidatos):
        raise RutaInseguraError("Ruta de artefacto fuera del almacenamiento.")
    raise NoEncontradoError("Archivo no encontrado en el almacenamiento.")


def _fuera_de_raiz(path: Path) -> bool:
    try:
        _verificar_dentro_de_raiz(path)
    except RutaInseguraError:
        return True
    return False


def leer(ruta_o_key: str) -> Archivo:
    """Lee los bytes de un archivo almacenado junto con su nombre, MIME y huella."""
    path, entrada = resolver(ruta_o_key)
    try:
        contenido = path.read_bytes()
    except FileNotFoundError as exc:
        raise NoEncontradoError("Archivo no encontrado en el almacenamiento.") from exc
    except OSError as exc:
        raise AlmacenamientoError("No se pudo leer el artefacto.") from exc
    nombre = (entrada or {}).get("nombre_original") or nombre_legible(path)
    return Archivo(
        path=path,
        contenido=contenido,
        nombre=nombre,
        mime_type=(entrada or {}).get("mime_type") or mime_de(nombre),
        sha256=sha256(contenido),
        entrada=entrada,
    )


def leer_json(entrada: dict[str, Any]) -> dict[str, Any]:
    """Contenido de un artefacto JSON (con caché por clave)."""
    clave_cache = f"art:{entrada['tipo']}:{entrada['instrumentoId']}:{entrada['key']}"
    en_cache = cache.get(clave_cache)
    if en_cache is not None:
        return en_cache
    path = _ruta_de_key(entrada["tipo"], entrada["key"])
    try:
        datos = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NoEncontradoError("Artefacto no encontrado.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AlmacenamientoError("El artefacto almacenado no es un JSON válido.") from exc
    if not isinstance(datos, dict):
        raise AlmacenamientoError("El artefacto almacenado no es un objeto JSON.")
    cache.set(clave_cache, datos)
    return datos


def eliminar(ruta_o_key: str) -> bool:
    """Elimina un archivo (y su entrada del manifiesto). Idempotente."""
    try:
        path, entrada = resolver(ruta_o_key)
    except NoEncontradoError:
        # Puede quedar una entrada huérfana en el manifiesto: limpiarla.
        with _lock:
            entradas = _leer_manifiesto()
            restantes = [e for e in entradas if e.get("key") != ruta_o_key]
            if len(restantes) != len(entradas):
                _escribir_manifiesto(restantes)
                return True
        return False

    with _lock:
        path.unlink(missing_ok=True)
        if entrada is not None:
            entradas = _leer_manifiesto()
            _escribir_manifiesto([e for e in entradas if e.get("key") != entrada["key"]])
            cache.invalidar(f"art:{entrada['tipo']}:{entrada['instrumentoId']}")
    return True


def purgar_instrumento(instrumento_id: str) -> int:
    """Elimina TODOS los artefactos registrados de un instrumento."""
    eliminados = 0
    for entrada in listar(instrumento_id=instrumento_id):
        if eliminar(entrada["key"]):
            eliminados += 1
    cache.invalidar("art:")
    return eliminados


def estadisticas() -> dict[str, Any]:
    por_tipo: dict[str, dict[str, int]] = {t: {"n_artefactos": 0, "bytes": 0} for t in sorted(TIPOS_VALIDOS)}
    for entrada in _leer_manifiesto():
        datos = por_tipo.setdefault(entrada.get("tipo", "?"), {"n_artefactos": 0, "bytes": 0})
        datos["n_artefactos"] += 1
        datos["bytes"] += int(entrada.get("size_bytes") or 0)
    return {
        "por_tipo": por_tipo,
        "total_artefactos": sum(d["n_artefactos"] for d in por_tipo.values()),
        "total_bytes": sum(d["bytes"] for d in por_tipo.values()),
        "cache": cache.estadisticas(),
    }
