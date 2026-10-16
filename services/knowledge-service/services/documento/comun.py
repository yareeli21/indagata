"""Piezas comunes del documento final: instrumento, KPIs, secciones y resúmenes.

Los resúmenes e interpretaciones se generan con PLANTILLAS determinísticas (nunca
con el LLM), para que el RAG no tenga que contar filas ni redactar cifras.
"""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from services.estructura import Estructura

# Cómo se nombra cada nivel en la interpretación («Predomina el acuerdo…»).
_NOMBRE_NIVEL = {
    "acuerdo": "el acuerdo", "desacuerdo": "el desacuerdo", "neutral": "la posición neutral",
    "satisfaccion": "la satisfacción", "insatisfaccion": "la insatisfacción",
    "alta": "el nivel alto", "media": "el nivel medio", "baja": "el nivel bajo",
    "si": "el «Sí»", "no": "el «No»",
}


def pct(n: int, total: int) -> float:
    return round(100 * n / total, 1) if total else 0.0


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}".rstrip("0").rstrip(".")


def instrumento(perfil: dict[str, Any], **conteos: int) -> dict[str, Any]:
    """Bloque `instrumento`: los campos descriptivos del perfil y los conteos del tipo."""
    campos = ("titulo", "objetivo", "temas", "palabras_clave", "nivel_educativo", "poblacion", "contexto")
    return {"id": perfil["instrumento_id"], "tipo": perfil["tipo"], **{c: perfil.get(c) or ([] if c in ("temas", "palabras_clave") else "") for c in campos}, **conteos}


def kpis_por_pregunta(kpis_asociados: list[dict[str, Any]]) -> dict[str, list[str]]:
    """{pregunta_id: [KPI-07…]}: la relación inversa de la evidencia de cada KPI aceptado."""
    salida: dict[str, list[str]] = {}
    for k in kpis_asociados:
        for e in k.get("evidencia") or []:
            lista = salida.setdefault(e["pregunta_id"], [])
            if k["kpi_id"] not in lista:
                lista.append(k["kpi_id"])
    return salida


def secciones(estructura: Estructura, usadas: set[str] | None = None) -> list[dict[str, Any]]:
    salida = []
    for s in estructura.secciones:
        if usadas is not None and s.id not in usadas:
            continue
        item: dict[str, Any] = {"id": s.id, "nombre": s.nombre}
        if s.descripcion:
            item["descripcion"] = s.descripcion
        salida.append(item)
    return salida


# ── Resumen de una pregunta de encuesta ────────────────────────────────────────


def resumen_pregunta(tipo: str, respuestas: list[dict[str, Any]], escala: dict[str, Any] | None) -> dict[str, Any]:
    """Distribución por significado y por nivel, porcentajes, media y una interpretación."""
    validas = [r for r in respuestas if r["estado"] == "respondida"]
    sin = [r for r in respuestas if r["estado"] == "sin_respuesta"]
    malas = sum(1 for r in respuestas if r["estado"] == "no_interpretada")
    n = len(validas)
    res: dict[str, Any] = {"n_validas": n, "n_sin_respuesta": len(sin)}
    motivos = Counter(r.get("motivo") or "en_blanco" for r in sin)
    if motivos and set(motivos) != {"en_blanco"}:
        res["sin_respuesta_por_motivo"] = dict(motivos)
    if malas:
        res["n_no_interpretadas"] = malas

    # Distribución por significado (en opción múltiple, cada opción elegida cuenta).
    if tipo in ("opcion_multiple_varias", "ranking"):
        conteo = Counter(o for r in validas for o in r.get("seleccion") or [])
    elif tipo in ("texto_corto", "texto_largo"):
        conteo = Counter()
    else:
        conteo = Counter(r.get("significado") for r in validas if r.get("significado"))
    orden = list((escala or {}).get("etiquetas", {}).values()) if tipo in ("likert", "cuadricula", "escala_lineal") else []
    claves = [o for o in orden if o in conteo] + [o for o, _ in conteo.most_common() if o not in orden]
    if tipo not in ("numerica", "calificacion") and claves:
        res["distribucion"] = [{"significado": k, "n": conteo[k], "pct": pct(conteo[k], n)} for k in claves]

    niveles = Counter(r["nivel"] for r in validas if r.get("nivel"))
    if niveles:
        res["por_nivel"] = {nv: pct(c, n) for nv, c in niveles.items()}

    numeros = [float(r["valor"]) for r in validas if isinstance(r.get("valor"), (int, float))]
    if numeros and tipo in ("likert", "cuadricula", "escala_lineal", "numerica", "calificacion"):
        res["media"] = round(statistics.fmean(numeros), 2)
        res["mediana"] = round(float(statistics.median(numeros)), 2)
        if tipo in ("numerica", "calificacion"):
            res["minimo"], res["maximo"] = min(numeros), max(numeros)
        recod = [float(r["valor_recodificado"]) for r in validas if "valor_recodificado" in r]
        if recod:
            res["media_recodificada"] = round(statistics.fmean(recod), 2)

    res["interpretacion"] = _interpretacion(tipo, res, escala, conteo)
    return res


def _interpretacion(tipo: str, res: dict[str, Any], escala: dict[str, Any] | None, conteo: Counter) -> str:
    n = res["n_validas"]
    if n == 0:
        return "Sin respuestas válidas."
    if res.get("por_nivel"):
        nivel, valor = max(res["por_nivel"].items(), key=lambda x: x[1])
        etiquetas_nivel = _etiquetas_de_nivel(nivel, escala)
        detalle = f" ({' o '.join(etiquetas_nivel)})" if etiquetas_nivel else ""
        if valor > 50:
            return f"Predomina {_NOMBRE_NIVEL.get(nivel, f'el nivel «{nivel}»')}: {_fmt(valor)} %{detalle.lower() if tipo != 'binaria' else ''}."
        partes = ", ".join(f"{_fmt(v)} % {k}" for k, v in sorted(res["por_nivel"].items(), key=lambda x: -x[1]))
        return f"Respuestas divididas: {partes}."
    if tipo in ("numerica", "calificacion"):
        return f"Media {_fmt(res['media'])}, mediana {_fmt(res['mediana'])} (de {_fmt(res['minimo'])} a {_fmt(res['maximo'])})."
    if tipo in ("texto_corto", "texto_largo"):
        return f"{n} respuesta{'s' if n != 1 else ''} abierta{'s' if n != 1 else ''}."
    if conteo:
        opcion, c = conteo.most_common(1)[0]
        if tipo in ("opcion_multiple_varias", "ranking"):
            return f"La opción más elegida es «{opcion}»: la eligió el {_fmt(pct(c, n))} % de quienes respondieron."
        return f"La opción más frecuente es «{opcion}» ({_fmt(pct(c, n))} % de las respuestas)."
    return f"{n} respuesta{'s' if n != 1 else ''}."


def _etiquetas_de_nivel(nivel: str, escala: dict[str, Any] | None) -> list[str]:
    if not escala or not escala.get("niveles") or not escala.get("etiquetas"):
        return []
    return [escala["etiquetas"].get(str(int(c)) if float(c).is_integer() else str(c), "") for c in escala["niveles"].get(nivel, [])]
