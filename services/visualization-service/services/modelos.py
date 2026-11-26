"""Catálogo de modelos del chat (`config/modelos.yaml`) y el modelo de la consulta en curso (26 nov 2026).

El modelo que elige la página se fija al empezar la consulta (`usar`) y lo leen todas las etapas que llaman a Ollama
(interpretación, clasificadores, redacción) con `en_curso`; antes solo la redacción lo usaba. Los parámetros de
Ollama de cada modelo salen del catálogo (`parametros`).
"""
from __future__ import annotations

from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from shared.db.core.config import settings

_RUTA = Path(__file__).resolve().parents[1] / "config" / "modelos.yaml"
_EN_CURSO: ContextVar[str | None] = ContextVar("modelo_en_curso", default=None)


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    try:
        return yaml.safe_load(_RUTA.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def catalogo() -> list[dict[str, Any]]:
    """Modelos elegibles, con el predeterminado (OLLAMA_MODEL) primero aunque no esté en el archivo."""
    modelos = [dict(m) for m in _config().get("modelos") or [] if m.get("id")]
    if not any(m["id"] == settings.OLLAMA_MODEL for m in modelos):
        modelos.insert(0, {"id": settings.OLLAMA_MODEL, "etiqueta": settings.OLLAMA_MODEL, "descripcion": ""})
    for m in modelos:
        m["predeterminado"] = m["id"] == settings.OLLAMA_MODEL
    return sorted(modelos, key=lambda m: not m["predeterminado"])


def ids() -> set[str]:
    return {m["id"] for m in catalogo()}


def parametros(modelo: str) -> tuple[dict[str, Any], Any]:
    """(opciones de Ollama para la redacción, keep_alive) del modelo."""
    cfg = _config()
    opciones = {"temperature": settings.RAG_TEMPERATURA_REDACCION, "num_ctx": settings.OLLAMA_NUM_CTX,
                **(cfg.get("parametros_comunes") or {})}
    entrada = next((m for m in cfg.get("modelos") or [] if m.get("id") == modelo), {})
    opciones.update(entrada.get("parametros") or {})
    if modelo == settings.OLLAMA_MODEL:
        keep_alive: Any = -1  # número: Ollama rechaza el texto "-1"
    else:
        keep_alive = entrada.get("keep_alive") or cfg.get("keep_alive_no_predeterminado") or "10m"
    return opciones, keep_alive


def campos_extra(modelo: str) -> dict[str, Any]:
    """Campos de /api/generate fuera de `options` («think»: false en los modelos que razonan antes de responder)."""
    entrada = next((m for m in _config().get("modelos") or [] if m.get("id") == modelo), {})
    return {"think": False} if entrada.get("pensar") is False else {}


def usar(modelo: str) -> None:
    """Fija el modelo de la consulta en curso (contexto de la petición)."""
    _EN_CURSO.set(modelo)


def en_curso(predeterminado: str | None = None) -> str:
    """El modelo de la consulta en curso; si no se fijó, `predeterminado` o OLLAMA_MODEL."""
    return _EN_CURSO.get() or predeterminado or settings.OLLAMA_MODEL
