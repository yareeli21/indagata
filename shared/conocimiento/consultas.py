"""Consultas simples y determinísticas sobre el documento final (sin LLM).

Demuestran que el documento contiene todo lo necesario para responder las preguntas
de los criterios de aceptación. Las usan knowledge-service (pruebas de criterios) y la
ruta estructurada del chat (visualization-service, `services/enrutador.py`).

Los IDs se aceptan completos («INS-0012-R017») o cortos («R017», «p03», «KPI-07»).
"""
from __future__ import annotations

import unicodedata
from typing import Any


def _norm(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def _id(doc: dict[str, Any], corto: str) -> str:
    """«R017» → «INS-0012-R017» (los IDs completos se devuelven tal cual)."""
    ins = doc["instrumento"]["id"]
    return corto if corto.startswith("INS-") else f"{ins}-{corto}"


def _kpi(doc: dict[str, Any], kpi: str) -> dict[str, Any] | None:
    return next((k for k in doc.get("kpis_asociados") or [] if k["kpi_id"] == kpi), None)


def pregunta(doc: dict[str, Any], *, pregunta_id: str | None = None, texto: str | None = None) -> dict[str, Any] | None:
    """La pregunta por ID o la primera cuyo texto contiene `texto` (sin acentos ni mayúsculas)."""
    preguntas = doc.get("preguntas") or doc.get("reactivos") or doc.get("preguntas_guia") or []
    if pregunta_id:
        objetivo = _id(doc, pregunta_id)
        return next((p for p in preguntas if p["id"] == objetivo), None)
    buscado = _norm(texto or "")
    return next((p for p in preguntas if buscado in _norm(p["texto"])), None)


# 1. ¿Qué respondió el respondente R017 en la pregunta sobre X?
def respuesta(doc: dict[str, Any], respondente: str, *, pregunta_id: str | None = None, texto: str | None = None) -> dict[str, Any] | None:
    p = pregunta(doc, pregunta_id=pregunta_id, texto=texto)
    persona = next((r for r in doc.get("respondentes") or [] if r["id"] == _id(doc, respondente)), None)
    if p is None or persona is None:
        return None
    r = next((x for x in persona["respuestas"] if x["pregunta_id"] == p["id"]), None)
    return {"pregunta": p["texto"], **r} if r else None


# 2. Un respondente que esté en un nivel (p. ej. «desacuerdo») en TODAS estas preguntas, o None.
def respondente_con_nivel(doc: dict[str, Any], preguntas: list[str], nivel: str) -> str | None:
    objetivo = {_id(doc, p) for p in preguntas}
    for r in doc.get("respondentes") or []:
        niveles = {x["pregunta_id"]: x.get("nivel") for x in r["respuestas"] if x["pregunta_id"] in objetivo}
        if len(niveles) == len(objetivo) and all(v == nivel for v in niveles.values()):
            return r["id"]
    return None


# 3. ¿Qué porcentaje de un grupo (contexto) está en un nivel en una pregunta?
def conteo_nivel(doc: dict[str, Any], pregunta_id: str, nivel: str, contexto: dict[str, str] | None = None) -> tuple[int, int]:
    """(cuántos están en el nivel, cuántos respondieron válidamente) dentro del grupo."""
    objetivo = _id(doc, pregunta_id)
    filtro = {_norm(k): _norm(v) for k, v in (contexto or {}).items()}
    total = en_nivel = 0
    for r in doc.get("respondentes") or []:
        ctx = {_norm(k): _norm(v) for k, v in r["contexto"].items() if v is not None}
        if any(ctx.get(k) != v for k, v in filtro.items()):
            continue
        x = next((x for x in r["respuestas"] if x["pregunta_id"] == objetivo), None)
        if x and x["estado"] == "respondida":
            total += 1
            en_nivel += x.get("nivel") == nivel
    return en_nivel, total


def pct_nivel(doc: dict[str, Any], pregunta_id: str, nivel: str, contexto: dict[str, str] | None = None) -> float | None:
    """Porcentaje sobre quienes respondieron válidamente esa pregunta dentro del grupo."""
    en_nivel, total = conteo_nivel(doc, pregunta_id, nivel, contexto)
    return round(100 * en_nivel / total, 1) if total else None


# 4. ¿Por qué el KPI X está relacionado y qué mide según sus preguntas?
def info_kpi(doc: dict[str, Any], kpi: str) -> dict[str, Any] | None:
    k = _kpi(doc, kpi)
    if k is None:
        return None
    evidencia = []
    for e in k["evidencia"]:
        p = pregunta(doc, pregunta_id=e["pregunta_id"])
        evidencia.append({"pregunta_id": e["pregunta_id"], "similitud": e["similitud"], "texto": p["texto"] if p else None,
                          "resumen": (p or {}).get("resumen")})
    return {"kpi_id": k["kpi_id"], "nombre": k["nombre"], "definicion": k["definicion"], "que_mide": k["que_mide"],
            "dimension": k["dimension"], "justificacion": k["justificacion"], "evidencia": evidencia}


# 5. ¿Qué preguntas miden el KPI X y cómo respondieron?
def preguntas_de_kpi(doc: dict[str, Any], kpi: str) -> list[dict[str, Any]]:
    preguntas = doc.get("preguntas") or doc.get("reactivos") or doc.get("preguntas_guia") or []
    return [{"pregunta_id": p["id"], "texto": p["texto"], "resumen": p.get("resumen")} for p in preguntas if kpi in p.get("kpis_relacionados", [])]


# 6a. ¿Qué reactivo tuvo el menor porcentaje de acierto y qué distractor fue el más elegido?
def reactivo_mas_dificil(doc: dict[str, Any]) -> dict[str, Any] | None:
    reactivos = [r for r in doc.get("reactivos") or [] if r["resumen"].get("pct_acierto") is not None]
    if not reactivos:
        return None
    r = min(reactivos, key=lambda x: (x["resumen"]["pct_acierto"], x["id"]))
    return {"reactivo_id": r["id"], "texto": r["texto"], "pct_acierto": r["resumen"]["pct_acierto"],
            "distractor_mas_elegido": r["resumen"]["distractor_mas_elegido"]}


# 6b. ¿Qué alumnos fallaron los reactivos del KPI X?
def alumnos_que_fallaron_kpi(doc: dict[str, Any], kpi: str) -> dict[str, list[str]]:
    """{reactivo_id: [alumnos que no lo acertaron (incorrecta, nula o sin respuesta)]}."""
    ids = [r["id"] for r in doc.get("reactivos") or [] if kpi in r.get("kpis_relacionados", [])]
    salida: dict[str, list[str]] = {i: [] for i in ids}
    for a in doc.get("alumnos") or []:
        for x in a["respuestas"]:
            if x["reactivo_id"] in salida and x.get("correcta") is False:
                salida[x["reactivo_id"]].append(a["id"])
    return salida


# 7. ¿Qué dijo el participante E02 sobre el tema Y?
def dijo(doc: dict[str, Any], participante: str, tema: str) -> list[dict[str, Any]]:
    objetivo, buscado = _id(doc, participante), _norm(tema)
    e = next((x for x in doc.get("entrevistas") or [] if x["participante"] == objetivo), None)
    if e is None:
        return []
    return [{"pregunta_id": i.get("pregunta_id"), "pregunta": i["pregunta"], "respuesta": i["respuesta"]}
            for i in e["intercambios"] if buscado in _norm(i["pregunta"]) or buscado in _norm(i["respuesta"])]
