"""Consultas simples y determinísticas sobre el documento final (sin LLM).

Demuestran que el documento contiene todo lo necesario para responder las preguntas
de los criterios de aceptación. Las usan knowledge-service (pruebas de criterios) y la
ruta estructurada del chat (visualization-service, `services/enrutador.py`).

Los IDs se aceptan completos («INS-0012-R017») o cortos («R017», «p03», «KPI-07»).
"""
from __future__ import annotations

import unicodedata
from collections import Counter
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


# 7. ¿Qué dijo el participante E02 sobre el tema Y?
def dijo(doc: dict[str, Any], participante: str, tema: str) -> list[dict[str, Any]]:
    objetivo, buscado = _id(doc, participante), _norm(tema)
    e = next((x for x in doc.get("entrevistas") or [] if x["participante"] == objetivo), None)
    if e is None:
        return []
    return [{"pregunta_id": i.get("pregunta_id"), "pregunta": i["pregunta"], "respuesta": i["respuesta"]}
            for i in e["intercambios"] if buscado in _norm(i["pregunta"]) or buscado in _norm(i["respuesta"])]


# 8. Respondentes que cumplen condiciones sobre sus respuestas («los que sí reprobaron por falta de tiempo»).
_OPERADORES = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b}


def _numero(valor: Any) -> float | None:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def cumple(respuesta: dict[str, Any] | None, condicion: dict[str, Any]) -> bool:
    """¿La respuesta cumple la condición?

    `{"nivel": "acuerdo"}`, `{"valores": [...]}` (significados) o `{"comparacion": [op, n]}`.
    """
    if not respuesta or respuesta.get("estado") != "respondida":
        return False
    if condicion.get("nivel"):
        return respuesta.get("nivel") == condicion["nivel"]
    if condicion.get("valores"):
        aceptados = {_norm(v) for v in condicion["valores"]}
        # Selección múltiple: basta con que una de las opciones marcadas sea la pedida. Antes se comparaba el
        # texto completo («Biblioteca, Tutorías») y solo contaban quienes marcaron ÚNICAMENTE esa opción
        # (24 oct, banco de preguntas: 45 en lugar de 93 en «¿cuántos usaron la biblioteca?»).
        if isinstance(respuesta.get("seleccion"), list):
            return any(_norm(s) in aceptados for s in respuesta["seleccion"])
        return _norm(respuesta.get("significado") or respuesta.get("valor") or "") in aceptados
    if condicion.get("comparacion"):
        op, n = condicion["comparacion"]
        valor = _numero(respuesta.get("valor"))
        return valor is not None and _OPERADORES[op](valor, float(n))
    return False


def filtrar(doc: dict[str, Any], condiciones: list[dict[str, Any]], contexto: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Respondentes del grupo (contexto) que cumplen TODAS las condiciones, en orden de ID.

    Cada condición: `{"pregunta_id": "p13", "valores": ["Sí, una vez", …]}` o
    `{"pregunta_id": "p17", "comparacion": [">", 20]}`.
    """
    objetivo = [{**c, "pregunta_id": _id(doc, c["pregunta_id"])} for c in condiciones]
    filtro = {_norm(k): _norm(v) for k, v in (contexto or {}).items()}
    salida = []
    for r in doc.get("respondentes") or []:
        ctx = {_norm(k): _norm(v) for k, v in (r.get("contexto") or {}).items() if v is not None}
        if any(ctx.get(k) != v for k, v in filtro.items()):
            continue
        por_pregunta = {x["pregunta_id"]: x for x in r["respuestas"]}
        if all(cumple(por_pregunta.get(c["pregunta_id"]), c) for c in objetivo):
            salida.append(r)
    return sorted(salida, key=lambda r: r["id"])


# 9. ¿Cuántos entrevistados dicen que sí (o no) a la pregunta X y qué motivos dan? (esquema 2.1)
def posturas(doc: dict[str, Any], pregunta_id: str) -> dict[str, Any]:
    """Posturas de los intercambios con análisis de respuesta para una pregunta del guion."""
    objetivo = _id(doc, pregunta_id)
    detalle = []
    for e in doc.get("entrevistas") or []:
        for i in e.get("intercambios") or []:
            an = i.get("analisis") or {}
            if i.get("pregunta_id") == objetivo and an.get("nucleo"):
                detalle.append({"participante": e["participante"], "postura": an.get("postura") or "sin_determinar",
                                "motivo": an.get("motivo") or "", "nucleo": an["nucleo"], "revisado": an.get("estado") == "revisado"})
    return {"total": len(detalle), "conteo": dict(Counter(d["postura"] for d in detalle)), "detalle": detalle}
