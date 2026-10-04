"""Prompt de fundamentación en español (diseño §4.8).

`construir(pregunta, chunks)` arma el prompt EXACTO del diseño: instrucción de
responder únicamente con el CONTEXTO, el bloque de fuentes numeradas y la
pregunta del usuario.
"""
from __future__ import annotations

from typing import Any

_INSTRUCCION = (
    "Eres un asistente de investigación educativa. Responde en español, de forma\n"
    "clara y concisa, USANDO ÚNICAMENTE la información del CONTEXTO. Si el contexto\n"
    "no contiene la respuesta, dilo explícitamente y no inventes datos."
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
