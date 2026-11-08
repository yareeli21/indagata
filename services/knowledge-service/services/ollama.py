"""Cliente mínimo de Ollama para el análisis de entrevistas (JSON, temperatura 0).

Degradación limpia: si Ollama no responde, devuelve None y el análisis usa el
respaldo por reglas. El documento final nunca depende del modelo.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("knowledge-service")
# 300 s: con gemma3:4b (43 % en CPU) un JSON largo puede pasar de 2 minutos (7 nov).
_TIMEOUT = httpx.Timeout(300.0, connect=5.0)


def generar_json(prompt: str, modelo: str | None = None, formato: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """`formato`: esquema JSON de la salida (Ollama solo deja escribir esos campos); sin él, JSON libre."""
    payload = {
        "model": modelo or settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": formato or "json",
        # Número, no texto: Ollama rechaza "-1". num_ctx igual al de los demás servicios.
        "keep_alive": -1,
        "options": {"temperature": 0.0, "num_ctx": 4096},
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as cliente:
            r = cliente.post(f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate", json=payload)
        r.raise_for_status()
        datos = json.loads(r.json().get("response") or "{}")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Análisis de entrevista sin LLM: %s", exc)
        return None
    return datos if isinstance(datos, dict) else None
