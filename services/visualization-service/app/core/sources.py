"""Obtención de contenido y metadata de instrumentos para el RAG (diseño §4.2).

`resolver_artefacto(instrumentoId)` localiza el JSON del instrumento (clave =
`str(id_crudo)`, §2.1) en este orden (§2.8 (b)):

  1. storage-service: GET {STORAGE_SERVICE_URL}/almacenamiento/artefacto/analysis/<id>
     y, si falta, .../metadata/<id>. La base se lee con
     `os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004")` — NUNCA
     vía `settings` (AppSettings NO define STORAGE_SERVICE_URL; con
     `extra="ignore"` pydantic lo descartaría y daría AttributeError).
  2. `instrumento_procesado.ruta_json` si hay BD disponible vía `shared`.
  3. Fallback a `storage/raw/inst_<NN>.v*.json`: traduce `id_crudo -> inst_XX`
     por `_seed_map.json` o por el mapeo directo `N -> inst_{N:02d}`, y abre la
     última versión (`glob`), bajo `settings.raw_path_abs`.

`extraer_texto(json)` concatena título + objetivo + dimensiones + preguntas con
sus opciones (fallback a `dc:description`). `extraer_metadata(json, id)` devuelve
`{instrumentoId, titulo, tipo (mapeado §2.4), investigador, kpis}`.

NOTA (Chroma): `kpis` es una lista, pero la metadata de Chroma solo acepta
escalares; el router serializa `kpis` a string JSON al hacer upsert (§4.6) y lo
deserializa al construir `FuenteChatOut`. Aquí `kpis` se devuelve como lista.
"""
from __future__ import annotations

import json as jsonlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_SEED_MAP_NOMBRE = "_seed_map.json"
_STORAGE_DEFAULT = "http://storage-service:8004"

# ── Mapeo canónico de tipo backend -> frontend (§2.4) ────────────────────────
_TIPO_MAP: dict[str, str] = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_TIPO_DEFAULT = "Encuesta"


def _como_dict(valor: Any) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def _como_lista(valor: Any) -> list[Any]:
    return valor if isinstance(valor, list) else []


def _texto(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


# ── (1) storage-service ───────────────────────────────────────────────────────
async def _resolver_desde_storage(instrumento_id: str) -> dict[str, Any] | None:
    """GET analysis/<id> y, si falta, metadata/<id> del storage-service."""
    base = os.getenv("STORAGE_SERVICE_URL", _STORAGE_DEFAULT).rstrip("/")
    for tipo in ("analysis", "metadata"):
        url = f"{base}/almacenamiento/artefacto/{tipo}/{instrumento_id}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as cliente:
                resp = await cliente.get(url)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("storage-service no disponible (%s): %s", url, exc)
            return None
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            logger.warning("storage-service respondió %s en %s", resp.status_code, url)
            continue
        try:
            detalle = resp.json()
        except ValueError:
            continue
        contenido = _como_dict(detalle).get("contenido")
        if isinstance(contenido, dict) and contenido:
            return contenido
    return None


# ── (2) BD: instrumento_procesado.ruta_json ────────────────────────────────────
def _resolver_desde_bd(instrumento_id: str) -> dict[str, Any] | None:
    """Lee `instrumento_procesado.ruta_json` por `id_crudo` si hay BD."""
    try:
        id_crudo = int(instrumento_id)
    except (TypeError, ValueError):
        return None
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from shared.models.instrumento_procesado import InstrumentoProcesado
    except Exception as exc:  # pragma: no cover - sin BD/driver disponible
        logger.debug("BD no disponible para resolución: %s", exc)
        return None
    try:
        engine = create_engine(settings.DATABASE_URL)
        with Session(engine) as sesion:
            procesado = sesion.scalar(
                select(InstrumentoProcesado).where(
                    InstrumentoProcesado.id_crudo == id_crudo
                )
            )
            ruta_json = getattr(procesado, "ruta_json", None) if procesado else None
    except Exception as exc:  # pragma: no cover - Postgres caído
        logger.debug("No se pudo consultar la BD: %s", exc)
        return None
    if not ruta_json:
        return None
    ruta = Path(ruta_json)
    if not ruta.is_absolute():
        ruta = settings.PROJECT_ROOT / ruta_json
    return _leer_json(ruta) if ruta.is_file() else None


# ── (3) Fallback a storage/raw ─────────────────────────────────────────────────
def _leer_json(ruta: Path) -> dict[str, Any] | None:
    try:
        with ruta.open("r", encoding="utf-8") as fh:
            data = jsonlib.load(fh)
    except (OSError, jsonlib.JSONDecodeError) as exc:
        logger.warning("No se pudo leer el JSON %s: %s", ruta, exc)
        return None
    return data if isinstance(data, dict) else None


def _cargar_seed_map() -> dict[str, int]:
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
    seed_map = _cargar_seed_map()
    for inst, cid in seed_map.items():
        if cid == id_crudo:
            return inst
    if id_crudo >= 1:
        return f"inst_{id_crudo:02d}"
    return None


def _resolver_fallback_raw(instrumento_id: str) -> dict[str, Any] | None:
    try:
        id_crudo = int(instrumento_id)
    except (TypeError, ValueError):
        return None
    slug = _slug_por_id_crudo(id_crudo)
    if slug is None:
        return None
    candidatos = sorted(settings.raw_path_abs.glob(f"{slug}.v*.json"))
    if not candidatos:
        logger.debug("Sin artefacto en storage/raw para %s", slug)
        return None
    return _leer_json(candidatos[-1])


async def resolver_artefacto(instrumento_id: str) -> dict[str, Any] | None:
    """Resuelve el JSON del instrumento en el orden §2.8 (b).

    Devuelve el `dict` del JSON o `None` si ninguna fuente lo resuelve.
    """
    desde_storage = await _resolver_desde_storage(instrumento_id)
    if desde_storage is not None:
        return desde_storage
    desde_bd = _resolver_desde_bd(instrumento_id)
    if desde_bd is not None:
        return desde_bd
    return _resolver_fallback_raw(instrumento_id)


# ── Extracción de texto y metadata ─────────────────────────────────────────────
def extraer_texto(instrumento_json: dict[str, Any] | None) -> str:
    """Texto a indexar: título + objetivo + dimensiones + preguntas/opciones.

    Fallback si `instrument` falta: `metadata.dublin_core["dc:description"]`.
    """
    data = _como_dict(instrumento_json)
    instrumento = _como_dict(data.get("instrument"))

    partes: list[str] = []
    titulo = _texto(instrumento.get("title"))
    if titulo:
        partes.append(titulo)
    objetivo = _texto(instrumento.get("objective"))
    if objetivo:
        partes.append(objetivo)

    dimensiones = [_texto(d) for d in _como_lista(instrumento.get("dimensions_explored"))]
    dimensiones = [d for d in dimensiones if d]
    if dimensiones:
        partes.append("\n".join(dimensiones))

    for seccion in _como_lista(instrumento.get("sections")):
        for pregunta in _como_lista(_como_dict(seccion).get("questions")):
            pregunta = _como_dict(pregunta)
            bloque: list[str] = []
            texto_q = _texto(pregunta.get("text"))
            if texto_q:
                bloque.append(texto_q)
            opciones = [_texto(o) for o in _como_lista(pregunta.get("options"))]
            opciones = [o for o in opciones if o]
            if opciones:
                bloque.append("\n".join(opciones))
            if bloque:
                partes.append("\n".join(bloque))

    if not partes:
        metadata = _como_dict(data.get("metadata"))
        dublin_core = _como_dict(metadata.get("dublin_core"))
        descripcion = _texto(dublin_core.get("dc:description"))
        if descripcion:
            partes.append(descripcion)

    return "\n\n".join(partes)


def _mapear_tipo(tipo_raw: str | None) -> str:
    clave = (tipo_raw or "").strip().lower()
    tipo = _TIPO_MAP.get(clave)
    if tipo is None:
        if clave:
            logger.warning("tipo desconocido %r; se mapea a %r.", tipo_raw, _TIPO_DEFAULT)
        return _TIPO_DEFAULT
    return tipo


def extraer_kpis(instrumento_json: dict[str, Any] | None) -> list[str]:
    """KPIs = `design_reference.kpi_hints` (lista de str)."""
    data = _como_dict(instrumento_json)
    design = _como_dict(data.get("design_reference"))
    return [str(k) for k in _como_lista(design.get("kpi_hints")) if _texto(k)]


def extraer_metadata(
    instrumento_json: dict[str, Any] | None, instrumento_id: str
) -> dict[str, Any]:
    """Metadata del instrumento para Chroma / FuenteChatOut (§4.2).

    Devuelve `{instrumentoId, titulo, tipo (mapeado), investigador, kpis}`.
    `tipo` se infiere de `metadata.dublin_core["dc:type"]` solo de forma
    informativa; el esquema real no trae el tipo canónico de `raw_data`, así que
    si no mapea cae al default "Encuesta" (§2.4). `kpis` es lista (el router la
    serializa a JSON string para la metadata de Chroma).
    """
    data = _como_dict(instrumento_json)
    instrumento = _como_dict(data.get("instrument"))
    metadata = _como_dict(data.get("metadata"))
    dublin_core = _como_dict(metadata.get("dublin_core"))

    titulo = (
        _texto(instrumento.get("title"))
        or _texto(dublin_core.get("dc:title"))
        or f"Instrumento {instrumento_id}"
    )
    investigador = _texto(dublin_core.get("dc:creator"))

    return {
        "instrumentoId": instrumento_id,
        "titulo": titulo,
        "tipo": _mapear_tipo(dublin_core.get("dc:type")),
        "investigador": investigador,
        "kpis": extraer_kpis(data),
    }
