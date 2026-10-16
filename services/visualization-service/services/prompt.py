"""Prompt de fundamentación en español para el chat RAG.

Dos partes:
  - `SISTEMA`: las reglas (responder SOLO con el CONTEXTO, citar [Fuente n],
    decir que no hay información si nada se relaciona). Va en el campo `system`
    de Ollama: llama3.2 las respeta mejor ahí que mezcladas con el contexto
    (comparado con las mismas preguntas y fragmentos: cita en el formato pedido
    y no agrega frases contradictorias).
  - `construir(pregunta, fragmentos)`: el mensaje del usuario con la
    investigación en curso, los fragmentos agrupados por instrumento bajo
    `[Fuente n]` (n = número de la tarjeta de fuente en la UI) y la pregunta.
    Cada fragmento indica qué parte es (ficha, reactivo o texto), para combinar
    lo cualitativo con lo cuantitativo.
"""
from __future__ import annotations

from typing import Any

SIN_INFORMACION = "No tengo información relacionada con lo que solicitas en los instrumentos consultados."

SISTEMA = (
    "Eres un asistente de investigación educativa que responde preguntas sobre instrumentos de "
    "investigación (encuestas, entrevistas y pruebas estandarizadas).\n"
    "Reglas obligatorias:\n"
    "1. Usa SOLO la información del CONTEXTO. No agregues conocimiento propio ni supongas datos.\n"
    "2. Al final de cada afirmación escribe la fuente de donde sale, así: [Fuente 2].\n"
    "3. Si el CONTEXTO trae resultados numéricos, cítalos con exactitud. Si se piden porcentajes, da "
    "la distribución completa e indica el significado de cada valor de la escala.\n"
    "4. Si la pregunta pide instrumentos, menciona solo los que en el CONTEXTO se relacionan "
    "explícitamente con lo que se pregunta (por su objetivo, temas, preguntas o KPIs asociados) y di por "
    "qué; no incluyas un instrumento solo porque aparece en el CONTEXTO.\n"
    "5. Distingue quién dice qué (estudiante, docente, entrevistador) tal como aparece en el CONTEXTO.\n"
    "6. Responde solo lo que se pregunta, sin comentarios sobre temas que no se piden.\n"
    f'7. Si NADA del CONTEXTO se relaciona con la PREGUNTA, responde únicamente: "{SIN_INFORMACION}" '
    "Usa esa frase solo cuando no puedas responder nada; nunca la agregues a una respuesta que sí diste.\n"
    "8. Responde en español, de forma clara y breve."
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

    # Agrupados por instrumento: una fuente = un instrumento, con el mismo número
    # que su tarjeta en la UI (`numero`; si falta, orden de aparición).
    grupos: dict[str, list[dict[str, Any]]] = {}
    for f in fragmentos:
        grupos.setdefault(str(f.get("instrumentoId") or f.get("titulo") or ""), []).append(f)
    lineas: list[str] = []
    for i, grupo in enumerate(grupos.values(), start=1):
        f = grupo[0]
        lineas.append(
            f"[Fuente {f.get('numero') or i}] {f.get('titulo') or 'Instrumento'} ({f.get('tipo') or ''}, "
            f"{f.get('investigador') or 'autor no indicado'})"
        )
        for g in grupo:
            parte = _SECCION.get(str(g.get("seccion") or ""), "fragmento")
            lineas.append(f"- {parte}: {g.get('fragmento') or ''}")
        lineas.append("")
    contexto = "\n".join(lineas).strip() if lineas else "(sin fragmentos)"
    return f"{investigacion}CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"
