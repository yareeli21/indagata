"""Chunks del RAG a partir del DOCUMENTO FINAL vigente (knowledge-service).

El documento final ya trae las respuestas interpretadas (significado, no códigos),
los resúmenes precalculados y los KPIs aceptados con su justificación. Aquí solo se
convierte cada unidad con sentido propio en uno o más chunks:

  Encuesta    → ficha · dos `pregunta` por pregunta (definición: texto completo y opciones o
                escala; resultados: distribución) · uno o más `respondente` por persona
                (contexto + respuestas) · un `kpi` por KPI
  Prueba      → ficha · dos `reactivo` por reactivo (definición: texto, sección y opciones;
                resultados: distribución y opción más elegida) · `alumno` por alumno (sus
                respuestas por significado) · `kpi` (las pruebas no se califican: no hay
                respuesta correcta ni puntaje)
  Entrevista  → ficha (con las indicaciones del entrevistador) · una `pregunta` por pregunta
                guía · un `intercambio` por par pregunta-respuesta de cada participante, con
                los temas y la valoración del análisis · `kpi`

Reglas no obvias:
  - **Se mide en tokens** (7 nov 2026). El modelo de embeddings solo lee `max_seq_length`
    (128) tokens; lo demás no se embebe. Con 450 caracteres fijos se truncaban el 92 % de
    los chunks de alumno y el 16 % de los de respondente (`evidencias/chunks_2026-11-07`).
    `construir(..., medir=)` recibe el contador del tokenizador del modelo; cada pieza se
    achica hasta caber. Sin contador (pruebas) se usa el límite de `VENTANA` caracteres.
  - Si una unidad no cabe, se trocea y CADA pieza repite su prefijo (quién o qué es, con el
    TEXTO COMPLETO de la pregunta), para que ninguna pieza quede sin contexto.
  - La definición de cada pregunta va en su propio chunk, sin cifras: «¿cuántos trabajan
    en algo relacionado con su carrera?» se parece a «¿Cuál es tu situación laboral?
    Opciones: … Trabajo en un área relacionada…», no a «Respuestas válidas: 1966…».
  - La ficha va en la sección `encabezado` y siempre es el chunk 0: visualization-
    service la usa para comparar instrumentos.
  - Los IDs se muestran cortos en el texto («R017», «p04») y completos en la
    metadata (`INS-0012-R017`), que es lo que se filtra.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from services.chroma_indexer import VENTANA, Chunk, trocear

# Texto de la pregunta dentro del chunk de un respondente: lo justo para reconocerla.
# Con 70 caracteres, una encuesta de 200 personas × 46 preguntas daba ~2,400 chunks
# (minutos de vectorización en CPU); con 40, ~1,400. El texto completo está en los
# chunks de cada pregunta y las consultas por persona van por la ruta estructurada.
_MAX_PREGUNTA_EN_RESPUESTA = 40
_MAX_TEXTO_PREFIJO = 400  # el texto completo de la pregunta; solo se recorta si no cabe en tokens
_MAX_TITULO = 50
_VENTANA_MINIMA = 60

Medidor = Callable[[str], int]
# Contador de tokens y límite del modelo, fijados por `construir` mientras arma un documento.
_medidor: ContextVar[tuple[Medidor, int] | None] = ContextVar("_medidor", default=None)


def corto(id_completo: str) -> str:
    """«INS-0012-R017» → «R017» (lo que el usuario escribe en el chat)."""
    return str(id_completo or "").rsplit("-", 1)[-1]


def _recortar(texto: Any, n: int) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= n else texto[: n - 1].rstrip() + "…"


def _cabe(texto: str) -> bool:
    medidor = _medidor.get()
    if medidor is None:
        return len(texto) <= VENTANA
    medir, limite = medidor
    return medir(texto) <= limite


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


def _prefijo_que_cabe(prefijo: str) -> str:
    """El prefijo debe dejar lugar al cuerpo: si solo él ya llena el modelo, se recorta su final."""
    while len(prefijo) > 40 and not _cabe(prefijo + " " + "x" * 80):
        prefijo = _recortar(prefijo, int(len(prefijo) * 0.85))
    return prefijo


def _piezas(prefijo: str, cuerpo: str, lista: bool = False) -> list[str]:
    """Cuerpo troceado para que `prefijo + pieza` quepa en el modelo (tokens) y en `VENTANA` (caracteres)."""
    prefijo = _prefijo_que_cabe(prefijo.rstrip()) + "\n"
    if not cuerpo.strip():
        return [prefijo.strip()]
    if len(prefijo) + len(cuerpo) <= VENTANA and _cabe(prefijo + cuerpo):
        return [prefijo + cuerpo]
    ventana = VENTANA - len(prefijo)
    while True:
        piezas = _por_lineas(cuerpo, ventana) if lista else trocear(cuerpo, ventana=ventana, solape=min(60, ventana // 4))
        salida = [prefijo + t for t in piezas] or [prefijo.strip()]
        if ventana <= _VENTANA_MINIMA or all(_cabe(t) for t in salida):
            return salida
        ventana = max(_VENTANA_MINIMA, int(ventana * 0.8))


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


def _titulo(doc: dict[str, Any]) -> str:
    return _recortar((doc.get("instrumento") or {}).get("titulo") or "Instrumento", _MAX_TITULO)


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
        lineas.append(f"Participantes entrevistados: {len(doc['entrevistas'])}")
        lineas.append(f"Preguntas de la guía: {len(doc.get('preguntas') or [])}")
    if doc.get("reactivos") is not None:
        lineas.append(_estructura_prueba(doc))
    if ins.get("encabezado"):
        # 7 nov: el encabezado de la transcripción (tipo de entrevista, modalidad, duración), del reporte de limpieza.
        lineas.append("Encabezado de la transcripción: " + "; ".join(ins["encabezado"]))
    if ins.get("indicaciones"):
        # 7 nov: lo que el entrevistador dice antes de su primera pregunta («Todo lo que digas es confidencial…»).
        lineas.append("Indicaciones del entrevistador: " + " ".join(ins["indicaciones"]))
    nombres = [k.get("nombre") for k in doc.get("kpis_asociados") or [] if k.get("nombre")]
    # Se dice también cuando no hay: sin esta línea, al comparar instrumentos el modelo
    # atribuía a uno los KPIs del otro (verificación de la Fase 5).
    lineas.append("KPIs asociados: " + (", ".join(nombres) if nombres else "ninguno"))
    return _chunks(f"Instrumento: {titulo}", "\n".join(lineas), "encabezado", lista=True)


def _estructura_prueba(doc: dict[str, Any]) -> str:
    """«Reactivos: 22 (Competencias básicas: 10; Verdadero o falso: 7; …)»."""
    nombres = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    por_seccion: dict[str, int] = {}
    for r in doc.get("reactivos") or []:
        nombre = nombres.get(r.get("seccion_id"), "")
        por_seccion[nombre] = por_seccion.get(nombre, 0) + 1
    detalle = "; ".join(f"{n}: {k}" for n, k in por_seccion.items() if n)
    return f"Reactivos: {len(doc.get('reactivos') or [])}" + (f" ({detalle})" if detalle else "")


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


def _opciones_encuesta(p: dict[str, Any]) -> str:
    """Opciones como las ve la persona, o los extremos de la escala («Escala 1 (Nada probable) a 5 (Muy probable)»)."""
    if p.get("opciones"):
        return "Opciones: " + "; ".join(str(o) for o in p["opciones"])
    etiquetas = (p.get("escala") or {}).get("etiquetas") or {}
    if etiquetas:
        puntos = sorted(etiquetas, key=lambda k: int(k) if str(k).isdigit() else 0)
        return f"Escala de {puntos[0]} ({etiquetas[puntos[0]]}) a {puntos[-1]} ({etiquetas[puntos[-1]]})"
    return ""


def _encuesta(doc: dict[str, Any]) -> list[Chunk]:
    secciones = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    nombres_kpi = _nombres_kpi(doc)
    textos = {p["id"]: p.get("texto", "") for p in doc.get("preguntas") or []}
    titulo = _titulo(doc)
    chunks: list[Chunk] = []
    for p in doc.get("preguntas") or []:
        kpis = [nombres_kpi.get(str(k), str(k)) for k in p.get("kpis_relacionados") or []]
        seccion = secciones.get(p.get("seccion_id"), "")
        texto = _recortar(p.get("texto"), _MAX_TEXTO_PREFIJO)
        meta = {"pregunta_id": p["id"], "pregunta": _recortar(p.get("texto"), 300), "seccionInstrumento": seccion,
                "kpisChunk": _kpis_json(kpis)}
        definicion = [f"Sección: {seccion}" if seccion and seccion.lower() not in _SIN_TEMA else "", _opciones_encuesta(p),
                      "KPIs que mide: " + ", ".join(kpis) if kpis else ""]
        chunks += _chunks(f"Pregunta {corto(p['id'])} (encuesta «{titulo}»): {texto}", "\n".join(x for x in definicion if x),
                          "pregunta", parte="definicion", **meta)
        chunks += _chunks(f"Pregunta {corto(p['id'])}: {texto}", _resumen_pregunta(p.get("resumen") or {}), "pregunta",
                          parte="resultados", **meta)
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
    titulo = _titulo(doc)
    chunks: list[Chunk] = []
    for r in doc.get("reactivos") or []:
        res = r.get("resumen") or {}
        opciones = r.get("opciones") or {}
        seccion = secciones.get(r.get("seccion_id"), "")
        kpis = [nombres_kpi.get(str(k), str(k)) for k in r.get("kpis_relacionados") or []]
        texto = _recortar(r.get("texto"), _MAX_TEXTO_PREFIJO)
        meta = {"pregunta_id": r["id"], "pregunta": _recortar(r.get("texto"), 300), "seccionInstrumento": seccion,
                "kpisChunk": _kpis_json(kpis)}
        definicion = [f"Sección: {seccion}" if seccion else "",
                      "Opciones: " + "; ".join(f"{k}) {v}" for k, v in opciones.items()) if opciones else "",
                      "KPIs que mide: " + ", ".join(kpis) if kpis else ""]
        chunks += _chunks(f"Reactivo {corto(r['id'])} (prueba «{titulo}»): {texto}", "\n".join(x for x in definicion if x),
                          "reactivo", parte="definicion", **meta)
        resultados = []
        mas = res.get("opcion_mas_elegida")
        if mas:
            resultados.append(f"Opción más elegida: {mas['opcion']} ({mas.get('significado')}), {mas['pct']} % de {res.get('n_alumnos')} alumnos")
        dist = res.get("distribucion") or {}
        if dist:
            resultados.append("Distribución: " + "; ".join(
                f"{k}{' (' + str(opciones[k]) + ')' if k in opciones else ''} {v['pct']} %" + (f" (n={v['n']})" if 'n' in v else "")
                for k, v in dist.items()))
        if res.get("n_sin_respuesta") or res.get("n_nulas"):
            resultados.append(f"Sin respuesta: {res.get('n_sin_respuesta') or 0}; nulas: {res.get('n_nulas') or 0}")
        if res.get("media") is not None:
            resultados.append(f"Media: {res['media']}")
        if res.get("opciones_sin_elegir"):
            resultados.append("Nadie eligió: " + ", ".join(res["opciones_sin_elegir"]))
        chunks += _chunks(f"Reactivo {corto(r['id'])}: {texto}", "\n".join(resultados), "reactivo", parte="resultados", **meta)
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
    """Con análisis (esquema 2.1): primero los temas y la valoración de lo que cuenta (7 nov), lo que responde a la
    pregunta y su postura, luego el antecedente (relato de otro momento) y la respuesta completa; sin análisis, la
    respuesta."""
    respuesta = f"Respuesta: {i.get('respuesta') or ''}"
    an = i.get("analisis") or {}
    lineas = []
    nlp = an.get("nlp") or {}
    temas = [t["tema"] for t in nlp.get("temas") or [] if t.get("tema")]
    if temas:
        lineas.append("Temas: " + "; ".join(temas))
    if (nlp.get("valoracion") or {}).get("valor"):
        lineas.append(f"Valoración: {nlp['valoracion']['valor']}")
    if an.get("nucleo"):
        lineas.append(f"Postura: {_POSTURA.get(an.get('postura'), an.get('postura'))} "
                      f"(en {_MARCO.get(an.get('marco_pregunta'), 'presente')}). Responde: {an['nucleo']}")
        if an.get("motivo"):
            lineas.append(f"Motivo: {an['motivo']}")
        for u in an.get("unidades") or []:
            if u.get("funcion") == "contexto":
                lineas.append(f"Antecedente ({_MARCO.get(u.get('marco_temporal'), 'general')}): {u['texto']}")
    return "\n".join([*lineas, respuesta])


def _entrevista(doc: dict[str, Any]) -> list[Chunk]:
    nombres_kpi = _nombres_kpi(doc)
    textos = {p["id"]: p.get("texto", "") for p in doc.get("preguntas") or []}
    titulo = _titulo(doc)
    chunks: list[Chunk] = []
    for p in doc.get("preguntas") or []:
        kpis = [nombres_kpi.get(str(k), str(k)) for k in p.get("kpis_relacionados") or []]
        cuerpo = "KPIs que mide: " + ", ".join(kpis) if kpis else ""
        chunks += _chunks(f"Pregunta guía {corto(p['id'])} (entrevista «{titulo}»): {_recortar(p.get('texto'), _MAX_TEXTO_PREFIJO)}",
                          cuerpo, "pregunta", pregunta_id=p["id"], pregunta=_recortar(p.get("texto"), 300), kpisChunk=_kpis_json(kpis))
    for e in doc.get("entrevistas") or []:
        for i in e.get("intercambios") or []:
            pid = i.get("pregunta_id") or ""
            etiqueta = f"pregunta guía {corto(pid)}" if pid else "pregunta"
            # El texto completo de la pregunta guía (si el intercambio tiene una) y no la del turno, que puede venir
            # recortada o con muletillas.
            texto = textos.get(pid) or i.get("pregunta") or ""
            prefijo = f"Participante {corto(e['participante'])}, {etiqueta}: {_recortar(texto, _MAX_TEXTO_PREFIJO)}"
            an = i.get("analisis") or {}
            extra = {"postura": an["postura"], "marcoTemporal": an.get("marco_pregunta") or ""} if an.get("nucleo") else {}
            chunks += _chunks(prefijo, _cuerpo_intercambio(i), "intercambio", pregunta_id=pid,
                              pregunta=_recortar(i.get("pregunta"), 300), respondenteId=e["participante"], **extra)
    return chunks + _kpis(doc, textos)


_POR_TIPO = {"encuesta": _encuesta, "prueba_estandarizada": _prueba, "entrevista": _entrevista}


def construir(doc: dict[str, Any], tipo_ui: str, medir: Medidor | None = None, limite: int = 128) -> list[Chunk]:
    """Chunks del documento final; el primero siempre es la ficha (`encabezado`).

    `medir(texto) -> tokens` (el tokenizador del modelo de embeddings) hace que ninguna pieza pase de `limite`
    tokens; sin él se usa el límite de `VENTANA` caracteres.
    """
    marca = _medidor.set((medir, limite) if medir else None)
    try:
        tipo = (doc.get("instrumento") or {}).get("tipo") or ""
        cuerpo = _POR_TIPO.get(tipo)
        return _ficha(doc, tipo_ui) + (cuerpo(doc) if cuerpo else [])
    finally:
        _medidor.reset(marca)


def nombres_kpis(doc: dict[str, Any]) -> list[str]:
    """Nombres de los KPIs aceptados (metadata `kpis` de cada chunk)."""
    return [k["nombre"] for k in doc.get("kpis_asociados") or [] if k.get("nombre")]
