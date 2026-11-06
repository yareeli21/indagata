"""Chunks del RAG a partir del DOCUMENTO FINAL vigente (knowledge-service).

El documento final ya trae las respuestas interpretadas (significado, no códigos),
los resúmenes precalculados y los KPIs aceptados con su justificación. Aquí solo se
convierte cada unidad con sentido propio en uno o más chunks:

  Encuesta    → ficha · una `pregunta` por pregunta (con su resumen) · uno o más
                `respondente` por persona (contexto + respuestas) · un `kpi` por KPI
  Prueba      → ficha · un `reactivo` por reactivo (distribución, opción más elegida) ·
                `alumno` por alumno (sus respuestas por significado) · `kpi`
                (las pruebas no se califican: no hay respuesta correcta ni puntaje)
  Entrevista  → ficha · una `pregunta` por pregunta guía · un `intercambio` por par
                pregunta-respuesta de cada participante · `kpi`

Reglas no obvias:
  - Ningún chunk excede `VENTANA` (450 caracteres): el modelo de embeddings solo
    vectoriza ~128 tokens. Si una unidad no cabe, se trocea y CADA pieza repite su
    prefijo (quién o qué es), para que ninguna pieza quede sin contexto.
  - La ficha va en la sección `encabezado` y siempre es el chunk 0: visualization-
    service la usa para comparar instrumentos.
  - Los IDs se muestran cortos en el texto («R017», «p04») y completos en la
    metadata (`INS-0012-R017`), que es lo que se filtra.
"""
from __future__ import annotations

import json
from typing import Any

from services.chroma_indexer import VENTANA, Chunk, trocear

# Texto de la pregunta dentro del chunk de un respondente: lo justo para reconocerla.
# Con 70 caracteres, una encuesta de 200 personas × 46 preguntas daba ~2,400 chunks
# (minutos de vectorización en CPU); con 40, ~1,400. El texto completo está en el
# chunk de cada pregunta y las consultas por persona van por la ruta estructurada.
_MAX_PREGUNTA_EN_RESPUESTA = 40
_MAX_TEXTO_PREFIJO = 160


def corto(id_completo: str) -> str:
    """«INS-0012-R017» → «R017» (lo que el usuario escribe en el chat)."""
    return str(id_completo or "").rsplit("-", 1)[-1]


def _recortar(texto: Any, n: int) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= n else texto[: n - 1].rstrip() + "…"


def _por_lineas(cuerpo: str, ventana: int) -> list[str]:
    """Empaca líneas completas, sin solape (listas: respuestas de una persona).

    Repetir media línea de la pieza anterior («…semestre»: En desacuerdo) confunde más
    de lo que ayuda en una lista; solo una línea que por sí sola no cabe se trocea.
    """
    piezas: list[str] = []
    actual = ""
    for linea in cuerpo.splitlines():
        for parte in [linea] if len(linea) <= ventana else trocear(linea, ventana=ventana, solape=0):
            candidato = f"{actual}\n{parte}" if actual else parte
            if len(candidato) <= ventana:
                actual = candidato
            else:
                piezas.append(actual)
                actual = parte
    return piezas + ([actual] if actual else [])


def _piezas(prefijo: str, cuerpo: str, lista: bool = False) -> list[str]:
    """Cuerpo troceado para que `prefijo + pieza` nunca exceda VENTANA."""
    prefijo = prefijo.rstrip() + "\n"
    if len(prefijo) + len(cuerpo) <= VENTANA:
        return [prefijo + cuerpo] if cuerpo.strip() else [prefijo.strip()]
    ventana = VENTANA - len(prefijo)
    piezas = _por_lineas(cuerpo, ventana) if lista else trocear(cuerpo, ventana=ventana, solape=60)
    return [prefijo + t for t in piezas] or [prefijo.strip()]


def _chunks(prefijo: str, cuerpo: str, seccion: str, *, lista: bool = False, **meta: Any) -> list[Chunk]:
    extra = {k: v for k, v in meta.items() if k not in ("pregunta_id", "pregunta")}
    return [
        Chunk(texto=t, seccion=seccion, pregunta_id=meta.get("pregunta_id", ""), pregunta=meta.get("pregunta", ""), extra=extra)
        for t in _piezas(prefijo, cuerpo, lista)
    ]


def _contexto(ctx: dict[str, Any] | None) -> str:
    pares = [f"{k}: {v}" for k, v in (ctx or {}).items() if v not in (None, "")]
    return f" ({'; '.join(pares)})" if pares else ""


def _kpis_json(ids: list[str] | None) -> str:
    return json.dumps(list(ids or []), ensure_ascii=False)


# ── Ficha y KPIs (comunes) ─────────────────────────────────────────────────────


_SIN_TEMA = {"general", "otras preguntas del archivo"}
_ETIQUETA_ASPECTOS = "Aspectos que pregunta: "
_MAX_ASPECTOS = 600  # el chat recibe la ficha completa (todas sus piezas), no solo la primera


def _aspectos_sin_secciones(doc: dict[str, Any], maximo: int) -> str:
    """Encuesta sin secciones con nombre: lo que pregunta, desde los textos de sus preguntas.

    Con secciones, sus nombres ya dicen qué evalúa (van en «Temas»). Sin ellas, la ficha
    quedaba sin contenido y el modelo describía el instrumento por sus KPIs. Va junto al
    objetivo, recortado a `maximo` caracteres.
    """
    secciones = [s.get("nombre", "") for s in doc.get("secciones") or []]
    if not doc.get("respondentes") or any(" ".join(s.lower().split()) not in _SIN_TEMA for s in secciones):
        return ""
    salida = ""
    for p in doc.get("preguntas") or []:
        texto = _recortar(" ".join(str(p.get("texto") or "").split()).rstrip(".?¿"), 60)
        siguiente = f"{salida}; {texto}" if salida else texto
        if len(siguiente) + 3 > maximo:
            return f"{salida}; …" if salida else ""
        salida = siguiente
    return salida


def _ficha(doc: dict[str, Any], tipo_ui: str) -> list[Chunk]:
    ins = doc.get("instrumento") or {}
    titulo = _recortar(ins.get("titulo") or "Instrumento", 120)
    lineas = [f"Tipo: {tipo_ui}"]
    for etiqueta, clave in (("Objetivo", "objetivo"), ("Población", "poblacion"), ("Nivel educativo", "nivel_educativo"),
                            ("Contexto", "contexto")):
        if ins.get(clave) and ins.get(clave) != "No especificado":
            lineas.append(f"{etiqueta}: {ins[clave]}")
        if clave == "objetivo" and (aspectos := _aspectos_sin_secciones(doc, _MAX_ASPECTOS)):
            lineas.append(_ETIQUETA_ASPECTOS + aspectos)
    temas = [str(t) for t in ins.get("temas") or [] if str(t).strip() and str(t) != "No especificado"]
    if temas:
        lineas.append("Temas: " + ", ".join(temas))
    for etiqueta, clave in (("Respondentes", "n_respondentes"), ("Alumnos", "n_alumnos")):
        if ins.get(clave) is not None:
            lineas.append(f"{etiqueta}: {ins[clave]}")
    if doc.get("entrevistas") is not None:
        lineas.append(f"Entrevistas: {len(doc['entrevistas'])}")
    nombres = [k.get("nombre") for k in doc.get("kpis_asociados") or [] if k.get("nombre")]
    # Se dice también cuando no hay: sin esta línea, al comparar instrumentos el modelo
    # atribuía a uno los KPIs del otro (verificación de la Fase 5).
    lineas.append("KPIs asociados: " + (", ".join(nombres) if nombres else "ninguno"))
    return _chunks(f"Instrumento: {titulo}", "\n".join(lineas), "encabezado")


def _kpis(doc: dict[str, Any], textos: dict[str, str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for k in doc.get("kpis_asociados") or []:
        evidencia = [e.get("pregunta_id") for e in k.get("evidencia") or [] if e.get("pregunta_id")]
        cuerpo = [f"Definición: {k['definicion']}" if k.get("definicion") else "",
                  f"Qué mide: {k['que_mide']}" if k.get("que_mide") else "",
                  f"Por qué se asoció a este instrumento: {k['justificacion']}" if k.get("justificacion") else ""]
        if evidencia:
            cuerpo.append("Preguntas que lo sustentan: " + "; ".join(
                f"{corto(p)} «{_recortar(textos.get(p, ''), 80)}»" for p in evidencia))
        chunks += _chunks(f"KPI: {k.get('nombre') or k.get('kpi_id')}", "\n".join(c for c in cuerpo if c), "kpi",
                          kpiId=str(k.get("kpi_id") or ""), kpisChunk=_kpis_json([k.get("nombre") or ""]))
    return chunks


def _nombres_kpi(doc: dict[str, Any]) -> dict[str, str]:
    return {str(k.get("kpi_id")): k.get("nombre") or str(k.get("kpi_id")) for k in doc.get("kpis_asociados") or []}


# ── Encuesta ───────────────────────────────────────────────────────────────────


def _resumen_pregunta(resumen: dict[str, Any]) -> str:
    partes = [f"Respuestas válidas: {resumen.get('n_validas', 0)}; sin respuesta: {resumen.get('n_sin_respuesta', 0)}"]
    dist = resumen.get("distribucion") or []
    if dist:
        partes.append("Distribución: " + "; ".join(f"{d['significado']} {d['pct']} % (n={d['n']})" for d in dist))
    if resumen.get("por_nivel"):
        partes.append("Por nivel: " + ", ".join(f"{k} {v} %" for k, v in resumen["por_nivel"].items()))
    if resumen.get("media") is not None:
        partes.append(f"Media: {resumen['media']}; mediana: {resumen.get('mediana')}")
    if resumen.get("interpretacion"):
        partes.append(resumen["interpretacion"])
    return "\n".join(partes)


def _encuesta(doc: dict[str, Any]) -> list[Chunk]:
    secciones = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    nombres_kpi = _nombres_kpi(doc)
    textos = {p["id"]: p.get("texto", "") for p in doc.get("preguntas") or []}
    chunks: list[Chunk] = []
    for p in doc.get("preguntas") or []:
        kpis = [nombres_kpi.get(str(k), str(k)) for k in p.get("kpis_relacionados") or []]
        cuerpo = _resumen_pregunta(p.get("resumen") or {})
        if kpis:
            cuerpo += "\nKPIs que mide: " + ", ".join(kpis)
        seccion = secciones.get(p.get("seccion_id"), "")
        prefijo = f"Pregunta {corto(p['id'])}: {_recortar(p.get('texto'), _MAX_TEXTO_PREFIJO)}"
        chunks += _chunks(prefijo, cuerpo, "pregunta", pregunta_id=p["id"], pregunta=_recortar(p.get("texto"), 300),
                          seccionInstrumento=seccion, kpisChunk=_kpis_json(kpis))
    for r in doc.get("respondentes") or []:
        lineas = []
        for x in r.get("respuestas") or []:
            if x.get("estado") == "respondida":
                valor = x.get("significado") if x.get("significado") not in (None, "") else x.get("valor")
            elif x.get("estado") == "no_interpretada":
                valor = f"valor no interpretable ({x.get('valor')})"
            else:
                valor = f"sin respuesta ({x.get('motivo') or x.get('estado')})"
            lineas.append(f"{corto(x['pregunta_id'])} «{_recortar(x.get('pregunta'), _MAX_PREGUNTA_EN_RESPUESTA)}»: {valor}")
        chunks += _chunks(f"Respondente {corto(r['id'])}{_contexto(r.get('contexto'))}", "\n".join(lineas), "respondente", lista=True,
                          respondenteId=r["id"])
    return chunks + _kpis(doc, textos)


# ── Prueba estandarizada ───────────────────────────────────────────────────────


def _prueba(doc: dict[str, Any]) -> list[Chunk]:
    nombres_kpi = _nombres_kpi(doc)
    secciones = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    textos = {r["id"]: r.get("texto", "") for r in doc.get("reactivos") or []}
    chunks: list[Chunk] = []
    for r in doc.get("reactivos") or []:
        res = r.get("resumen") or {}
        opciones = r.get("opciones") or {}
        cuerpo = []
        if opciones:
            cuerpo.append("Opciones: " + "; ".join(f"{k}) {v}" for k, v in opciones.items()))
        mas = res.get("opcion_mas_elegida")
        if mas:
            cuerpo.append(f"Opción más elegida: {mas['opcion']} ({mas.get('significado')}), {mas['pct']} % de {res.get('n_alumnos')} alumnos")
        dist = res.get("distribucion") or {}
        if dist:
            cuerpo.append("Distribución: " + "; ".join(f"{k} {v['pct']} %" for k, v in dist.items()))
        if res.get("media") is not None:
            cuerpo.append(f"Media: {res['media']}")
        if res.get("opciones_sin_elegir"):
            cuerpo.append("Nadie eligió: " + ", ".join(res["opciones_sin_elegir"]))
        kpis = [nombres_kpi.get(str(k), str(k)) for k in r.get("kpis_relacionados") or []]
        if kpis:
            cuerpo.append("KPIs que mide: " + ", ".join(kpis))
        prefijo = f"Reactivo {corto(r['id'])}: {_recortar(r.get('texto'), _MAX_TEXTO_PREFIJO)}"
        chunks += _chunks(prefijo, "\n".join(cuerpo), "reactivo", pregunta_id=r["id"], pregunta=_recortar(r.get("texto"), 300),
                          seccionInstrumento=secciones.get(r.get("seccion_id"), ""), kpisChunk=_kpis_json(kpis))
    for a in doc.get("alumnos") or []:
        lineas = []
        for x in a.get("respuestas") or []:
            respuesta = x.get("respuesta") or "sin respuesta"
            significado = f" ({x['significado']})" if x.get("significado") else ""
            estado = "" if x.get("estado") in (None, "valida") else f" [{x['estado'].replace('_', ' ')}]"
            lineas.append(f"{corto(x['reactivo_id'])}: {respuesta}{significado}{estado}")
        prefijo = (f"Alumno {corto(a['id'])}{_contexto(a.get('contexto'))}: respondió {a.get('n_respondidas', 0)} reactivos"
                   + (f", {a['n_nulas']} nulas" if a.get("n_nulas") else "")
                   + (f", {a['n_sin_respuesta']} sin respuesta" if a.get("n_sin_respuesta") else ""))
        chunks += _chunks(prefijo, "\n".join(lineas), "alumno", lista=True, respondenteId=a["id"])
    return chunks + _kpis(doc, textos)


# ── Entrevista ─────────────────────────────────────────────────────────────────


_MARCO = {"actual": "presente", "pasado": "pasado", "hipotetico": "supuesto", "general": "general"}
_POSTURA = {"si": "sí", "no": "no", "ambivalente": "ambivalente", "no_aplica": "no aplica", "sin_determinar": "sin determinar"}


def _cuerpo_intercambio(i: dict[str, Any]) -> str:
    """Con análisis (esquema 2.1): primero lo que responde a la pregunta y su postura, luego
    el antecedente (relato de otro momento) y la respuesta completa; sin análisis, la respuesta."""
    respuesta = f"Respuesta: {i.get('respuesta') or ''}"
    an = i.get("analisis") or {}
    if not an.get("nucleo"):
        return respuesta
    lineas = [f"Postura: {_POSTURA.get(an.get('postura'), an.get('postura'))} "
              f"(en {_MARCO.get(an.get('marco_pregunta'), 'presente')}). Responde: {an['nucleo']}"]
    if an.get("motivo"):
        lineas.append(f"Motivo: {an['motivo']}")
    for u in an.get("unidades") or []:
        if u.get("funcion") == "contexto":
            lineas.append(f"Antecedente ({_MARCO.get(u.get('marco_temporal'), 'general')}): {u['texto']}")
    return "\n".join([*lineas, respuesta])


def _entrevista(doc: dict[str, Any]) -> list[Chunk]:
    nombres_kpi = _nombres_kpi(doc)
    textos = {p["id"]: p.get("texto", "") for p in doc.get("preguntas") or []}
    chunks: list[Chunk] = []
    for p in doc.get("preguntas") or []:
        kpis = [nombres_kpi.get(str(k), str(k)) for k in p.get("kpis_relacionados") or []]
        cuerpo = "KPIs que mide: " + ", ".join(kpis) if kpis else ""
        chunks += _chunks(f"Pregunta guía {corto(p['id'])}: {_recortar(p.get('texto'), 300)}", cuerpo, "pregunta",
                          pregunta_id=p["id"], pregunta=_recortar(p.get("texto"), 300), kpisChunk=_kpis_json(kpis))
    for e in doc.get("entrevistas") or []:
        for i in e.get("intercambios") or []:
            pid = i.get("pregunta_id") or ""
            etiqueta = f"pregunta {corto(pid)}" if pid else "pregunta"
            prefijo = f"Participante {corto(e['participante'])}, {etiqueta}: {_recortar(i.get('pregunta'), _MAX_TEXTO_PREFIJO)}"
            an = i.get("analisis") or {}
            extra = {"postura": an["postura"], "marcoTemporal": an.get("marco_pregunta") or ""} if an.get("nucleo") else {}
            chunks += _chunks(prefijo, _cuerpo_intercambio(i), "intercambio", pregunta_id=pid,
                              pregunta=_recortar(i.get("pregunta"), 300), respondenteId=e["participante"], **extra)
    return chunks + _kpis(doc, textos)


_POR_TIPO = {"encuesta": _encuesta, "prueba_estandarizada": _prueba, "entrevista": _entrevista}


def construir(doc: dict[str, Any], tipo_ui: str) -> list[Chunk]:
    """Chunks del documento final; el primero siempre es la ficha (`encabezado`)."""
    tipo = (doc.get("instrumento") or {}).get("tipo") or ""
    cuerpo = _POR_TIPO.get(tipo)
    return _ficha(doc, tipo_ui) + (cuerpo(doc) if cuerpo else [])


def nombres_kpis(doc: dict[str, Any]) -> list[str]:
    """Nombres de los KPIs aceptados (metadata `kpis` de cada chunk)."""
    return [k["nombre"] for k in doc.get("kpis_asociados") or [] if k.get("nombre")]
