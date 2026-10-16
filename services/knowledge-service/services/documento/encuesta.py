"""Documento final de una encuesta.

  - preguntas:    definición (texto, sección, tipo, escala con niveles, opciones),
                  KPIs relacionados y un resumen precalculado; SIN repetir respuestas.
  - respondentes: R001, R002… (IDs anónimos, en el orden del archivo limpio), con su
                  contexto (turno, semestre…) y TODAS sus respuestas interpretadas, una
                  por pregunta (las faltantes como `sin_respuesta`). Cada respuesta lleva
                  también el TEXTO de su pregunta, para que se entienda sola (un chunk por
                  respondente debe poder leerse sin cruzarlo con la lista de preguntas).

Privacidad: las columnas con datos personales (nombre, correo, matrícula… por palabra
completa) nunca entran, ni como pregunta ni como contexto.
"""
from __future__ import annotations

from typing import Any

from services.documento import comun
from services.estructura import Estructura
from services.interpretacion.encuestas import interpretar_columna
from services.interpretacion.privacidad import es_dato_personal


def construir(perfil: dict[str, Any], estructura: Estructura, reporte: dict[str, Any], filas: list[dict[str, str]]) -> dict[str, Any]:
    ins = perfil["instrumento_id"]
    columnas = {c["id"]: c for c in ((reporte.get("especifico") or {}).get("encuesta") or {}).get("columnas") or []}
    avisos: list[dict[str, Any]] = []
    kpis_de = comun.kpis_por_pregunta(perfil.get("kpis_asociados") or [])
    n = len(filas)

    personales = sorted({c.get("etiqueta") or cid for cid, c in columnas.items() if c.get("estado") != "eliminada" and es_dato_personal(c.get("etiqueta") or cid)})
    if personales:
        avisos.append({"codigo": "datos_personales_excluidos", "mensaje": f"Columnas con datos personales excluidas del documento: {', '.join(personales)}.", "n": len(personales)})

    # Contexto del respondente: columnas con rol «contexto» que no son datos personales.
    contexto_cols = [
        (cid, c.get("etiqueta") or cid) for cid, c in columnas.items()
        if c.get("estado") != "eliminada" and c.get("rol") == "contexto" and not es_dato_personal(c.get("etiqueta") or cid)
    ]

    preguntas: list[dict[str, Any]] = []
    # (id, texto de la pregunta, respuestas): el texto viaja en cada respuesta para que se entienda sola.
    respuestas_por_pregunta: list[tuple[str, str, list[dict[str, Any]]]] = []
    for p in estructura.preguntas:
        spec = columnas.get(p.columna or "")
        item: dict[str, Any] = {"id": p.id, "seccion_id": p.seccion_id, "texto": p.texto}
        if p.grupo:
            item["grupo"] = p.grupo
        if p.aspecto:
            item["aspecto"] = p.aspecto
        if spec is None or es_dato_personal(spec.get("etiqueta") or ""):
            if spec is not None:
                continue  # dato personal: fuera del documento
            # Pregunta del instrumento original sin columna en el archivo.
            item.update(tipo="sin_datos", tipo_origen="original", kpis_relacionados=kpis_de.get(p.id, []),
                        resumen={"n_validas": 0, "n_sin_respuesta": 0, "interpretacion": "La pregunta no está en el archivo de respuestas."})
            if p.opciones:
                item["opciones"] = list(p.opciones)
            preguntas.append(item)
            continue
        valores = [f.get(p.columna or "", "") for f in filas]
        col = interpretar_columna(dict(spec, etiqueta=spec.get("etiqueta") or p.texto), valores, p.anclas)
        tipo = spec.get("tipo_canonico") or "texto_corto"
        item.update(tipo=tipo, tipo_origen="limpieza", kpis_relacionados=kpis_de.get(p.id, []))
        if col.opciones:
            item["opciones"] = col.opciones
        if col.escala:
            item["escala"] = col.escala
        item["resumen"] = comun.resumen_pregunta(tipo, col.respuestas, col.escala)
        if col.no_interpretadas:
            avisos.append({"codigo": "no_interpretadas", "pregunta_id": p.id, "n": col.no_interpretadas,
                           "mensaje": f"{col.no_interpretadas} respuesta(s) de «{p.texto[:80]}» no se pudieron interpretar (valor fuera de la escala o del tipo)."})
        preguntas.append(item)
        respuestas_por_pregunta.append((p.id, p.texto, col.respuestas))

    respondentes = []
    for i, fila in enumerate(filas):
        contexto = {etq: (fila.get(cid) or None) for cid, etq in contexto_cols}
        respuestas = [{"pregunta_id": pid, "pregunta": texto, **resps[i]} for pid, texto, resps in respuestas_por_pregunta]
        respondentes.append({"id": f"{ins}-R{i + 1:03d}", "contexto": contexto, "respuestas": respuestas})

    usadas = {p["seccion_id"] for p in preguntas}
    return {
        "esquema_version": "1.0",
        "instrumento": comun.instrumento(perfil, n_respondentes=n),
        "kpis_asociados": perfil.get("kpis_asociados") or [],
        "secciones": comun.secciones(estructura, usadas),
        "preguntas": preguntas,
        "respondentes": respondentes,
        "avisos": avisos,
    }
