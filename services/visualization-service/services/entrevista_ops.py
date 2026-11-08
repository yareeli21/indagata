"""Operaciones de entrevista que se calculan sin modelo (7 nov 2026, Fase 4).

En la prueba de la investigadora estas preguntas recibían otra cosa: la tabla de respuestas de la participante, una
aclaración («¿qué guía?») o tres preguntas recuperadas por similitud. Se detectan con reglas, se calculan sobre el
documento final (y el reporte de limpieza) y se responden tal cual, con su tabla:

  hablantes    «¿cuántas palabras dijo la participante y cuántas el entrevistador?», «¿cuántas intervenciones…?»:
               turnos y palabras por hablante del reporte de limpieza (la transcripción completa, antes de partirla en
               preguntas).
  cobertura    «¿respondió todas las preguntas de la guía? ¿cuáles no?»: preguntas guía con y sin respuesta de cada
               participante.
  extension    «¿cuál fue su respuesta más larga (o más corta) y a qué pregunta corresponde?»: palabras por respuesta.
  fuera_guia   «¿hubo preguntas de seguimiento que no estaban en la guía?»: intercambios cuya pregunta no es de la guía.
  diagnostico  «¿la participante tiene depresión?»: no se diagnostica; se dice lo que la persona contó sobre cómo se
               siente, con sus citas (análisis de lo que se cuenta, Fase 1).
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from services.dominio import normalizar

HABLANTES, COBERTURA, EXTENSION, FUERA_GUIA, DIAGNOSTICO = "hablantes", "cobertura", "extension", "fuera_guia", "diagnostico"

_HABLANTES = re.compile(r"\bcuant[oa]s\s+(?:palabras|intervenciones|turnos)\b|\b(?:palabras|intervenciones|turnos)\s+(?:dijo|tuvo|"
                        r"hizo|de cada|por hablante)\b|\bquien hablo mas\b")
_COBERTURA = re.compile(r"\brespondi\w*\s+todas\s+las\s+preguntas\b|\bcontest\w*\s+todas\s+las\s+preguntas\b|"
                        r"\b(?:cuales|que)\s+preguntas\s+(?:de la guia\s+)?no\s+(?:respondi|contest)\w*\b|\bcuales\s+no\b.{0,30}\bguia\b")
_EXTENSION = re.compile(r"\brespuesta\s+mas\s+(larga|extensa|corta|breve)\b")
_FUERA_GUIA = re.compile(r"\bpreguntas?\s+de\s+seguimiento\b|\b(?:no|fuera de)\s+(?:estaban|estaba)?\s*(?:en\s+)?la\s+guia\b|"
                         r"\bpreguntas?\s+(?:que\s+)?no\s+(?:estaban|eran)\s+(?:de|en)\s+la\s+guia\b")
_DIAGNOSTICO = re.compile(r"\b(?:tiene|padece|sufre|presenta|esta)\s+(?:de\s+)?(?:una\s+)?(depresion|ansiedad|trastorno\w*|"
                          r"estres cronico|burnout|ataques? de panico|deprimid[oa]|ansios[oa]|enferm\w*)")
_ID = re.compile(r"\b([E]\d{2,4})\b")


def detectar(pregunta: str, instrumentos: list[Any]) -> str | None:
    if not instrumentos or not all(i.tipo == "entrevista" for i in instrumentos):
        return None
    texto = normalizar(pregunta)
    for op, patron in ((DIAGNOSTICO, _DIAGNOSTICO), (HABLANTES, _HABLANTES), (COBERTURA, _COBERTURA),
                       (EXTENSION, _EXTENSION), (FUERA_GUIA, _FUERA_GUIA)):
        if patron.search(texto):
            return op
    return None


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto or ""))


def _participantes(doc: dict[str, Any], pregunta: str) -> list[dict[str, Any]]:
    """Los participantes que nombra la consulta («E05»), o todos."""
    nombrados = set(_ID.findall(pregunta.upper()))
    todos = doc.get("entrevistas") or []
    return [e for e in todos if _corto(e["participante"]) in nombrados] or todos


def _tabla(titulo: str, columnas: list[str], filas: list[list[str]]) -> str:
    lineas = [f"**{titulo}**", "| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    return "\n".join(lineas + ["| " + " | ".join(f) + " |" for f in filas])


def _hablantes(sesion: Session | None, ins: Any) -> str:
    fila = None
    if sesion is not None:
        fila = (sesion.query(LimpiezaEjecucion)
                .filter(LimpiezaEjecucion.id_crudo == int(ins.id_crudo), LimpiezaEjecucion.estado == "confirmada")
                .order_by(LimpiezaEjecucion.version.desc()).first())
    hablantes = (((fila.reporte or {}).get("especifico") or {}).get("entrevista") or {}).get("hablantes") if fila else None
    if not hablantes:
        # Sin reporte de limpieza: se cuenta en el documento final (preguntas del entrevistador y respuestas).
        doc = ins.doc
        entrevistador = sum(_palabras(i.get("pregunta")) for e in doc.get("entrevistas") or [] for i in e["intercambios"])
        filas = [["Entrevistador", str(sum(len(e["intercambios"]) for e in doc.get("entrevistas") or [])), str(entrevistador)]]
        filas += [[_corto(e["participante"]), str(len(e["intercambios"])),
                   str(sum(_palabras(i.get("respuesta")) for i in e["intercambios"]))] for e in doc.get("entrevistas") or []]
        fuente = "contadas en el documento final (preguntas y respuestas)"
    else:
        filas = [[str(h.get("nombre") or h.get("rol")) + f" ({h.get('rol')})", str(h.get("turnos")), str(h.get("palabras"))]
                 for h in hablantes]
        fuente = "de la limpieza de la transcripción completa"
    resumen = "; ".join(f"{f[0]}: {f[1]} intervenciones y {f[2]} palabras" for f in filas)
    return (f"Participación por hablante en «{ins.titulo}» ({fuente}): {resumen}.\n\n"
            + _tabla("Intervenciones y palabras por hablante", ["Hablante", "Intervenciones", "Palabras"], filas))


def _cobertura(ins: Any, pregunta: str) -> str:
    doc = ins.doc
    guia = [(p["id"], p.get("texto", "")) for p in doc.get("preguntas") or []]
    filas, frases = [], []
    for e in _participantes(doc, pregunta):
        respondidas = {i.get("pregunta_id") for i in e["intercambios"] if i.get("pregunta_id") and (i.get("respuesta") or "").strip()}
        faltan = [(pid, t) for pid, t in guia if pid not in respondidas]
        quien = _corto(e["participante"])
        filas.append([quien, f"{len(guia) - len(faltan)} de {len(guia)}", ", ".join(_corto(p) for p, _ in faltan) or "ninguna"])
        frases.append(f"{quien} respondió las {len(guia)} preguntas de la guía." if not faltan else
                      f"{quien} respondió {len(guia) - len(faltan)} de {len(guia)}; no respondió: "
                      + "; ".join(f"{_corto(p)} «{t[:70]}»" for p, t in faltan) + ".")
    aviso = (" La guía se tomó de las preguntas que hizo el entrevistador (no se subió el guion original)."
             if any(a.get("codigo") == "sin_original" for a in doc.get("avisos") or []) else "")
    return " ".join(frases) + aviso + "\n\n" + _tabla("Preguntas de la guía respondidas", ["Participante", "Respondió", "Sin respuesta"], filas)


def _extension(ins: Any, pregunta: str) -> str:
    corta = bool(re.search(r"\b(?:corta|breve)\b", normalizar(pregunta)))
    doc = ins.doc
    guia = {p["id"]: p.get("texto", "") for p in doc.get("preguntas") or []}
    frases, filas = [], []
    for e in _participantes(doc, pregunta)[:5]:
        medidas = sorted(((_palabras(i.get("respuesta")), i) for i in e["intercambios"]), key=lambda x: x[0], reverse=not corta)
        if not medidas:
            continue
        n, i = medidas[0]
        pid = i.get("pregunta_id") or ""
        texto = guia.get(pid) or i.get("pregunta") or ""
        frases.append(f"La respuesta más {'corta' if corta else 'larga'} de {_corto(e['participante'])} es la de "
                      f"{_corto(pid) or 'una pregunta fuera de la guía'} «{texto[:90]}»: {n} palabras.")
        filas += [[_corto(e["participante"]), _corto(x.get("pregunta_id") or "") or "—", str(m)] for m, x in medidas[:3]]
    return (" ".join(frases) + " (Se cuentan las palabras de cada respuesta en el documento final.)\n\n"
            + _tabla(f"Respuestas más {'cortas' if corta else 'largas'}", ["Participante", "Pregunta", "Palabras"], filas))


def _fuera_guia(ins: Any) -> str:
    doc = ins.doc
    fuera = [(e, i) for e in doc.get("entrevistas") or [] for i in e["intercambios"] if not i.get("pregunta_id")]
    sin_original = any(a.get("codigo") == "sin_original" for a in doc.get("avisos") or [])
    if not fuera:
        base = "Todas las preguntas del entrevistador corresponden a una pregunta de la guía; no hubo preguntas de seguimiento fuera de ella."
        if sin_original:
            base += (" Ojo: como no se subió el guion original, la guía se armó con las preguntas que hizo el entrevistador, "
                     "así que una pregunta de seguimiento también quedó como parte de la guía.")
        return base
    filas = [[_corto(e["participante"]), (i.get("pregunta") or "")[:120]] for e, i in fuera[:20]]
    return (f"Hubo {len(fuera)} intervención(es) del entrevistador que no corresponden a ninguna pregunta de la guía.\n\n"
            + _tabla("Preguntas fuera de la guía", ["Participante", "Pregunta del entrevistador"], filas))


def _diagnostico(ins: Any, pregunta: str) -> str:
    termino = (_DIAGNOSTICO.search(normalizar(pregunta)) or [None, "eso"])[1]
    doc = ins.doc
    personas = _participantes(doc, pregunta)
    quien = ", ".join(_corto(e["participante"]) for e in personas[:3]) if len(personas) <= 3 else "las personas entrevistadas"
    citas = []
    for e in personas:
        for i in e["intercambios"]:
            nlp = (i.get("analisis") or {}).get("nlp") or {}
            v = nlp.get("valoracion") or {}
            if v.get("valor") in ("negativo", "mixto") and v.get("cita"):
                citas.append((_corto(e["participante"]), _corto(i.get("pregunta_id") or ""), v["cita"]))
    lineas = [f"- {p} en {q or 'una respuesta'}: «{c}»" for p, q, c in citas[:4]]
    base = (f"No hago diagnósticos: con una entrevista no se puede saber si {quien} tiene {termino}, y eso solo lo puede "
            "valorar un profesional de la salud.")
    if lineas:
        return base + f" Lo que sí contó sobre cómo se siente, con sus palabras:\n" + "\n".join(lineas)
    return base + " Puedo mostrarte lo que dijo sobre su estado de ánimo si me dices de qué pregunta."


def responder(op: str, pregunta: str, instrumentos: list[Any], sesion: Session | None = None) -> str:
    bloques = []
    for ins in instrumentos[:2]:
        if op == HABLANTES:
            bloques.append(_hablantes(sesion, ins))
        elif op == COBERTURA:
            bloques.append(_cobertura(ins, pregunta))
        elif op == EXTENSION:
            bloques.append(_extension(ins, pregunta))
        elif op == FUERA_GUIA:
            bloques.append(_fuera_guia(ins))
        elif op == DIAGNOSTICO:
            bloques.append(_diagnostico(ins, pregunta))
    return "\n\n".join(bloques)
