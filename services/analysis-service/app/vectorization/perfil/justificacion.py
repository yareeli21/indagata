"""Justificación breve de por qué un KPI se relaciona con el instrumento.

Es la ÚNICA pieza del flujo de conocimiento generada con LLM, y el investigador la
revisa (y puede editarla) antes de aceptar el KPI. Si el LLM no responde o su
respuesta no sirve, se usa una plantilla determinística.

Orígenes posibles (se guardan con la decisión):
  llm                 generada por el LLM y aceptada sin cambios
  llm_revisada        generada por el LLM y editada por el investigador
  plantilla           plantilla determinística aceptada sin cambios
  plantilla_revisada  plantilla editada por el investigador
"""
from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from app.vectorization.core import llm_client

_MAX_DEFINICION = 900
_MIN_LARGO = 30
_MAX_LARGO = 600


def plantilla(nombre_kpi: str, objetivo: str, preguntas: list[str]) -> str:
    """Justificación determinística a partir de la evidencia."""
    citas = [f"«{p}»" for p in preguntas[:2]]
    if len(citas) == 2:
        return f"Se relaciona con «{nombre_kpi}» porque las preguntas {citas[0]} y {citas[1]} abordan aspectos que este indicador mide."
    if citas:
        return f"Se relaciona con «{nombre_kpi}» porque la pregunta {citas[0]} aborda aspectos que este indicador mide."
    if objetivo:
        return f"Se relaciona con «{nombre_kpi}» por el objetivo del instrumento: {objetivo.rstrip('.')}."
    return f"Se relaciona con «{nombre_kpi}» por la similitud entre el instrumento y la definición del indicador."


def _prompt(nombre: str, definicion: str, que_mide: str, objetivo: str, preguntas: list[str]) -> str:
    lista = "\n".join(f"- {p}" for p in preguntas[:5]) or "- (sin preguntas con respaldo directo)"
    return (
        "Eres un analista de investigación educativa. Explica en 2 o 3 oraciones, en español, "
        "por qué el indicador (KPI) se relaciona con el instrumento, citando qué miden sus "
        "preguntas. Usa solo la información dada; no inventes datos, cifras ni resultados.\n\n"
        f"KPI: {nombre}\nQué mide: {que_mide[:_MAX_DEFINICION]}\nDefinición: {definicion[:_MAX_DEFINICION]}\n\n"
        f"Objetivo del instrumento: {objetivo[:400]}\nPreguntas del instrumento más relacionadas:\n{lista}\n\n"
        'Responde ÚNICAMENTE con un objeto JSON: {"justificacion": "…"}'
    )


def justificar(
    kpi: dict[str, Any],
    objetivo: str,
    preguntas: list[str],
    *,
    usar_llm: bool,
    generar: Callable[[str], dict[str, Any] | None] | None = None,
) -> tuple[str, str]:
    """(texto, origen) — LLM si está disponible y da una respuesta útil; si no, plantilla."""
    if usar_llm:
        generar = generar or llm_client.generar_json  # se resuelve al llamar (reemplazable en pruebas)
        datos = generar(_prompt(kpi["nombre"], kpi.get("definicion") or "", kpi.get("que_mide") or "", objetivo, preguntas))
        # El modelo a veces devuelve entidades HTML (&quot;…): se convierten a texto normal.
        texto = " ".join(html.unescape(str((datos or {}).get("justificacion") or "")).split())
        if _MIN_LARGO <= len(texto):
            return texto[:_MAX_LARGO], "llm"
    return plantilla(kpi["nombre"], objetivo, preguntas), "plantilla"


def origen_final(origen: str, editada: bool) -> str:
    """Origen que se guarda al confirmar: marca si el investigador editó el texto."""
    if not editada:
        return origen if origen in ("llm", "plantilla") else "plantilla"
    return "llm_revisada" if origen.startswith("llm") else "plantilla_revisada"
