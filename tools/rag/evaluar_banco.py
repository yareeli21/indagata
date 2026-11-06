"""Evalúa el chat con el banco de preguntas (tools/rag/banco_preguntas.json) y produce un reporte reproducible.

Métricas (Pruebas Y.x; el plan de evaluación modelo por modelo):
  - Decisión de dominio: exactitud, matriz de confusión, F1 macro y FALSAS ACEPTACIONES (privacidad o
    manipulación respondidas como «dentro»; la meta es 0).
  - Exactitud con referencia: la respuesta contiene las `cifras_clave`, los `hechos_clave` y, si las hay, una
    de las respuestas `aceptables` (comparación sin acentos ni mayúsculas; las cifras, como números).
  - Recuperación (solo preguntas con `relevantes`): Hit@k y MRR sobre los fragmentos que vio el modelo
    (rag_log.contexto_usado), en el orden en que se le entregaron.
  - Consistencia: proporción de paráfrasis con la misma decisión y la misma exactitud que la original.
  - Estabilidad: con --repeticiones N, proporción de preguntas cuya exactitud no cambia entre corridas.
  - Eficiencia: latencia p50 y p95, en total y por ruta.
  - Métricas del juez (fidelidad, relevancia, precisión del contexto): solo de las preguntas originales;
    las respuestas calculadas aparecen como «fiel por construcción».

Todas las consultas van SIN caché (`usarCache: false`); las paráfrasis y repeticiones no piden métricas al
juez (`calcularMetricas: false`) para no saturar su cola.

Uso (con la app levantada):
    python tools/rag/evaluar_banco.py --parafrasis --repeticiones 3 [--redactor llama3.2:3b] [--ids E11-01,E10-01]
    python tools/rag/evaluar_banco.py --sin-metricas          # solo exactitud, dominio y tiempos (rápido)
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

RAIZ = Path(__file__).resolve().parents[2]
GATEWAY = "http://localhost:8006"
_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0)
_RESTRINGIDAS = {"privacidad", "manipulacion"}


def normalizar(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def _numeros(texto: str) -> set[float]:
    """Cifras de un texto como números (13.3 % → 13.3; 0,68 → 0.68), sin los dígitos de IDs ni citas."""
    limpio = re.sub(r"\[fuente\s*\d+[^\]]*\]|\b(?:ins|kpi)-?\d+\b|\b[rpqaei]-?\d{1,4}\b", " ", texto, flags=re.IGNORECASE)
    return {round(float(c.replace(",", ".")), 2) for c in re.findall(r"\d+(?:[.,]\d+)?", limpio)}


def exacta(respuesta: str, pregunta: dict[str, Any]) -> bool | None:
    """¿Contiene lo que debe? None si la pregunta no tiene nada verificable (se evalúa con el juez y la persona)."""
    cifras, hechos, aceptables = pregunta["cifras_clave"], pregunta["hechos_clave"], pregunta["aceptables"]
    if not (cifras or hechos or aceptables):
        return None
    numeros, texto = _numeros(respuesta), normalizar(respuesta)

    def aparece(cifra: str) -> bool:
        """La cifra esperada, con su misma precisión: «27.2» acepta 27.23; «60» acepta 60.0."""
        decimales = len(cifra.split(".")[1]) if "." in cifra else 0
        return any(round(n, decimales) == round(float(cifra), decimales) for n in numeros)

    ok_cifras = all(aparece(c) for c in cifras)
    ok_hechos = all(normalizar(h) in texto for h in hechos)
    ok_aceptables = not aceptables or any(re.search(rf"\b{re.escape(normalizar(a))}\b", texto) for a in aceptables)
    return ok_cifras and ok_hechos and ok_aceptables


def _psql_json(consulta: str) -> list[dict[str, Any]]:
    salida = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "indagata_db", "-At", "-c",
         f"select coalesce(json_agg(t), '[]') from ({consulta}) t"],
        capture_output=True, text=True, encoding="utf-8", cwd=RAIZ,
    )
    return json.loads(salida.stdout.strip() or "[]")


def _registros(ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    filas = _psql_json("select rag_log_id, motivo, ruta, decision_dominio, latencia_ms, contexto_usado, metricas, "
                       f"modelo_juez, modelo_usado from tt_rag.rag_log where rag_log_id in ({','.join(map(str, ids))})")
    return {f["rag_log_id"]: f for f in filas}


def recuperacion(contexto: list[dict[str, Any]] | None, relevantes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Hit@k y rango recíproco del primer fragmento relevante entre los que vio el modelo."""
    if not relevantes:
        return None
    fragmentos = [c for c in contexto or [] if c.get("tipo") not in ("resultado", "glosario", "ayuda", "fuente_kpi")]
    for rango, f in enumerate(fragmentos, start=1):
        for r in relevantes:
            if str(f.get("instrumentoId")) == str(r["instrumentoId"]) and normalizar(r["contiene"]) in normalizar(f.get("texto", "")):
                return {"hit": True, "rr": 1 / rango, "k": len(fragmentos), "rango": rango}
    return {"hit": False, "rr": 0.0, "k": len(fragmentos), "rango": None}


def _preguntar(cliente: httpx.Client, token: str, texto: str, alcance: list[str], redactor: str | None, metricas: bool) -> dict[str, Any]:
    cuerpo = {"pregunta": texto, "instrumentoIds": alcance, "stream": False, "usarCache": False, "calcularMetricas": metricas}
    if redactor:
        cuerpo["modelo"] = redactor
    inicio = time.monotonic()
    try:
        r = cliente.post(f"{GATEWAY}/rag/chat", json=cuerpo, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:  # una consulta lenta o caída no tumba la corrida (25 oct: memoria al límite)
        return {"error": f"{type(exc).__name__}: {exc}", "segundos": round(time.monotonic() - inicio, 2)}
    segundos = round(time.monotonic() - inicio, 2)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "segundos": segundos}
    datos = r.json()
    return {"respuesta": datos.get("respuesta", ""), "decision": datos.get("decision"), "ruta": datos.get("ruta"),
            "consultaId": datos.get("consultaId"), "segundos": segundos}


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return round(ordenados[min(len(ordenados) - 1, int(round(p * (len(ordenados) - 1))))], 2)


def _f1_macro(pares: list[tuple[str, str]]) -> float:
    clases = sorted({e for e, _ in pares} | {o for _, o in pares})
    f1s = []
    for c in clases:
        tp = sum(1 for e, o in pares if e == c and o == c)
        fp = sum(1 for e, o in pares if e != c and o == c)
        fn = sum(1 for e, o in pares if e == c and o != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return round(sum(f1s) / len(f1s), 3) if f1s else 0.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--banco", type=Path, default=RAIZ / "tools" / "rag" / "banco_preguntas.json")
    p.add_argument("--redactor", help="modelo que redacta (por defecto, el del servicio)")
    p.add_argument("--parafrasis", action="store_true", help="también las 2 paráfrasis de cada pregunta")
    p.add_argument("--repeticiones", type=int, default=1, help="corridas de cada pregunta original (estabilidad)")
    p.add_argument("--ids", help="solo estas preguntas (coma)")
    p.add_argument("--sin-metricas", action="store_true", help="no pedir métricas al juez")
    p.add_argument("--espera-metricas", type=int, default=3600, help="segundos máximos esperando al juez")
    p.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / f"banco_{datetime.now():%Y-%m-%d}")
    p.add_argument("--email", default="admin@indagata.com")
    p.add_argument("--password", default="admin123")
    args = p.parse_args()
    args.salida = args.salida.resolve()

    banco = json.loads(args.banco.read_text(encoding="utf-8"))["preguntas"]
    if args.ids:
        elegidas = set(args.ids.split(","))
        banco = [q for q in banco if q["id"] in elegidas]
    cliente = httpx.Client(timeout=_TIMEOUT)
    token = cliente.post(f"{GATEWAY}/auth/login", json={"email": args.email, "password": args.password}).json()["access_token"]

    filas: list[dict[str, Any]] = []
    for n, q in enumerate(banco, start=1):
        textos = [("original", q["pregunta"], 0)]
        textos += [("repeticion", q["pregunta"], i) for i in range(1, args.repeticiones)]
        if args.parafrasis:
            textos += [("parafrasis", t, i) for i, t in enumerate(q["parafrasis"], start=1)]
        for clase, texto, i in textos:
            r = _preguntar(cliente, token, texto, q["alcance"], args.redactor,
                           metricas=clase == "original" and not args.sin_metricas)
            filas.append({"id": q["id"], "clase": clase, "i": i, "texto": texto, **r})
            print(f"[{n}/{len(banco)}] {q['id']} {clase}{i or ''}: {r.get('decision')} {r.get('ruta')} {r.get('segundos')} s", flush=True)

    # Métricas del juez: se esperan al final (la cola se procesa mientras no hay preguntas en curso).
    originales = [f["consultaId"] for f in filas if f["clase"] == "original" and f.get("consultaId")]
    limite = time.monotonic() + (0 if args.sin_metricas else args.espera_metricas)
    registros = _registros([f["consultaId"] for f in filas if f.get("consultaId")])
    while time.monotonic() < limite:
        pendientes = [i for i in originales if (registros.get(i, {}).get("metricas") or {}).get("estado") in (None, "calculando")]
        if not pendientes:
            break
        print(f"Esperando métricas del juez: {len(pendientes)} pendientes…", flush=True)
        time.sleep(30)
        registros = _registros([f["consultaId"] for f in filas if f.get("consultaId")])

    por_id = {q["id"]: q for q in banco}
    for f in filas:
        q, reg = por_id[f["id"]], registros.get(f.get("consultaId") or -1, {})
        f["decision_esperada"] = q["decision_esperada"]
        f["decision_ok"] = f.get("decision") == q["decision_esperada"]
        f["exacta"] = exacta(f.get("respuesta", ""), q) if f["decision_ok"] and q["decision_esperada"] == "dentro" else (
            None if q["decision_esperada"] != "dentro" else False)
        f["motivo"] = reg.get("motivo")
        f["recuperacion"] = recuperacion(reg.get("contexto_usado"), q["relevantes"]) if q["relevantes"] else None
        m = reg.get("metricas") or {}
        f["metricas"] = {k: m.get(k) for k in ("estado", "fidelidad", "relevancia", "precision_contexto")}
        f["modelo_juez"], f["modelo_usado"] = reg.get("modelo_juez"), reg.get("modelo_usado")

    orig = [f for f in filas if f["clase"] == "original"]
    pares = [(f["decision_esperada"], f.get("decision") or "error") for f in orig]
    verificables = [f for f in orig if f["exacta"] is not None]
    recup = [f["recuperacion"] for f in orig if f["recuperacion"]]
    lat = [f["segundos"] for f in orig if f.get("segundos") is not None]
    lat_ruta: dict[str, list[float]] = defaultdict(list)
    for f in orig:
        lat_ruta[f.get("ruta") or "sin ruta"].append(f["segundos"])
    paraf = [f for f in filas if f["clase"] == "parafrasis"]
    consistentes = [f for f in paraf if f["decision_ok"] and (f["exacta"] is None or f["exacta"] == next(
        (o["exacta"] for o in orig if o["id"] == f["id"]), None))]
    estab_ids = [i for i in {f["id"] for f in filas if f["clase"] == "repeticion"}]
    estables = [i for i in estab_ids if len({f["exacta"] for f in filas if f["id"] == i and f["clase"] in ("original", "repeticion")}) == 1]
    juez = [f["metricas"] for f in orig if f["metricas"].get("estado") == "listo"]

    def media(clave: str) -> float | None:
        valores = [m[clave] for m in juez if m.get(clave) is not None]
        return round(statistics.mean(valores), 3) if valores else None

    por_tipo: dict[str, list[bool]] = defaultdict(list)
    for f in verificables:
        por_tipo[por_id[f["id"]]["tipo_consulta"]].append(bool(f["exacta"]))
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "redactor": args.redactor or (orig[0].get("modelo_usado") if orig else None),
        "juez": next((f["modelo_juez"] for f in orig if f.get("modelo_juez")), None),
        "preguntas": len(orig), "consultas": len(filas),
        "decision": {"exactitud": round(sum(f["decision_ok"] for f in orig) / len(orig), 3) if orig else None,
                     "f1_macro": _f1_macro(pares),
                     "falsas_aceptaciones": sum(1 for e, o in pares if e in _RESTRINGIDAS and o == "dentro"),
                     "matriz": {f"{e}→{o}": c for (e, o), c in sorted(Counter(pares).items())}},
        "exactitud": {"verificables": len(verificables),
                      "correctas": sum(bool(f["exacta"]) for f in verificables),
                      "proporcion": round(sum(bool(f["exacta"]) for f in verificables) / len(verificables), 3) if verificables else None,
                      "por_tipo": {t: f"{sum(v)}/{len(v)}" for t, v in sorted(por_tipo.items())},
                      "fallidas": [f["id"] for f in verificables if not f["exacta"]]},
        "recuperacion": {"preguntas": len(recup), "hit": round(sum(r["hit"] for r in recup) / len(recup), 3) if recup else None,
                         "mrr": round(statistics.mean(r["rr"] for r in recup), 3) if recup else None},
        "consistencia_parafrasis": round(len(consistentes) / len(paraf), 3) if paraf else None,
        "estabilidad": round(len(estables) / len(estab_ids), 3) if estab_ids else None,
        "latencia": {"p50": _percentil(lat, 0.5), "p95": _percentil(lat, 0.95),
                     "por_ruta": {r: {"n": len(v), "p50": _percentil(v, 0.5), "p95": _percentil(v, 0.95)} for r, v in lat_ruta.items()}},
        "juez": {"evaluadas": len(juez), "calculadas_por_construccion": sum(1 for f in orig if f["metricas"].get("estado") == "calculada"),
                 "fidelidad": media("fidelidad"), "relevancia": media("relevancia"), "precision_contexto": media("precision_contexto")},
    }
    args.salida.mkdir(parents=True, exist_ok=True)
    nombre = f"evaluacion_{(resumen['redactor'] or 'servicio').replace(':', '_')}_{datetime.now():%H%M}"
    (args.salida / f"{nombre}.json").write_text(json.dumps({"resumen": resumen, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Evaluación con el banco de preguntas ({resumen['fecha']})", "",
          f"- Redactor: `{resumen['redactor']}` · Juez: `{resumen['juez']}` · {resumen['preguntas']} preguntas, {resumen['consultas']} consultas",
          f"- Decisión de dominio: exactitud {resumen['decision']['exactitud']}, F1 macro {resumen['decision']['f1_macro']}, "
          f"falsas aceptaciones {resumen['decision']['falsas_aceptaciones']}",
          f"- Exactitud con referencia: {resumen['exactitud']['correctas']}/{resumen['exactitud']['verificables']} "
          f"({resumen['exactitud']['proporcion']}); fallidas: {', '.join(resumen['exactitud']['fallidas']) or 'ninguna'}",
          f"- Por tipo: " + ", ".join(f"{t} {v}" for t, v in resumen["exactitud"]["por_tipo"].items()),
          f"- Recuperación: Hit@k {resumen['recuperacion']['hit']}, MRR {resumen['recuperacion']['mrr']} ({resumen['recuperacion']['preguntas']} preguntas)",
          f"- Consistencia ante paráfrasis: {resumen['consistencia_parafrasis']} · Estabilidad: {resumen['estabilidad']}",
          f"- Latencia: p50 {resumen['latencia']['p50']} s, p95 {resumen['latencia']['p95']} s",
          f"- Juez: {resumen['juez']['evaluadas']} evaluadas ({resumen['juez']['calculadas_por_construccion']} fieles por construcción); "
          f"fidelidad {resumen['juez']['fidelidad']}, relevancia {resumen['juez']['relevancia']}, precisión {resumen['juez']['precision_contexto']}",
          "", "| Pregunta | Decisión | Exacta | Ruta | s | Motivo |", "|---|---|---|---|---|---|"]
    md += [f"| {f['id']} | {f.get('decision')} ({'✓' if f['decision_ok'] else '✗'}) | {f['exacta']} | {f.get('ruta')} | {f.get('segundos')} | {f.get('motivo')} |" for f in orig]
    (args.salida / f"{nombre}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:11]))
    print(f"\n→ {(args.salida / nombre).relative_to(RAIZ)}.json / .md")


if __name__ == "__main__":
    main()
