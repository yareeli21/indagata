"""Reporte del experimento de modelos: métricas contra la referencia y cruce entre juez, métricas sin juez y persona.

Uso (dentro del contenedor del chat):
    docker compose exec visualization-service python scripts/modelos/reporte.py \
        --corrida llama3.2:3b=1328-1370 --corrida qwen2.5:3b=1371-1410 ...

Escribe en `storage/evaluacion_modelos/<fecha>/` (carpeta montada del repositorio):
  <redactor>.md / .json   cada turno: respuesta, indicadores del sistema, métricas contra la referencia, cada juez y
                          la calificación humana.
  resumen.md / .json      comparación de redactores, matriz redactor × juez, sesgo de autoevaluación, el cruce
                          (kappa, Spearman, confusión) y qué fallas se repiten en todos los modelos (probable código).

Métricas contra la referencia (`casos.json`), por tipo de turno:
  intención correcta    la intención interpretada está entre las aceptadas del turno (todos los tipos).
  contexto suficiente   el contexto que vio el modelo trae las cifras / textos esperados (turnos de dato).
  exactitud de cifras   fracción de las cifras esperadas presentes en la respuesta (la mejor alternativa).
  criterios             menciona lo que debe; «sin cifras» en los inexistentes.
  similitud semántica   coseno (mpnet) entre la respuesta y la referencia (dato, inexistente, control).
Los interpretativos no tienen exactitud ni similitud: los califica la persona.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from statistics import median

import comun  # noqa: F401  (ajusta sys.path)
from comun import CASOS, Corrida, clave_texto, emparejar, kappa, leer_casos, media, parsear_corrida, spearman

from shared.db.session import SessionLocal
from shared.models.rag_evaluacion import RagCalificacion, RagMetricaJuez
from shared.models.rag_log import RagLog

from services import evaluacion, indicadores, vectores

_RAIZ_SALIDA = Path(__file__).resolve().parents[2] / "storage" / "evaluacion_modelos"
METRICAS_JUEZ = ("fidelidad", "relevancia", "precision_contexto")
APROBADO = 0.7  # mismo umbral que el verde del panel


def _cifras(texto: str) -> set[float]:
    return {round(float(c.replace(",", ".")), 1)
            for c in evaluacion._CIFRA.findall(evaluacion._NO_CIFRA.sub(" ", texto or ""))}


def _contiene(texto: str, buscado: str) -> bool:
    return clave_texto(buscado) in clave_texto(texto)


def _exactitud(texto: str, alternativas: list[list[float]]) -> float:
    presentes = _cifras(texto)
    return max(sum(round(float(x), 1) in presentes for x in alt) / len(alt) for alt in alternativas)


def _coseno(a: list[float], b: list[float]) -> float:
    return round(evaluacion._coseno(a, b), 3)


def _original(sesion, fila: RagLog) -> RagLog:
    """Una respuesta de la caché se mide con la consulta original (ahí están su plan, contexto y métricas)."""
    origen = (fila.metricas or {}).get("origen")
    return (sesion.get(RagLog, origen) if origen else None) or fila


def medir_turno(sesion, fila: RagLog, turno: dict) -> dict:
    original = _original(sesion, fila)
    ind = indicadores.calcular(original)
    respuesta = fila.respuesta or ""
    contexto = "\n".join(c.get("texto", "") for c in original.contexto_usado or [])
    tipo = turno["tipo"]
    r: dict = {"consulta": fila.rag_log_id, "enCache": original is not fila, "respuesta": respuesta,
               "indicadores": ind, "tipo": tipo}

    r["intencion_correcta"] = ind["intencion"] in turno.get("intenciones", [])
    if tipo != "interpretativo":
        if "cifras" in turno:
            r["exactitud"] = round(_exactitud(respuesta, turno["cifras"]), 3)
            r["contexto_suficiente"] = _exactitud(contexto, turno["cifras"]) == 1
        criterios = []
        for texto in turno.get("debe_mencionar", []):
            criterios.append(_contiene(respuesta, texto))
        if turno.get("debe_mencionar_alguno"):
            criterios.append(any(_contiene(respuesta, t) for t in turno["debe_mencionar_alguno"]))
            if "cifras" not in turno:
                r["contexto_suficiente"] = any(_contiene(contexto, t) for t in turno["debe_mencionar_alguno"])
        if turno.get("sin_cifras"):
            criterios.append(not _cifras(re.sub(r"\[Fuente \d+\]", "", respuesta)))
        if criterios:
            r["criterios"] = all(criterios)
    r["plantilla_indebida"] = ind["respuesta"] == "plantilla" and ind["plantilla"] not in ("aclaracion",) \
        and tipo != "capacidad"
    if tipo == "inexistente":  # una aclaración con las opciones reales es la respuesta esperada
        r["plantilla_indebida"] = ind["plantilla"] not in (None, "aclaracion")

    jueces = {}
    for j in sesion.query(RagMetricaJuez).filter_by(rag_log_id=original.rag_log_id):
        m = j.metricas or {}
        if m.get("estado") in (evaluacion.LISTO, evaluacion.CALCULADA):
            valores = {k: m.get(k) for k in METRICAS_JUEZ}
            jueces[j.modelo_juez] = {**valores, "promedio": media(list(valores.values())), "estado": m.get("estado")}
    r["jueces"] = jueces

    c = sesion.get(RagCalificacion, fila.rag_log_id)
    r["humana"] = None if c is None else {"calificacion": c.calificacion, "entendio": c.entendio,
                                          "fundamenta": c.fundamenta, "comentario": c.comentario}
    return r


def acierto(r: dict) -> bool | None:
    """¿El turno salió bien? Manda la calificación humana; sin ella, las métricas contra la referencia."""
    if r["humana"] is not None:
        return r["humana"]["calificacion"] == 2
    if r["tipo"] == "interpretativo":
        return None
    partes = [v for v in (r.get("criterios"), None if "exactitud" not in r else r["exactitud"] == 1) if v is not None]
    return all(partes) if partes else None


def _fmt(v, pct: bool = False) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    return f"{round(v * 100)} %" if pct else str(v)


# ── Por redactor ───────────────────────────────────────────────────────────────


def resumen_redactor(turnos: list[dict]) -> dict:
    inds = [t["indicadores"] for t in turnos]
    humanas = [t["humana"]["calificacion"] for t in turnos if t["humana"]]
    redactadas = [i for i in inds if i["respuesta"] == "redactada" and i["cifrasTotal"]]
    return {
        "turnos": len(turnos),
        "intencion_correcta": media([float(t["intencion_correcta"]) for t in turnos]),
        "plantilla_indebida": sum(t["plantilla_indebida"] for t in turnos),
        "redactadas": sum(i["respuesta"] == "redactada" for i in inds),
        "regeneraciones": sum(i["regeneraciones"] or 0 for i in inds),
        "cifras_sin_respaldo": sum(len(i["cifrasSinRespaldo"]) for i in inds),
        "cifras_con_respaldo": media([i["cifrasConRespaldo"] / i["cifrasTotal"] for i in redactadas]),
        "ids_inventados": sum(len(i["idsInventados"]) for i in inds),
        "exactitud": media([t["exactitud"] for t in turnos if "exactitud" in t]),
        "criterios": media([float(t["criterios"]) for t in turnos if "criterios" in t]),
        "contexto_suficiente": media([float(t["contexto_suficiente"]) for t in turnos if "contexto_suficiente" in t]),
        "similitud": media([t["similitud"] for t in turnos if t.get("similitud") is not None]),
        "latencia_mediana_s": round(median([i["latenciaMs"] for i in inds if i["latenciaMs"]]) / 1000, 1)
        if any(i["latenciaMs"] for i in inds) else None,
        "humana_media": media(humanas),
        "humana_bien": media([float(h == 2) for h in humanas]),
        "calificadas": len(humanas),
    }


def md_redactor(corrida: Corrida, turnos: list[dict], casos: dict, faltan: list[str]) -> str:
    textos = {(c["caso"], i): t for c in casos["casos"] for i, t in enumerate(c["turnos"], 1)}
    jueces = sorted({j for t in turnos for j in t["jueces"]})
    l = [f"# Redactor {corrida.modelo}", "", f"Corrida: consultas {corrida.desde}–{corrida.hasta or '…'} de `rag_log`; "
         f"{len(turnos)} de {len(textos)} turnos.", ""]
    if faltan:
        l += ["Turnos sin respuesta en la corrida:", *[f"- {f}" for f in faltan], ""]
    cab = ["Turno", "Tipo", "Entendió", "Respuesta", "Regen.", "Cifras con respaldo", "IDs inv.", "Exactitud",
           "Criterios", "Similitud", *[f"Juez {j}" for j in jueces], "Humana", "Tiempo"]
    l += ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for t in turnos:
        i = t["indicadores"]
        cif = "—" if i["cifrasTotal"] is None else f"{i['cifrasConRespaldo']} de {i['cifrasTotal']}"
        resp = i["plantilla"] or i["respuesta"]
        fila = [t["turno"], t["tipo"], f"{i['intencion'] or '—'} ({_fmt(t['intencion_correcta'])})", resp,
                _fmt(i["regeneraciones"]), cif, ", ".join(i["idsInventados"]) or "—", _fmt(t.get("exactitud"), True),
                _fmt(t.get("criterios")), _fmt(t.get("similitud")),
                *["/".join(_fmt(t["jueces"][j][k], True) for k in METRICAS_JUEZ) if j in t["jueces"] else "—"
                  for j in jueces],
                "—" if not t["humana"] else ["mal", "parcial", "bien"][t["humana"]["calificacion"]],
                "—" if not i["latenciaMs"] else f"{i['latenciaMs'] / 1000:.1f} s" + (" (caché)" if t["enCache"] else "")]
        l.append("| " + " | ".join(str(x).replace("|", "/") for x in fila) + " |")
    l += ["", "Jueces: fidelidad / relevancia / precisión del contexto.", "", "## Respuestas", ""]
    for t in turnos:
        caso, n = map(int, t["turno"].split("."))
        l += [f"### {t['turno']} · {textos[(caso, n)]['texto']}", "", f"Consulta {t['consulta']} · tipo {t['tipo']}"]
        if textos[(caso, n)].get("referencia"):
            l.append(f"Referencia: {textos[(caso, n)]['referencia']}")
        for crit in textos[(caso, n)].get("criterios", []):
            l.append(f"Criterio: {crit}")
        l += ["", "> " + t["respuesta"][:1500].replace("\n", "\n> "), ""]
        if t["humana"] and t["humana"]["comentario"]:
            l += [f"Comentario de la persona: {t['humana']['comentario']}", ""]
    return "\n".join(l)


# ── Resumen y cruce ────────────────────────────────────────────────────────────


def cruce(todos: list[dict]) -> dict:
    """Juez contra métricas sin juez y contra la persona, por cada juez."""
    salida = {}
    for juez in sorted({j for t in todos for j in t["jueces"]}):
        con = [t for t in todos if juez in t["jueces"]]
        red = [t for t in con if t["indicadores"]["respuesta"] == "redactada" and t["indicadores"]["cifrasTotal"]
               and t["jueces"][juez]["fidelidad"] is not None]
        fid_vs_cifras = kappa([t["jueces"][juez]["fidelidad"] >= 0.8 for t in red],
                              [t["indicadores"]["cifrasConRespaldo"] == t["indicadores"]["cifrasTotal"] for t in red])
        hum = [t for t in con if t["humana"] and t["jueces"][juez]["promedio"] is not None]
        ap_vs_humana = kappa([t["jueces"][juez]["promedio"] >= APROBADO for t in hum],
                             [t["humana"]["calificacion"] == 2 for t in hum])
        rho_prom = spearman([t["jueces"][juez]["promedio"] for t in hum], [t["humana"]["calificacion"] for t in hum])
        hum_rel = [t for t in hum if t["jueces"][juez]["relevancia"] is not None]
        rho_rel = spearman([t["jueces"][juez]["relevancia"] for t in hum_rel], [t["humana"]["calificacion"] for t in hum_rel])
        conf = {"prec_alta_ctx_si": 0, "prec_alta_ctx_no": 0, "prec_baja_ctx_si": 0, "prec_baja_ctx_no": 0}
        for t in con:
            p = t["jueces"][juez]["precision_contexto"]
            if p is None or "contexto_suficiente" not in t:
                continue
            conf[f"prec_{'alta' if p >= 0.5 else 'baja'}_ctx_{'si' if t['contexto_suficiente'] else 'no'}"] += 1
        salida[juez] = {"n": len(con), "kappa_fidelidad_vs_cifras": fid_vs_cifras, "n_fidelidad": len(red),
                        "kappa_aprobado_vs_humana": ap_vs_humana, "spearman_promedio_vs_humana": rho_prom,
                        "spearman_relevancia_vs_humana": rho_rel, "n_humana": len(hum), "confusion_precision": conf}
    return salida


def entre_jueces(todos: list[dict]) -> dict:
    jueces = sorted({j for t in todos for j in t["jueces"]})
    salida = {}
    for i, a in enumerate(jueces):
        for b in jueces[i + 1:]:
            pares = [(t["jueces"][a]["promedio"], t["jueces"][b]["promedio"]) for t in todos
                     if a in t["jueces"] and b in t["jueces"]
                     and None not in (t["jueces"][a]["promedio"], t["jueces"][b]["promedio"])]
            salida[f"{a} ~ {b}"] = {"n": len(pares), "spearman": spearman([x for x, _ in pares], [y for _, y in pares])}
    return salida


def matriz(por_redactor: dict[str, list[dict]]) -> dict:
    jueces = sorted({j for ts in por_redactor.values() for t in ts for j in t["jueces"]})
    celdas = {r: {j: {k: media([t["jueces"][j][k] for t in ts if j in t["jueces"]]) for k in (*METRICAS_JUEZ, "promedio")}
                  for j in jueces} for r, ts in por_redactor.items()}
    sesgo = {}
    for r in por_redactor:
        if r in jueces and celdas[r][r]["promedio"] is not None:
            otros = [celdas[r][j]["promedio"] for j in jueces if j != r and celdas[r][j]["promedio"] is not None]
            if otros:
                sesgo[r] = round(celdas[r][r]["promedio"] - sum(otros) / len(otros), 3)
    return {"jueces": jueces, "celdas": celdas, "sesgo_autoevaluacion": sesgo}


def md_resumen(resumenes: dict, mat: dict, cru: dict, ej: dict, por_redactor: dict, casos: dict) -> str:
    red = list(resumenes)
    l = ["# Experimento de modelos: resumen", "",
         f"Instrumento {casos['instrumento']}; {sum(len(c['turnos']) for c in casos['casos'])} turnos en "
         f"{len(casos['casos'])} casos. Generado con `scripts/modelos/reporte.py`.", "",
         "## 1. Redactores (métricas sin juez, contra la referencia y humanas)", ""]
    filas = [("Intención correcta", "intencion_correcta", True), ("Plantillas indebidas", "plantilla_indebida", False),
             ("Respuestas redactadas por el modelo", "redactadas", False), ("Regeneraciones", "regeneraciones", False),
             ("Cifras con respaldo (redactadas)", "cifras_con_respaldo", True),
             ("Cifras sin respaldo", "cifras_sin_respaldo", False), ("IDs inventados", "ids_inventados", False),
             ("Contexto suficiente (dato)", "contexto_suficiente", True), ("Exactitud de cifras", "exactitud", True),
             ("Criterios cumplidos", "criterios", True), ("Similitud semántica", "similitud", False),
             ("Latencia mediana (s)", "latencia_mediana_s", False), ("Calificación humana media (0–2)", "humana_media", False),
             ("Respuestas «Bien»", "humana_bien", True), ("Turnos calificados", "calificadas", False)]
    l += ["| Métrica | " + " | ".join(red) + " |", "|---|" + "---|" * len(red)]
    for nombre, clave, pct in filas:
        l.append(f"| {nombre} | " + " | ".join(_fmt(resumenes[r][clave], pct) for r in red) + " |")

    l += ["", "## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)", ""]
    if mat["jueces"]:
        l += ["| Redactor \\ Juez | " + " | ".join(mat["jueces"]) + " |", "|---|" + "---|" * len(mat["jueces"])]
        for r in red:
            l.append(f"| {r} | " + " | ".join(
                ("**" if r == j else "") + _fmt(mat["celdas"][r][j]["promedio"], True) + ("**" if r == j else "")
                for j in mat["jueces"]) + " |")
        l += ["", "En negritas, la autoevaluación (el redactor se juzga a sí mismo).", ""]
        for k, nombre in zip(METRICAS_JUEZ, ("Fidelidad", "Relevancia", "Precisión del contexto")):
            l += [f"**{nombre}**", "", "| Redactor \\ Juez | " + " | ".join(mat["jueces"]) + " |",
                  "|---|" + "---|" * len(mat["jueces"])]
            l += [f"| {r} | " + " | ".join(_fmt(mat["celdas"][r][j][k], True) for j in mat["jueces"]) + " |" for r in red]
            l.append("")
        l += ["## 3. Sesgo de autoevaluación", "",
              "Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces "
              "(positivo = se califica mejor).", ""]
        l += [f"- {r}: {'+' if v > 0 else ''}{round(v * 100)} puntos" for r, v in mat["sesgo_autoevaluacion"].items()] \
            or ["- Sin datos suficientes (hace falta que el redactor también sea juez y al menos otro juez)."]
    else:
        l.append("Todavía no hay evaluaciones de jueces: corre `juzgar.py`.")

    l += ["", "## 4. ¿Se puede confiar en cada juez? (cruce)", "",
          "Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.", "",
          "| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | "
          "Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |", "|---|---|---|---|---|---|"]
    for j, c in cru.items():
        l.append(f"| {j} | {_fmt(c['kappa_fidelidad_vs_cifras'])} (n={c['n_fidelidad']}) | "
                 f"{_fmt(c['kappa_aprobado_vs_humana'])} | {_fmt(c['spearman_promedio_vs_humana'])} | "
                 f"{_fmt(c['spearman_relevancia_vs_humana'])} | {c['n']} ({c['n_humana']} calificadas) |")
    l += ["", "**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**", "",
          "| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |", "|---|---|---|---|---|"]
    for j, c in cru.items():
        m = c["confusion_precision"]
        l.append(f"| {j} | {m['prec_alta_ctx_si']} | {m['prec_alta_ctx_no']} | {m['prec_baja_ctx_si']} | {m['prec_baja_ctx_no']} |")
    if ej:
        l += ["", "**Acuerdo entre jueces** (Spearman del promedio sobre las mismas respuestas)", ""]
        l += [f"- {par}: {_fmt(v['spearman'])} (n={v['n']})" for par, v in ej.items()]

    l += ["", "## 5. ¿Falla del modelo o del código?", "",
          "Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que "
          "sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las "
          "métricas contra la referencia.", "",
          "| Turno | Tipo | " + " | ".join(red) + " | Lectura |", "|---|---|" + "---|" * len(red) + "---|"]
    for c in casos["casos"]:
        for n, t in enumerate(c["turnos"], 1):
            clave = f"{c['caso']}.{n}"
            valores = []
            for r in red:
                turno = next((x for x in por_redactor[r] if x["turno"] == clave), None)
                valores.append(None if turno is None else acierto(turno))
            conocidos = [v for v in valores if v is not None]
            if not conocidos:
                lectura = "sin datos"
            elif len(conocidos) == 1:  # con un solo modelo no se puede separar código de modelo
                lectura = "bien" if conocidos[0] else "falla (comparar con otros modelos)"
            else:
                lectura = ("falla en todos: probable código" if not any(conocidos)
                           else "bien en todos" if all(conocidos) else "depende del modelo")
            l.append(f"| {clave} | {t['tipo']} | " + " | ".join("—" if v is None else ("✓" if v else "✗") for v in valores)
                     + f" | {lectura} |")
    return "\n".join(l)


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--corrida", action="append", required=True, help="modelo=INICIO-FIN (rag_log_id)")
    args.add_argument("--casos", default="casos.json", help="archivo de casos junto a este script (p. ej. casos_pru03.json)")
    args.add_argument("--salida", default="", help="carpeta (por defecto storage/evaluacion_modelos/<fecha>)")
    a = args.parse_args()
    casos = leer_casos(CASOS.with_name(a.casos))
    sufijo = "" if a.casos == "casos.json" else "_" + Path(a.casos).stem.removeprefix("casos_")
    destino = Path(a.salida) if a.salida else _RAIZ_SALIDA / f"{date.today().isoformat()}{sufijo}"
    destino.mkdir(parents=True, exist_ok=True)

    sesion = SessionLocal()
    por_redactor: dict[str, list[dict]] = {}
    resumenes: dict[str, dict] = {}
    try:
        textos = {(c["caso"], i): t for c in casos["casos"] for i, t in enumerate(c["turnos"], 1)}
        for texto in a.corrida:
            corrida = parsear_corrida(texto)
            faltan = emparejar(sesion, corrida, casos)
            turnos = []
            for (caso, n), fila in sorted(corrida.filas.items()):
                r = medir_turno(sesion, fila, textos[(caso, n)])
                r["turno"] = f"{caso}.{n}"
                turnos.append(r)
            # Similitud semántica: un solo lote de embeddings por corrida.
            pares = [(r, textos[tuple(map(int, r["turno"].split(".")))]["referencia"]) for r in turnos
                     if r["tipo"] != "interpretativo" and textos[tuple(map(int, r["turno"].split(".")))].get("referencia")]
            if pares:
                vec = vectores.embed_texts([x for r, ref in pares for x in (r["respuesta"][:1500], ref)])
                for k, (r, _) in enumerate(pares):
                    r["similitud"] = _coseno(vec[2 * k], vec[2 * k + 1])
            por_redactor[corrida.modelo] = turnos
            resumenes[corrida.modelo] = resumen_redactor(turnos)
            nombre = re.sub(r"[^\w.-]+", "_", corrida.modelo)
            (destino / f"{nombre}.md").write_text(md_redactor(corrida, turnos, casos, faltan), encoding="utf-8")
            (destino / f"{nombre}.json").write_text(json.dumps({"corrida": texto, "faltan": faltan, "turnos": turnos},
                                                               ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            print(f"{corrida.nombre}: {len(turnos)} turnos" + (f", faltan {len(faltan)}" if faltan else ""))
    finally:
        sesion.close()

    todos = [t for ts in por_redactor.values() for t in ts]
    mat, cru, ej = matriz(por_redactor), cruce(todos), entre_jueces(todos)
    (destino / "resumen.md").write_text(md_resumen(resumenes, mat, cru, ej, por_redactor, casos), encoding="utf-8")
    (destino / "resumen.json").write_text(json.dumps({"redactores": resumenes, "matriz": mat, "cruce": cru,
                                                      "entre_jueces": ej}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Reporte en {destino}")


if __name__ == "__main__":
    main()
