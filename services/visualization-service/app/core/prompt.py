"""Prompt de fundamentación en español (diseño §4.8).

`construir(pregunta, chunks)` arma el prompt EXACTO del diseño: instrucción de
responder únicamente con el CONTEXTO, el bloque de fuentes numeradas y la
pregunta del usuario.
"""
from __future__ import annotations

from typing import Any

_INSTRUCCION = (
    "Eres un asistente de investigación educativa que elabora DIAGNÓSTICOS\n"
    "PEDAGÓGICOS a partir de datos de instrumentos. Responde SIEMPRE en español,\n"
    "de forma clara y estructurada.\n"
    "\n"
    "Tu tarea es ANALIZAR E INTERPRETAR la información del CONTEXTO: identifica\n"
    "fortalezas y debilidades, señala patrones y explica sus implicaciones\n"
    "educativas (qué conviene reforzar y por qué). No te limites a repetir las\n"
    "cifras: razona su significado.\n"
    "\n"
    "ALCANCE DE LA COMPARACIÓN: compara dimensiones o grupos ENTRE SÍ solo si\n"
    "ambos aparecen en el CONTEXTO. Si el CONTEXTO trae una sola dimensión o un\n"
    "solo grupo, interprétalo por sí mismo SIN compararlo con otros que no estén\n"
    "presentes. Si un fragmento ya indica cuál es la dimensión más fuerte o más\n"
    "débil, puedes apoyarte en esa afirmación del propio contexto.\n"
    "\n"
    "REGLA ESTRICTA SOBRE LOS DATOS: las CIFRAS (medias, porcentajes, número de\n"
    "respondentes, nombres de dimensiones o ítems) deben provenir EXCLUSIVAMENTE\n"
    "del CONTEXTO. No inventes números, dimensiones, ítems ni resultados que no\n"
    "estén en el contexto. Si el contexto no contiene un dato concreto que se te\n"
    "pide, dilo explícitamente («el contexto no incluye ese dato») en lugar de\n"
    "inventarlo. Puedes y debes interpretar y concluir A PARTIR DE las cifras que\n"
    "sí están presentes."
)


def construir(pregunta: str, chunks: list[Any]) -> str:
    """Construye el prompt español fundamentado.

    Args:
        pregunta: la pregunta del usuario.
        chunks:   fragmentos recuperados. Cada elemento puede ser un str (solo
                  el fragmento) o un dict con las claves `fragmento`, `titulo`,
                  `tipo`, `investigador` para encabezar cada fuente.
    """
    lineas: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            titulo = chunk.get("titulo") or ""
            tipo = chunk.get("tipo") or ""
            investigador = chunk.get("investigador") or ""
            fragmento = chunk.get("fragmento") or chunk.get("documento") or ""
            lineas.append(f"[Fuente {i} — {titulo} ({tipo}, {investigador})]")
            lineas.append(str(fragmento))
        else:
            lineas.append(f"[Fuente {i}]")
            lineas.append(str(chunk))

    contexto = "\n".join(lineas)

    return (
        f"{_INSTRUCCION}\n\n"
        f"CONTEXTO:\n{contexto}\n\n"
        f"PREGUNTA: {pregunta}\n\n"
        f"RESPUESTA:"
    )
