"""Documento final de una prueba estandarizada.

  - reactivos: texto y opciones (si hay instrumento original), respuesta correcta,
               KPIs relacionados y resumen (% de acierto, distribución A/B/C/D/nula/NR,
               distractor más elegido, dificultad y discriminación).
  - alumnos:   A001, A002… (IDs anónimos: la matrícula NUNCA entra), contexto (turno…),
               puntaje, total, porcentaje y sus respuestas interpretadas.

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

def construir(perfil: dict[str, Any], estructura: Estructura, reporte: dict[str, Any], filas: list[dict[str, str]]) -> dict[str, Any]:
    ins = perfil["instrumento_id"]
    esp = (reporte.get("especifico") or {}).get("prueba_estandarizada") or {}
    clave: dict[str, str] = esp.get("clave") or {}
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
    if esp.get("clave_origen") == "inferida":
        avisos.append({"codigo": "clave_inferida",
                       "mensaje": "La prueba no traía clave: la clave de respuestas se propuso a partir de los datos y la confirmó el investigador."})
    if duplicadas:
        avisos.append({"codigo": "duplicados_excluidos", "n": duplicadas,
                       "mensaje": f"{duplicadas} respuesta(s) de registros repetidos (anulados por duplicado) no se incluyen."})

    # El puntaje y el total solo cuentan los reactivos calificables (con respuesta correcta).
    total = sum(1 for p in estructura.preguntas if (p.tipo or "opcion_multiple") in _CALIFICABLES)
    lista_alumnos = []
    for a in alumnos.values():
        respuestas = [a["respuestas"][p.id] for p in estructura.preguntas if p.id in a["respuestas"]]
        puntaje = sum(1 for r in respuestas if r.get("correcta"))
        lista_alumnos.append({"id": a["id"], "contexto": a["contexto"], "puntaje": puntaje, "total": total,
                              "porcentaje": comun.pct(puntaje, total), "respuestas": respuestas})

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
            "calificable": tipo in _CALIFICABLES,
            "opciones": dict(p.letras),
            "respuesta_correcta": clave.get(p.columna or "", "") if tipo in _CALIFICABLES else "",
            "kpis_relacionados": kpis_de.get(p.id, []),
            "resumen": _resumen(resps, clave.get(p.columna or "", ""), p.letras, analisis.get(p.columna), tipo, p.puntos_max),
        }
        if p.puntos_max is not None:
            item["puntos_max"] = p.puntos_max
        reactivos.append(item)

    usadas = {p.seccion_id for p in estructura.preguntas}
    return {
        "esquema_version": "1.0",
        "instrumento": comun.instrumento(perfil, n_alumnos=len(lista_alumnos)),
        "kpis_asociados": perfil.get("kpis_asociados") or [],
        "secciones": comun.secciones(estructura, usadas),
        "reactivos": reactivos,
        "alumnos": lista_alumnos,
        "avisos": avisos,
    }


_CALIFICABLES = {"opcion_multiple", "verdadero_falso", "puntos"}


def _resumen(resps: list[dict[str, Any]], correcta: str, letras: dict[str, str], analisis: dict[str, Any] | None,
             tipo: str = "opcion_multiple", puntos_max: int | None = None) -> dict[str, Any]:
    n = len(resps)
    if tipo not in _CALIFICABLES:
        return _resumen_no_calificable(resps, tipo, puntos_max)
    conteo = Counter(
        (r["respuesta"] or "").upper() if r["estado"] == "valida" else ("nula" if r["estado"] == "nula" else "NR") for r in resps
    )
    aciertos = sum(1 for r in resps if r.get("correcta"))
    distractores = [(o, c) for o, c in conteo.most_common() if o not in (correcta, "nula", "NR")]
    distractor = None
    if distractores:
        o, c = distractores[0]
        distractor = {"opcion": o, "significado": letras.get(o) or f"Opción {o}", "pct": comun.pct(c, n)}
    pct_acierto = comun.pct(aciertos, n)
    texto = f"Lo acertó el {comun._fmt(pct_acierto)} % de los alumnos."
    if distractor:
        texto += f" El distractor más elegido fue «{distractor['opcion']}» ({comun._fmt(distractor['pct'])} %)."
    return {
        "n_alumnos": n,
        "pct_acierto": pct_acierto,
        "distribucion": {o: {"n": c, "pct": comun.pct(c, n)} for o, c in sorted(conteo.items())},
        "n_nulas": conteo.get("nula", 0),
        "n_sin_respuesta": conteo.get("NR", 0),
        "distractor_mas_elegido": distractor,
        "dificultad": (analisis or {}).get("dificultad"),
        "discriminacion": (analisis or {}).get("discriminacion"),
        "interpretacion": texto,
    }


def _resumen_no_calificable(resps: list[dict[str, Any]], tipo: str, puntos_max: int | None) -> dict[str, Any]:
    """Reactivos de autoinforme o abiertos (escala, Sí/No, numérico): distribución y media, sin acierto."""
    n = len(resps)
    validas = [r for r in resps if r["estado"] == "valida"]
    conteo = Counter(r.get("significado") or r.get("respuesta") or "" for r in validas)
    numeros = []
    for r in validas:
        try:
            numeros.append(float(str(r.get("respuesta")).replace(",", ".")))
        except ValueError:
            pass
    if tipo in ("escala", "numerica") and numeros:
        media = sum(numeros) / len(numeros)
        texto = f"Media {comun._fmt(media)}" + (f" en escala 1–{puntos_max}." if tipo == "escala" and puntos_max else ".")
    elif conteo:
        opcion, c = conteo.most_common(1)[0]
        texto = f"La respuesta más frecuente es «{opcion}» ({comun._fmt(comun.pct(c, len(validas)))} %)."
    else:
        texto = "Sin respuestas válidas."
    return {
        "n_alumnos": n,
        "pct_acierto": None,
        "distribucion": {o: {"n": c, "pct": comun.pct(c, n)} for o, c in conteo.most_common(15)},
        "n_nulas": sum(1 for r in resps if r["estado"] == "nula"),
        "n_sin_respuesta": sum(1 for r in resps if r["estado"] == "sin_respuesta"),
        "distractor_mas_elegido": None,
        "dificultad": None,
        "discriminacion": None,
        "interpretacion": texto + " Reactivo no calificable (sin respuesta correcta).",
    }
