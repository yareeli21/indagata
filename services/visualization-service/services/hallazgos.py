"""Candidatos a hallazgo («dame un dato interesante»): cifras calculadas sobre el documento final, sin LLM.

Etapa 2 del chat (28 oct). El ejecutor calcula aquí los candidatos; en la redacción el modelo elige el más
relevante y lo explica, pero las cifras salen siempre de este cálculo. Cada candidato trae:
    tipo       qué clase de hallazgo es (mayor_acuerdo, diferencia_grupos…);
    texto      la frase con su cifra, lista para citarse;
    puntaje    magnitud comparable entre tipos (0–100: puntos porcentuales o equivalente), para ordenarlos;
    preguntas  IDs completos de las preguntas en que se basa (fuentes de la respuesta).

Encuestas: mayor y menor acuerdo, mayor dispersión, diferencias entre grupos de contexto, opción dominante, mucha no
respuesta y bloques con fiabilidad baja (α de la limpieza). Pruebas (no se califican): reactivo donde más alumnos
coinciden, el más repartido y el de más respuestas nulas o vacías; nunca «el más difícil». Entrevistas: posturas y
palabras que más participantes usan.
"""
from __future__ import annotations

import math
from typing import Any

from shared.conocimiento import consultas

from services.dominio import normalizar

_POSITIVOS = ("acuerdo", "alta", "satisfaccion", "si")
_NEGATIVOS = ("desacuerdo", "baja", "insatisfaccion", "no")
_MIN_GRUPO = 10  # respondentes por grupo para comparar porcentajes
_MIN_DIFERENCIA = 10.0  # puntos porcentuales
_MAX_CANDIDATOS = 6


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _items(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return doc.get("preguntas") or doc.get("reactivos") or []


def _nivel_pct(resumen: dict[str, Any], claves: tuple[str, ...]) -> float | None:
    por_nivel = resumen.get("por_nivel") or {}
    return next((por_nivel[k] for k in claves if k in por_nivel), None)


def _nombre_nivel(resumen: dict[str, Any], claves: tuple[str, ...]) -> str:
    """«de acuerdo» / «en desacuerdo» si la escala es de acuerdo; «nivel alto» / «nivel bajo» en las demás
    (frecuencia, probabilidad…): en p05 «¿Con qué frecuencia…?» «en desacuerdo» no tenía sentido (28 oct)."""
    clave = next((k for k in claves if k in (resumen.get("por_nivel") or {})), "")
    return {"acuerdo": "de acuerdo", "desacuerdo": "en desacuerdo", "alta": "en el nivel alto", "baja": "en el nivel bajo",
            "satisfaccion": "satisfechos", "insatisfaccion": "insatisfechos", "si": "en «sí»", "no": "en «no»"}.get(clave, "")


def _que_respondieron(p: dict[str, Any], claves: tuple[str, ...]) -> str:
    """« (respondieron «Nunca» o «Rara vez»)»: las etiquetas de la escala que forman el nivel.

    Sin esto, el modelo leyó «57.8 % en el nivel bajo» de «¿Con qué frecuencia te ha tocado un cambio de
    profesor…?» como «la mayoría ha tenido cambios», al revés (28 oct).
    """
    escala = p.get("escala") or {}
    clave = next((k for k in claves if k in (escala.get("niveles") or {})), None)
    if clave is None:
        return ""
    etiquetas = escala.get("etiquetas") or {}
    nombres = [str(etiquetas.get(str(c), c)) for c in escala["niveles"][clave]]
    return f" (respondieron {' o '.join(f'«{n}»' for n in nombres)})" if nombres else ""


def _desviacion(dist: list[dict[str, Any]]) -> float | None:
    """Desviación estándar de una escala a partir de su distribución (códigos 1..k en el orden de la escala)."""
    pares = [(k, d.get("n") or 0) for k, d in enumerate(dist, start=1)]
    n = sum(c for _, c in pares)
    if n < 2:
        return None
    media = sum(k * c for k, c in pares) / n
    return math.sqrt(sum(c * (k - media) ** 2 for k, c in pares) / n)


def _cand(tipo: str, texto: str, puntaje: float, preguntas: list[str]) -> dict[str, Any]:
    return {"tipo": tipo, "texto": texto, "puntaje": round(puntaje, 1), "preguntas": preguntas}


def _encuesta(doc: dict[str, Any], fiabilidad: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    preguntas = [p for p in _items(doc) if p.get("resumen")]
    escala = [p for p in preguntas if _nivel_pct(p["resumen"], _POSITIVOS) is not None]
    salida: list[dict[str, Any]] = []
    if escala:
        alto = max(escala, key=lambda p: _nivel_pct(p["resumen"], _POSITIVOS))
        pct = _nivel_pct(alto["resumen"], _POSITIVOS)
        salida.append(_cand("mayor_acuerdo", f"La pregunta con más respuestas {_nombre_nivel(alto['resumen'], _POSITIVOS)} es "
                            f"{_corto(alto['id'])} «{alto['texto']}»: {pct} % de quienes respondieron"
                            f"{_que_respondieron(alto, _POSITIVOS)}.", pct, [alto["id"]]))
        bajo = max(escala, key=lambda p: _nivel_pct(p["resumen"], _NEGATIVOS) or 0)
        pct = _nivel_pct(bajo["resumen"], _NEGATIVOS) or 0
        if pct:
            salida.append(_cand("mayor_desacuerdo", f"La pregunta con más respuestas {_nombre_nivel(bajo['resumen'], _NEGATIVOS)} es "
                                f"{_corto(bajo['id'])} «{bajo['texto']}»: {pct} % de quienes respondieron"
                                f"{_que_respondieron(bajo, _NEGATIVOS)}.", pct, [bajo["id"]]))
        con_dist = [(p, d) for p in escala if (d := _desviacion(p["resumen"].get("distribucion") or [])) is not None]
        if len(con_dist) >= 2:
            p, d = max(con_dist, key=lambda x: x[1])
            salida.append(_cand("mayor_dispersion", f"La pregunta con las opiniones más divididas es {_corto(p['id'])} "
                                f"«{p['texto']}»: desviación estándar de {d:.2f} puntos en la escala.", d * 25, [p["id"]]))
        salida += _diferencias_grupos(doc, escala)
    for p in preguntas:
        dist = p["resumen"].get("distribucion") or []
        if p.get("tipo") in ("categorica", "binaria", "opcion_multiple_varias") and dist:
            top = max(dist, key=lambda x: x.get("pct") or 0)
            if (top.get("pct") or 0) >= 60:
                salida.append(_cand("opcion_dominante", f"En {_corto(p['id'])} «{p['texto']}» predomina «{top['significado']}»: "
                                    f"{top['pct']} % de quienes respondieron.", top["pct"] - 30, [p["id"]]))
    sin = [(p, p["resumen"].get("n_sin_respuesta") or 0, (p["resumen"].get("n_validas") or 0) + (p["resumen"].get("n_sin_respuesta") or 0))
           for p in preguntas]
    sin = [(p, s, t) for p, s, t in sin if t and s / t >= 0.1]
    if sin:
        p, s, t = max(sin, key=lambda x: x[1] / x[2])
        pct = round(100 * s / t, 1)
        salida.append(_cand("mucha_no_respuesta", f"{_corto(p['id'])} «{p['texto']}» quedó sin respuesta en {s} de {t} casos ({pct} %).",
                            pct, [p["id"]]))
    for b in fiabilidad or []:
        if b.get("alfa") is not None and b["alfa"] < 0.6:
            salida.append(_cand("fiabilidad_baja", f"El bloque «{b.get('bloque')}» tiene una fiabilidad baja: α de Cronbach = "
                                f"{b['alfa']} con {b.get('n_items')} ítems.", (0.7 - b["alfa"]) * 100, []))
    return salida


def _diferencias_grupos(doc: dict[str, Any], escala: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """La mayor diferencia de % en el nivel alto entre grupos de una variable de contexto (turno…)."""
    personas = doc.get("respondentes") or []
    variables: dict[str, dict[str, int]] = {}
    for r in personas:
        for k, v in (r.get("contexto") or {}).items():
            if v not in (None, ""):
                variables.setdefault(k, {}).setdefault(str(v), 0)
                variables[k][str(v)] += 1
    mejor: tuple[float, str, str] | None = None  # (diferencia, texto, pregunta)
    for var, grupos in variables.items():
        validos = [g for g, n in grupos.items() if n >= _MIN_GRUPO]
        if not 2 <= len(validos) <= 6:
            continue
        for p in escala:
            pcts = {}
            for g in validos:
                total = en = 0
                for nivel in _POSITIVOS:  # el documento usa «acuerdo» o «alta» según la escala
                    en_n, total_n = consultas.conteo_nivel(doc, p["id"], nivel, {var: g})
                    en, total = en + en_n, max(total, total_n)
                if total:
                    pcts[g] = round(100 * en / total, 1)
            if len(pcts) < 2:
                continue
            g_alto, g_bajo = max(pcts, key=pcts.get), min(pcts, key=pcts.get)
            dif = round(pcts[g_alto] - pcts[g_bajo], 1)
            if dif >= _MIN_DIFERENCIA and (mejor is None or dif > mejor[0]):
                texto = (f"En {_corto(p['id'])} «{p['texto']}», el grupo «{g_alto}» ({var}) está en el nivel alto en un "
                         f"{pcts[g_alto]} % y el grupo «{g_bajo}» en un {pcts[g_bajo]} %: {dif} puntos de diferencia.")
                mejor = (dif, texto, p["id"])
    return [_cand("diferencia_grupos", mejor[1], mejor[0] + 10, [mejor[2]])] if mejor else []


def _prueba(doc: dict[str, Any]) -> list[dict[str, Any]]:
    reactivos = [r for r in _items(doc) if (r.get("resumen") or {}).get("opcion_mas_elegida")]
    salida = []
    if reactivos:
        def pct(r: dict[str, Any]) -> float:
            return r["resumen"]["opcion_mas_elegida"]["pct"]

        junto, repartido = max(reactivos, key=pct), min(reactivos, key=pct)
        m = junto["resumen"]["opcion_mas_elegida"]
        salida.append(_cand("reactivo_coincidencia", f"El reactivo donde más alumnos coinciden es {_corto(junto['id'])} "
                            f"«{junto['texto']}»: el {m['pct']} % eligió «{m['significado']}».", m["pct"] - 30, [junto["id"]]))
        m = repartido["resumen"]["opcion_mas_elegida"]
        salida.append(_cand("reactivo_repartido", f"El reactivo con las respuestas más repartidas es {_corto(repartido['id'])} "
                            f"«{repartido['texto']}»: la opción más elegida solo reúne el {m['pct']} %.", 70 - m["pct"], [repartido["id"]]))
    con_n = [r for r in _items(doc) if (r.get("resumen") or {}).get("n_alumnos")]
    if con_n:
        def vacias(r: dict[str, Any]) -> int:
            return (r["resumen"].get("n_nulas") or 0) + (r["resumen"].get("n_sin_respuesta") or 0)

        peor = max(con_n, key=vacias)
        if vacias(peor):
            pct = round(100 * vacias(peor) / peor["resumen"]["n_alumnos"], 1)
            salida.append(_cand("mucha_no_respuesta", f"{_corto(peor['id'])} «{peor['texto']}» tiene {vacias(peor)} respuestas nulas "
                                f"o vacías de {peor['resumen']['n_alumnos']} alumnos ({pct} %).", pct, [peor["id"]]))
    return salida


def _de_lo_que_cuentan(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Hallazgos del análisis de lo que se cuenta (Fase 1, `analisis.nlp`): por pregunta guía, los temas, la valoración
    y una cita literal; con varios participantes, cuántos hablan de cada tema. Se calculan una vez al generar el
    documento; aquí solo se ordenan (7 nov, ENT-11, ENT-17, ENT-19)."""
    guia = {p["id"]: p.get("texto", "") for p in _items(doc)}
    personas = doc.get("entrevistas") or []
    por_pregunta: dict[str, dict[str, Any]] = {}
    for e in personas:
        for i in e.get("intercambios") or []:
            nlp = (i.get("analisis") or {}).get("nlp") or {}
            if not nlp.get("temas") and not nlp.get("citas_clave"):
                continue
            d = por_pregunta.setdefault(i.get("pregunta_id") or "", {"temas": {}, "citas": [], "valoraciones": []})
            for t in nlp.get("temas") or []:
                d["temas"].setdefault(str(t["tema"]).lower(), set()).add(e["participante"])
            d["citas"] += [(e["participante"], c) for c in nlp.get("citas_clave") or []][:1]
            if (nlp.get("valoracion") or {}).get("valor"):
                d["valoraciones"].append(nlp["valoracion"]["valor"])
    salida = []
    for pid, d in por_pregunta.items():
        if not d["temas"] and not d["citas"]:
            continue
        temas = sorted(d["temas"].items(), key=lambda kv: -len(kv[1]))[:4]
        temas_txt = "; ".join(f"{t}" + (f" ({len(ps)} de {len(personas)} participantes)" if len(personas) > 1 else "")
                              for t, ps in temas)
        cita = f" Cita de {_corto(d['citas'][0][0])}: «{d['citas'][0][1]}»." if d["citas"] else ""
        valor = max(set(d["valoraciones"]), key=d["valoraciones"].count) if d["valoraciones"] else ""
        texto = (f"En {_corto(pid) or 'una respuesta'} «{guia.get(pid, '')[:80]}» habla de: {temas_txt}"
                 + (f"; valoración {valor}" if valor else "") + f".{cita}")
        alcance = max((len(ps) for _, ps in temas), default=1)
        salida.append(_cand("lo_que_cuentan", texto, 10 * alcance + (5 if valor == "negativo" else 0), [pid] if pid else []))
    return sorted(salida, key=lambda c: -c["puntaje"])


def _entrevista(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if de_lo_que_cuentan := _de_lo_que_cuentan(doc):
        return de_lo_que_cuentan[:_MAX_CANDIDATOS]
    salida = []
    for p in _items(doc):
        res = consultas.posturas(doc, p["id"])
        if res.get("total"):
            c = res["conteo"]
            mayor = max(c, key=c.get)
            pct = round(100 * c[mayor] / res["total"], 1)
            salida.append(_cand("postura", f"En {_corto(p['id'])} «{p['texto']}», {c[mayor]} de {res['total']} participantes "
                                f"tienen la postura «{mayor}» ({pct} %).", pct - 30, [p["id"]]))
    return salida


def por_polaridad(doc: dict[str, Any], sentido: str) -> list[dict[str, Any]]:
    """Lo más preocupante (`desfavorable`) o lo mejor (`favorable`) según la polaridad de cada pregunta (documento final,
    7 nov): el % de quienes eligieron sus respuestas desfavorables o favorables, de mayor a menor. Solo preguntas con
    polaridad decidida; «Nunca» en «¿con qué frecuencia te ha tocado un cambio de profesor?» cuenta como favorable si
    así lo marcó la investigadora (ENC-16)."""
    clave = "desfavorables" if sentido == "desfavorable" else "favorables"
    salida = []
    for p in _items(doc):
        po = p.get("polaridad") or {}
        elegidas = [str(o) for o in po.get(clave) or []]
        dist = (p.get("resumen") or {}).get("distribucion") or []
        validas = (p.get("resumen") or {}).get("n_validas") or sum(int(d.get("n") or 0) for d in dist)
        if not elegidas or not dist or not validas:
            continue
        n = sum(int(d.get("n") or 0) for d in dist if str(d.get("significado")) in elegidas)
        pct = round(100 * n / validas, 1)
        quien = "la investigadora" if po.get("origen") == "investigador" else "el sistema (sin revisar)"
        texto = (f"{pct} % ({n} de {validas}) respondió {' o '.join(f'«{o}»' for o in elegidas)} en {_corto(p['id'])} "
                 f"«{p.get('texto', '')[:90]}» (respuestas {clave} según {quien})")
        salida.append(_cand(f"mas_{clave}", texto, pct, [p["id"]]))
    return sorted(salida, key=lambda c: -c["puntaje"])[:_MAX_CANDIDATOS]


def candidatos(tipo: str, doc: dict[str, Any], fiabilidad: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Candidatos a hallazgo ordenados de mayor a menor puntaje (a lo más `_MAX_CANDIDATOS`)."""
    if tipo == "prueba_estandarizada":
        lista = _prueba(doc)
    elif tipo == "entrevista":
        lista = _entrevista(doc)
    else:
        lista = _encuesta(doc, fiabilidad)
    vistos: set[str] = set()
    unicos = []
    for c in sorted(lista, key=lambda c: -c["puntaje"]):
        clave = normalizar(c["texto"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(c)
    return unicos[:_MAX_CANDIDATOS]
