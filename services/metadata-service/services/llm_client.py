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
import re
from typing import Any

import httpx

from shared.db.core.config import settings

logger = logging.getLogger("metadata-service")

# Contexto máximo enviado al modelo (caracteres), acorde a num_ctx=2048.
_MAX_CONTEXTO = 2500
# Encabezados de columna («Evaluación_item3», «P3», «item_12»): no son dimensiones ni palabras clave.
_RE_CODIGO = re.compile(r"(_\s*(?:[ií]tem|reactivo)?\s*\d+$)|(^[A-Za-z]{1,3}\s*\d{1,3}$)|[\[\]{}]", re.IGNORECASE)


def _es_codigo(valor: str) -> bool:
    return bool(_RE_CODIGO.search(valor.strip()))


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
            # Solo cadenas: el modelo de 3B a veces anida listas de columnas
            # (['Evaluación', ['Evaluación_item1', …]]) que acabarían como texto crudo.
            elementos = [v.strip() for v in valor if isinstance(v, str) and v.strip() and not _es_codigo(v)]
            if elementos:
                sugerencias[clave] = elementos[:10]
    return sugerencias


def nombrar_grupos(tipo_ui: str, titulo: str, grupos: list[list[str]]) -> list[str]:
    """Un nombre corto por grupo de preguntas (dimensiones sugeridas). [] si no hay respuesta útil.

    El resultado se usa solo si trae exactamente un nombre por grupo, todos texto y sin
    códigos de columna; si no, se conservan los nombres genéricos («Dimensión 1»…).
    """
    if not grupos:
        return []
    lista = "\n".join(f"Grupo {i}:\n" + "\n".join(f"- {t}" for t in g[:12]) for i, g in enumerate(grupos, start=1))
    prompt = (
        f"Estas son las preguntas de un(a) {tipo_ui} titulado(a) «{titulo}», agrupadas por cómo se responden.\n"
        f"{lista}\n\n"
        "Para cada grupo, en orden, propone un nombre breve (2 a 5 palabras, en español) del aspecto que miden "
        "sus preguntas. Responde SOLO un JSON con la forma {\"nombres\": [\"…\", \"…\"]} y exactamente "
        f"{len(grupos)} nombres."
    )
    payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json",
               "keep_alive": -1, "options": {"temperature": 0.0, "num_ctx": 4096}}
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.METADATA_LLM_TIMEOUT, connect=5.0)) as cliente:
            resp = cliente.post(f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate", json=payload)
        resp.raise_for_status()
        nombres = json.loads(resp.json().get("response") or "{}").get("nombres")
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        logger.warning("Nombres de dimensiones no disponibles: %s", exc)
        return []
    if not isinstance(nombres, list) or len(nombres) != len(grupos):
        return []
    limpios = [" ".join(n.split())[:60] for n in nombres if isinstance(n, str) and n.strip() and not _es_codigo(n)]
    return limpios if len(limpios) == len(grupos) and len(set(limpios)) == len(limpios) else []
