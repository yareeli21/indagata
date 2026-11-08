"""Preguntas sobre la estructura del instrumento que se responden con su documento, sin modelo (7 nov 2026, Fase 4).

  opcionales  «¿qué preguntas eran opcionales / obligatorias?»: el documento final no registra ese dato; se dice así, en
              lugar de inventarlo (ENC-21: el modelo afirmó que p07 era opcional), y se ofrece lo que sí hay.
  escalas     «¿cuáles preguntas usan escala del 1 al 5 y qué significan sus extremos?»: las preguntas con escala y el
              significado de sus extremos, del catálogo (ENC-20: nombraba 3 de 4 y sin los extremos).
"""
from __future__ import annotations

import re
from typing import Any

from services.dominio import normalizar

OPCIONALES, ESCALAS = "opcionales", "escalas"
_OPCIONALES = re.compile(r"\b(?:opcional\w*|obligatori\w*|no eran obligatori\w*)\b")
_ESCALAS = re.compile(r"\b(?:cuales|que)\s+(?:preguntas|reactivos)\s+(?:usan|tienen|son\s+de|usaron|ocupan)\s+(?:una\s+)?escala\b"
                      r"|\bescala\s+del?\s+\d+\s+al?\s+\d+\b.{0,40}\b(?:preguntas|cuales)\b"
                      r"|\b(?:preguntas|cuales)\b.{0,40}\bescala\s+del?\s+\d+\s+al?\s+\d+\b")


def detectar(pregunta: str, instrumentos: list[Any]) -> str | None:
    if not instrumentos or any(i.tipo == "entrevista" for i in instrumentos):
        return None
    texto = normalizar(pregunta)
    if _OPCIONALES.search(texto) and re.search(r"\b(?:preguntas?|reactivos?)\b", texto):
        return OPCIONALES
    if _ESCALAS.search(texto):
        return ESCALAS
    return None


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _escalas(ins: Any) -> str:
    filas = []
    for p in ins.doc.get("preguntas") or ins.doc.get("reactivos") or []:
        etiquetas = (p.get("escala") or {}).get("etiquetas") or {}
        if not etiquetas:
            continue
        puntos = sorted(etiquetas, key=lambda k: int(k) if str(k).isdigit() else 0)
        filas.append([_corto(p["id"]), str(p.get("texto", ""))[:90], f"{puntos[0]} = {etiquetas[puntos[0]]}",
                      f"{puntos[-1]} = {etiquetas[puntos[-1]]}"])
    if not filas:
        return f"«{ins.titulo}» no tiene preguntas con escala numérica."
    tabla = ["| Pregunta | Texto | Extremo bajo | Extremo alto |", "|---|---|---|---|"] + ["| " + " | ".join(f) + " |" for f in filas]
    return (f"En «{ins.titulo}», {len(filas)} preguntas usan una escala: {', '.join(f[0] for f in filas)}. Sus extremos:\n\n"
            "**Preguntas con escala**\n" + "\n".join(tabla))


def responder(op: str, instrumentos: list[Any]) -> str:
    if op == OPCIONALES:
        return ("El documento final no registra qué preguntas eran opcionales u obligatorias en el instrumento original, "
                "así que no puedo decírtelo sin inventarlo. Lo que sí registra es cuántas personas dejaron cada pregunta "
                "sin responder: puedes preguntarme «¿en qué pregunta hubo más respuestas sin contestar?».")
    return "\n\n".join(_escalas(i) for i in instrumentos[:2])
