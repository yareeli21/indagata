"""Respuestas del documento final en formato largo (`tt_rag.respuesta_interpretada`).

Al publicar un documento final se reemplazan las filas de ese instrumento con una
fila por respuesta (respondente × pregunta). El chat usa la tabla para conteos y
porcentajes exactos entre varios instrumentos; las consultas de un solo
instrumento siguen corriendo sobre el documento (`consultas.py`).

Qué va en cada columna según el tipo:
  encuesta    valor (código o texto original) · significado · nivel de la escala
  prueba      opción elegida · su significado · nivel `correcta`/`incorrecta`
  entrevista  la respuesta (texto) · sin nivel; `pregunta_id` vacío si el turno
              no se pudo asociar a una pregunta del guion
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from shared.models.respuesta_interpretada import RespuestaInterpretada


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, list):
        return "; ".join(map(str, valor))
    return str(valor)


def filas(doc: dict[str, Any], id_crudo: int, version: int) -> list[dict[str, Any]]:
    """Filas de `respuesta_interpretada` derivadas del documento (sin escribir nada)."""
    salida: list[dict[str, Any]] = []
    base = {"id_crudo": id_crudo, "version": version}
    for r in doc.get("respondentes") or []:
        for x in r.get("respuestas") or []:
            salida.append({**base, "respondente_id": r["id"], "pregunta_id": x["pregunta_id"],
                           "valor": _texto(x.get("seleccion") or x.get("valor")), "significado": _texto(x.get("significado")),
                           "nivel": x.get("nivel"), "estado": x.get("estado") or "respondida", "contexto": r.get("contexto") or {}})
    for a in doc.get("alumnos") or []:
        for x in a.get("respuestas") or []:
            nivel = "correcta" if x.get("correcta") is True else "incorrecta" if x.get("correcta") is False else None
            salida.append({**base, "respondente_id": a["id"], "pregunta_id": x["reactivo_id"], "valor": _texto(x.get("respuesta")),
                           "significado": _texto(x.get("significado")), "nivel": nivel, "estado": x.get("estado") or "valida",
                           "contexto": a.get("contexto") or {}})
    for e in doc.get("entrevistas") or []:
        for i in e.get("intercambios") or []:
            salida.append({**base, "respondente_id": e["participante"], "pregunta_id": i.get("pregunta_id") or "",
                           "valor": _texto(i.get("respuesta")), "significado": None, "nivel": None, "estado": "respondida",
                           "contexto": {}})
    return salida


def reemplazar(db: Session, doc: dict[str, Any], id_crudo: int, version: int) -> int:
    """Reemplaza las filas del instrumento por las del documento (sin commit)."""
    db.query(RespuestaInterpretada).filter(RespuestaInterpretada.id_crudo == id_crudo).delete(synchronize_session=False)
    nuevas = filas(doc, id_crudo, version)
    db.add_all(RespuestaInterpretada(**f) for f in nuevas)
    return len(nuevas)
