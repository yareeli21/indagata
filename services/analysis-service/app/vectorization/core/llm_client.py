"""Cliente mínimo del LLM local (Ollama), con degradación grácil.

Solo se usa para la justificación breve de cada KPI sugerido (la única parte del
flujo de conocimiento que admite LLM, porque la revisa el investigador). Si Ollama
no responde, `generar_json` devuelve None y quien llama usa una plantilla.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("analysis-service")


def generar_json(prompt: str, *, timeout: float | None = None) -> dict[str, Any] | None:
    """Respuesta del modelo como objeto JSON, o None si falla. Nunca lanza."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": -1,  # número: Ollama rechaza "-1" como texto (exige unidad de tiempo)
        "options": {"temperature": 0.2, "num_ctx": 4096},  # igual que el chat: Ollama no recarga el modelo
    }
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate"
    try:
        limite = httpx.Timeout(timeout or settings.KPI_LLM_TIMEOUT, connect=5.0)
        with httpx.Client(timeout=limite) as cliente:
            resp = cliente.post(url, json=payload)
        resp.raise_for_status()
        datos = json.loads(resp.json().get("response") or "{}")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("LLM no disponible: %s", exc)
        return None
    return datos if isinstance(datos, dict) else None
