"""Documento final de una prueba estandarizada.

Indagata NO califica las pruebas: no hay respuesta correcta, aciertos ni puntaje. El
documento describe lo que respondieron los alumnos:
  - reactivos: texto y opciones (si hay instrumento original), KPIs relacionados y resumen
               (distribución de respuestas, opción más elegida, opciones que nadie eligió,
               nulas, sin respuesta y media en los reactivos numéricos).
  - alumnos:   A001, A002… (IDs anónimos: la matrícula NUNCA entra), contexto (turno…),
               cuántos reactivos respondió, nulas, sin respuesta y sus respuestas interpretadas.

Los registros anulados por ID repetido (motivo «duplicado») no se incluyen como
alumnos: son la copia anulada de otro registro (se avisa cuántos).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from services.documento import comun
from services.estructura import Estructura
from services.interpretacion import pruebas
from services.interpretacion.privacidad import es_dato_personal

ESQUEMA_VERSION = "2.0"
_NUMERICOS = {"puntos", "escala", "numerica"}
_CERRADOS = {"opcion_multiple", "verdadero_falso"}


def construir(perfil: dict[str, Any], estructura: Estructura, reporte: dict[str, Any], filas: list[dict[str, str]]) -> dict[str, Any]:
    ins = perfil["instrumento_id"]
    esp = (reporte.get("especifico") or {}).get("prueba_estandarizada") or {}
    analisis = {r.get("pregunta"): r for r in ((reporte.get("estadistica") or {}).get("despues") or {}).get("reactivos") or []}
    kpis_de = comun.kpis_por_pregunta(perfil.get("kpis_asociados") or [])
    avisos: list[dict[str, Any]] = []

    contexto_cols = [c for c in esp.get("columnas_contexto") or [] if not es_dato_personal(c.get("etiqueta") or c.get("id") or "")]
    reactivo_de = {p.columna: p for p in estructura.preguntas if p.columna}

    # Alumnos en orden de aparición, con ID anónimo. Se saltan las copias anuladas por duplicado.
    alumnos: dict[tuple[str, int], dict[str, Any]] = {}
    vistas: Counter = Counter()  # (id_alumno, reactivo) → veces vista
    duplicadas = 0
    for f in filas:
        if (f.get("motivo") or "") == "duplicado":
            duplicadas += 1
            continue
        p = reactivo_de.get(f.get("pregunta") or "")
        if p is None:
            continue
        id_original = f.get("id_alumno") or ""
        # Si el investigador conservó un ID repetido, cada aparición es un alumno distinto.
        aparicion = vistas[(id_original, p.id)]
        vistas[(id_original, p.id)] += 1
        alumno = alumnos.get((id_original, aparicion))
        if alumno is None:
            alumno = {"id": f"{ins}-A{len(alumnos) + 1:03d}",
                      "contexto": {c.get("etiqueta") or c["id"]: (f.get(c["id"]) or None) for c in contexto_cols},
                      "respuestas": {}}
            alumnos[(id_original, aparicion)] = alumno
        alumno["respuestas"][p.id] = {"reactivo_id": p.id, "pregunta": p.texto,
                                      **pruebas.interpretar(f, p.letras, p.tipo or "opcion_multiple", p.puntos_max)}
    if duplicadas:
        avisos.append({"codigo": "duplicados_excluidos", "n": duplicadas,
                       "mensaje": f"{duplicadas} respuesta(s) de registros repetidos (anulados por duplicado) no se incluyen."})

    lista_alumnos = []
    for a in alumnos.values():
        respuestas = [a["respuestas"][p.id] for p in estructura.preguntas if p.id in a["respuestas"]]
        estados = Counter(r["estado"] for r in respuestas)
        lista_alumnos.append({"id": a["id"], "contexto": a["contexto"], "n_respondidas": estados.get("valida", 0),
                              "n_nulas": estados.get("nula", 0), "n_sin_respuesta": estados.get("sin_respuesta", 0),
                              "respuestas": respuestas})

    reactivos = []
    for p in estructura.preguntas:
        resps = [a["respuestas"][p.id] for a in alumnos.values() if p.id in a["respuestas"]]
        tipo = p.tipo or "opcion_multiple"
        item = {
            "id": p.id,
            "seccion_id": p.seccion_id,
            "clave": p.columna or "",
            "texto": p.texto,
            "tipo_reactivo": tipo,
            "opciones": dict(p.letras),
            "kpis_relacionados": kpis_de.get(p.id, []),
            "resumen": _resumen(resps, p.letras, analisis.get(p.columna), tipo, p.puntos_max),
        }
        if p.puntos_max is not None:
            item["puntos_max"] = p.puntos_max
        reactivos.append(item)

    usadas = {p.seccion_id for p in estructura.preguntas}
    return {
        "esquema_version": ESQUEMA_VERSION,
        "instrumento": comun.instrumento(perfil, n_alumnos=len(lista_alumnos)),
        "kpis_asociados": perfil.get("kpis_asociados") or [],
        "secciones": comun.secciones(estructura, usadas),
        "reactivos": reactivos,
        "alumnos": lista_alumnos,
        "avisos": avisos,
    }


def _clave_opcion(r: dict[str, Any], tipo: str) -> str:
    """Cómo se agrupa una respuesta válida: la letra en opción múltiple; el significado en el resto."""
    if tipo == "opcion_multiple":
        return (r.get("respuesta") or "").upper()
    if tipo in _NUMERICOS:
        return r.get("respuesta") or ""
    return r.get("significado") or r.get("respuesta") or ""


def _resumen(resps: list[dict[str, Any]], letras: dict[str, str], analisis: dict[str, Any] | None,
             tipo: str = "opcion_multiple", puntos_max: int | None = None) -> dict[str, Any]:
    """Qué respondieron los alumnos en un reactivo (sin calificar)."""
    n = len(resps)
    validas = [r for r in resps if r["estado"] == "valida"]
    conteo = Counter(_clave_opcion(r, tipo) for r in validas)
    significado = {_clave_opcion(r, tipo): r.get("significado") or r.get("respuesta") or "" for r in validas}
    n_nulas = sum(1 for r in resps if r["estado"] == "nula")
    n_sin = sum(1 for r in resps if r["estado"] == "sin_respuesta")

    if tipo == "opcion_multiple" and letras:
        orden = list(letras)  # A, B, C, D en el orden del original
    else:
        orden = [o for o, _ in conteo.most_common()]
    distribucion = {o: {"n": conteo.get(o, 0), "pct": comun.pct(conteo.get(o, 0), n)} for o in orden if conteo.get(o, 0) or tipo in _CERRADOS}
    for o, c in conteo.most_common():  # opciones elegidas que el original no lista
        distribucion.setdefault(o, {"n": c, "pct": comun.pct(c, n)})
    if n_nulas:
        distribucion["nula"] = {"n": n_nulas, "pct": comun.pct(n_nulas, n)}
    if n_sin:
        distribucion["NR"] = {"n": n_sin, "pct": comun.pct(n_sin, n)}

    mas = None
    if conteo:
        primero = max(conteo.items(), key=lambda x: (x[1], -orden.index(x[0]) if x[0] in orden else 0))
        texto = letras.get(primero[0]) if tipo == "opcion_multiple" else significado.get(primero[0])
        mas = {"opcion": primero[0], "significado": texto or f"Opción {primero[0]}", "n": primero[1], "pct": comun.pct(primero[1], n)}

    sin_elegir = list((analisis or {}).get("opciones_sin_elegir") or [])
    if not sin_elegir and tipo == "opcion_multiple" and letras:
        sin_elegir = [o for o in letras if not conteo.get(o)]

    media = None
    if tipo in _NUMERICOS:
        numeros = []
        for r in validas:
            try:
                numeros.append(float(str(r.get("respuesta")).replace(",", ".")))
            except ValueError:
                pass
        media = round(sum(numeros) / len(numeros), 2) if numeros else None

    if mas is None:
        texto = "Sin respuestas válidas."
    elif tipo in _NUMERICOS and media is not None:
        texto = f"Media {comun._fmt(media)}" + (f" de {puntos_max} puntos." if tipo == "puntos" and puntos_max else
                                               f" en escala 1–{puntos_max}." if tipo == "escala" and puntos_max else ".")
        texto += f" La respuesta más frecuente fue «{mas['significado']}» ({comun._fmt(mas['pct'])} %)."
    else:
        etiqueta = f"{mas['opcion']}) {mas['significado']}" if tipo == "opcion_multiple" and letras.get(mas["opcion"]) else mas["significado"]
        texto = f"La opción más elegida fue «{etiqueta}» ({comun._fmt(mas['pct'])} % de los alumnos)."
    if n_nulas or n_sin:
        texto += f" {n_nulas + n_sin} sin respuesta válida ({comun._fmt(comun.pct(n_nulas + n_sin, n))} %)."
    if sin_elegir:
        texto += f" Nadie eligió: {', '.join(sin_elegir)}."
    return {
        "n_alumnos": n,
        "distribucion": distribucion,
        "opcion_mas_elegida": mas,
        "opciones_sin_elegir": sin_elegir,
        "n_nulas": n_nulas,
        "n_sin_respuesta": n_sin,
        "media": media,
        "interpretacion": texto,
    }
