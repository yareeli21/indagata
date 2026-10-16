"""Sugerencias de metadatos con el LLM local (Ollama), con degradación grácil.

Las heurísticas de `analizador` cubren lo que se puede leer del archivo (número
de respondentes, dimensiones, institución, ciclo escolar…). Los campos
interpretativos (objetivo, constructo, población, descripción) se piden al
modelo local SOLO si quedaron vacíos o son una plantilla genérica. Si Ollama no
responde, se devuelve `{}` y el autor completa esos campos a mano: el LLM nunca
es requisito para aprobar.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("metadata-service")

# Contexto máximo enviado al modelo (caracteres), acorde a num_ctx=2048.
_MAX_CONTEXTO = 2500


def _prompt(tipo_ui: str, titulo: str, contexto: str, campos: dict[str, str]) -> str:
    lista = "\n".join(f'- "{clave}": {descripcion}' for clave, descripcion in campos.items())
    return (
        "Eres un catalogador de instrumentos de investigación educativa en México.\n"
        f"Analiza el siguiente instrumento de tipo {tipo_ui} titulado «{titulo}» y propone "
        "metadatos en español, breves y fieles al contenido. Si un dato no se puede "
        "deducir, deja la cadena vacía. No inventes cifras, instituciones ni fechas.\n\n"
        f"CONTENIDO DEL INSTRUMENTO:\n{contexto[:_MAX_CONTEXTO]}\n\n"
        "Responde ÚNICAMENTE con un objeto JSON con estas claves:\n"
        f"{lista}\n"
        'Para las claves de lista ("palabras_clave", "dimensiones") devuelve un arreglo de cadenas.'
    )


def sugerir(tipo_ui: str, titulo: str, contexto: str, campos: dict[str, str]) -> dict[str, Any]:
    """Pide al modelo valores para `campos` ({clave: descripción}). Nunca lanza."""
    if not campos or not contexto.strip():
        return {}
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": _prompt(tipo_ui, titulo, contexto, campos),
        "stream": False,
        "format": "json",
        # Número, no texto: Ollama rechaza "-1" con 400. num_ctx igual al del chat
        # (visualization-service) para que Ollama no recargue el modelo al alternar.
        "keep_alive": -1,
        "options": {"temperature": 0.2, "num_ctx": 4096},
    }
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate"
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.METADATA_LLM_TIMEOUT, connect=5.0)) as cliente:
            resp = cliente.post(url, json=payload)
        resp.raise_for_status()
        datos = json.loads(resp.json().get("response") or "{}")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Sugerencias del LLM no disponibles: %s", exc)
        return {}
    if not isinstance(datos, dict):
        return {}

    sugerencias: dict[str, Any] = {}
    for clave in campos:
        valor = datos.get(clave)
        if isinstance(valor, str) and valor.strip():
            sugerencias[clave] = valor.strip()
        elif isinstance(valor, list):
            elementos = [str(v).strip() for v in valor if str(v).strip()]
            if elementos:
                sugerencias[clave] = elementos[:10]
    return sugerencias
