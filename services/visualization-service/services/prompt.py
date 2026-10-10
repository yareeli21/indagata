"""Prompt de fundamentación en español para el chat RAG.

`construir(pregunta, fragmentos)` arma el prompt: instrucción de responder SOLO
con el CONTEXTO (y citar las fuentes), el bloque de fragmentos numerados y la
pregunta del usuario. Cada fragmento indica de qué instrumento y qué parte
(encabezado, pregunta o contenido) proviene, para que el modelo pueda combinar
lo cualitativo (texto, preguntas) con lo cuantitativo (resultados por reactivo).
"""
from __future__ import annotations

from typing import Any

_INSTRUCCION = (
    "Eres un asistente de investigación educativa. Responde en español, de forma\n"
    "clara y concisa, USANDO ÚNICAMENTE la información del CONTEXTO. Cita las fuentes\n"
    "como [Fuente n]. Cuando haya resultados numéricos, úsalos con precisión. Si el\n"
    "contexto no contiene la respuesta, dilo explícitamente y no inventes datos."
)

_SECCION = {"encabezado": "ficha", "pregunta": "reactivo", "contenido": "texto"}


_CONTEXTO = {
    "objetivo": "Objetivo",
    "poblacion": "Población",
    "nivel": "Nivel educativo",
    "pregunta": "Pregunta de investigación",
}


def construir(
    pregunta: str, fragmentos: list[dict[str, Any]], contexto_investigacion: dict[str, Any] | None = None
) -> str:
    investigacion = ""
    if contexto_investigacion:
        datos = [
            f"- {etiqueta}: {contexto_investigacion[clave]}"
            for clave, etiqueta in _CONTEXTO.items()
            if contexto_investigacion.get(clave)
        ]
        if datos:
            investigacion = "INVESTIGACIÓN EN CURSO (orienta la respuesta, no es fuente):\n" + "\n".join(datos) + "\n\n"

    lineas: list[str] = []
    for i, f in enumerate(fragmentos, start=1):
        parte = _SECCION.get(str(f.get("seccion") or ""), "fragmento")
        lineas.append(
            f"[Fuente {i} — {f.get('titulo') or 'Instrumento'} ({f.get('tipo') or ''}, "
            f"{f.get('investigador') or 'autor no indicado'}) · {parte}]"
        )
        lineas.append(str(f.get("fragmento") or ""))
    contexto = "\n".join(lineas) if lineas else "(sin fragmentos)"
    return f"{_INSTRUCCION}\n\n{investigacion}CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA:"
