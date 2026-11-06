"""Evalúa el conjunto de regresión contra el chat en vivo (Fase 5 del rediseño, 28 oct 2026).

Para cada caso de `banco_regresion.json` pregunta a `/rag/chat` (sin caché) y mide:
  - exactitud del plan: intención, filtros (pregunta y valores), límite, campos, respondentes, preguntas, agrupar_por y
    nivel; solo se revisan los campos que el caso espera;
  - exactitud de la respuesta: cifras esperadas (todas), cifras alternativas (al menos una), textos y decisión;
  - tiempo por etapa (rag_log.tiempos) y latencia total;
  - métricas RAGAS bajo demanda (con --metricas: POST /rag/consultas/{id}/metricas y espera el resultado).

Modos: «antes» = flujo anterior, solo reglas (`usarInterpretacion: false`); «despues» = interpretación → ejecución →
redacción → verificación. Guarda un JSON y un resumen en Markdown en evidencias/rag_rediseno_2026-10-28/.

Uso (desde la raíz del repositorio, con el stack levantado):
    .venv\\Scripts\\python.exe tools\\rag\\regresion\\evaluar_regresion.py --modo despues [--metricas] [--casos C01,C02]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[3]
BANCO = Path(__file__).with_name("banco_regresion.json")
SALIDA = RAIZ / "evidencias" / "rag_rediseno_2026-10-28"
BASE = "http://localhost:8006"
_NIVELES = {"alto": "alto", "acuerdo": "alto", "medio": "medio", "neutral": "medio", "bajo": "bajo", "desacuerdo": "bajo"}
_NO_CIFRA = re.compile(r"\[fuente\s*\d+[^\]]*\]|\b(?:ins|kpi)-?\d+\b|\b[rpqaei]-?\d{1,4}\b", re.IGNORECASE)


def norm(texto: object) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def cifras(texto: str) -> set[float]:
    return {float(c.replace(",", ".")) for c in re.findall(r"\d+(?:[.,]\d+)?", _NO_CIFRA.sub(" ", texto or ""))}


# ── Comparación del plan ───────────────────────────────────────────────────────


def comparar_plan(esperado: dict, plan: dict | None) -> dict[str, bool]:
    """{campo: ¿coincide?} para cada campo que el caso espera."""
    if not esperado:
        return {}
    if plan is None:
        return {campo: False for campo in esperado}
    salida: dict[str, bool] = {}
    for campo, valor in esperado.items():
        real = plan.get(campo)
        if campo == "intencion":
            salida[campo] = real in valor
        elif campo == "filtros":
            reales = {f.get("pregunta"): {norm(v) for v in (f["valor"] if isinstance(f.get("valor"), list) else [f.get("valor")])}
                      for f in real or []}
            ok = len(reales) == len(valor)
            for f in valor:
                if f["pregunta"] not in reales or ("valores" in f and {norm(v) for v in f["valores"]} != reales[f["pregunta"]]):
                    ok = False
            salida[campo] = ok
        elif campo == "nivel":
            salida[campo] = _NIVELES.get(str(real)) == valor
        elif campo == "agrupar_por":
            salida[campo] = norm(real) == norm(valor)
        elif campo == "contexto":
            salida[campo] = {norm(k): norm(v) for k, v in (real or {}).items()} == {norm(k): norm(v) for k, v in valor.items()}
        elif campo == "campos":
            salida[campo] = (real or "solo_ids") == valor
        elif campo == "preguntas":
            salida[campo] = set(valor) <= set(real or [])
        else:
            salida[campo] = real == valor
    return salida


def comparar_respuesta(esperado: dict, r: dict) -> dict[str, bool]:
    respuesta = r.get("respuesta") or ""
    salida = {"decision": r.get("decision") == esperado.get("decision")}
    if "cifras" in esperado:
        presentes = cifras(respuesta)
        salida["cifras"] = all(float(c) in presentes for c in esperado["cifras"])
    if "cifras_alguna" in esperado:
        salida["cifras_alguna"] = bool(cifras(respuesta) & {float(c) for c in esperado["cifras_alguna"]})
    if "contiene" in esperado:
        salida["contiene"] = all(norm(t) in norm(respuesta) for t in esperado["contiene"])
    if "contiene_alguno" in esperado:
        salida["contiene_alguno"] = any(norm(t) in norm(respuesta) for t in esperado["contiene_alguno"])
    if esperado.get("sin_cifras"):
        salida["sin_cifras"] = not cifras(respuesta)
    if "ruta" in esperado:
        salida["ruta"] = r.get("ruta") in esperado["ruta"]
    return salida


# ── Ejecución ──────────────────────────────────────────────────────────────────


def _metricas(cliente: httpx.Client, consulta: int, espera: int = 240) -> dict:
    cliente.post(f"{BASE}/rag/consultas/{consulta}/metricas")
    inicio = time.time()
    while time.time() - inicio < espera:
        m = cliente.get(f"{BASE}/rag/consultas/{consulta}/metricas").json()
        if m.get("estado") not in ("calculando", "pendiente"):
            return m
        time.sleep(5)
    return {"estado": "sin_terminar"}


def evaluar(modo: str, con_metricas: bool, solo: set[str] | None) -> dict:
    token = httpx.post(f"{BASE}/auth/login", json={"email": "admin@indagata.com", "password": "admin123"}).json()["access_token"]
    cliente = httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=600)
    banco = json.loads(BANCO.read_text(encoding="utf-8"))
    resultados = []
    for caso in banco["casos"]:
        if solo and caso["id"] not in solo:
            continue
        inicio = time.perf_counter()
        r = cliente.post(f"{BASE}/rag/chat", json={
            "pregunta": caso["pregunta"], "instrumentoIds": caso["instrumentos"], "stream": False, "usarCache": False,
            "calcularMetricas": True, "historial": caso["historial"], "usarInterpretacion": modo == "despues"}).json()
        segundos = round(time.perf_counter() - inicio, 2)
        log = cliente.get(f"{BASE}/rag/consultas/{r['consultaId']}").json() if r.get("consultaId") else {}
        plan = ((log.get("plan") or {}).get("plan")) if modo == "despues" else None
        # Las reglas fijas de PA (privacidad, tareas ajenas) y la ayuda responden antes de interpretar: no hay plan
        # que comparar y no cuenta como error del plan.
        # (la ayuda deja en rag_log.plan solo su «verificacion»: sin «intentos» no hubo interpretación).
        sin_interpretar = (plan is None and "intentos" not in (log.get("plan") or {})
                           and r.get("decision") in ("fuera", "privacidad", "manipulacion", "ayuda"))
        fila = {
            "id": caso["id"], "categoria": caso["categoria"], "pregunta": caso["pregunta"], "segundos": segundos,
            "decision": r.get("decision"), "ruta": r.get("ruta"), "motivo": log.get("motivo"), "plan": plan,
            "correcciones": (log.get("plan") or {}).get("correcciones"), "tiempos": log.get("tiempos") or {},
            "respuesta": (r.get("respuesta") or "")[:3000],
            "plan_ok": comparar_plan(caso["plan_esperado"], plan) if modo == "despues" and not sin_interpretar else {},
            "respuesta_ok": comparar_respuesta(caso["esperado"], r),
        }
        if con_metricas and r.get("consultaId") and r.get("decision") == "dentro":
            m = _metricas(cliente, r["consultaId"])
            fila["metricas"] = {k: m.get(k) for k in ("estado", "fidelidad", "relevancia", "precisionContexto")}
        resultados.append(fila)
        ok = all(fila["respuesta_ok"].values()) and all(fila["plan_ok"].values())
        print(f"{caso['id']} {'OK ' if ok else 'MAL'} {segundos:>6} s  {fila['motivo']}  plan={fila['plan_ok']}  resp={fila['respuesta_ok']}",
              flush=True)
    return {"modo": modo, "fecha": datetime.now().isoformat(timespec="seconds"), "metricas": con_metricas,
            "resultados": resultados, "resumen": resumir(resultados, modo)}


def resumir(resultados: list[dict], modo: str) -> dict:
    def tasa(valores: list[bool]) -> float | None:
        return round(100 * sum(valores) / len(valores), 1) if valores else None

    campos_plan: dict[str, list[bool]] = {}
    for f in resultados:
        for campo, ok in f["plan_ok"].items():
            campos_plan.setdefault(campo, []).append(ok)
    respuesta = [all(f["respuesta_ok"].values()) for f in resultados]
    cifras_ok = [f["respuesta_ok"][k] for f in resultados for k in ("cifras", "cifras_alguna") if k in f["respuesta_ok"]]
    etapas: dict[str, list[int]] = {}
    for f in resultados:
        for etapa, ms in (f["tiempos"] or {}).items():
            etapas.setdefault(etapa, []).append(ms)
    metricas: dict[str, list[float]] = {}
    for f in resultados:
        for k, v in (f.get("metricas") or {}).items():
            if k != "estado" and isinstance(v, (int, float)):
                metricas.setdefault(k, []).append(v)
    return {
        "casos": len(resultados),
        "respuesta_correcta_pct": tasa(respuesta),
        "cifras_correctas_pct": tasa(cifras_ok),
        "decision_correcta_pct": tasa([f["respuesta_ok"]["decision"] for f in resultados]),
        "plan_por_campo_pct": {c: tasa(v) for c, v in campos_plan.items()} if modo == "despues" else None,
        "plan_completo_pct": tasa([all(f["plan_ok"].values()) for f in resultados if f["plan_ok"]]) if modo == "despues" else None,
        "segundos_mediana": round(statistics.median(f["segundos"] for f in resultados), 2) if resultados else None,
        "segundos_max": max((f["segundos"] for f in resultados), default=None),
        "ms_por_etapa_mediana": {e: int(statistics.median(v)) for e, v in etapas.items()},
        "metricas_media": {k: round(statistics.mean(v), 3) for k, v in metricas.items()},
        "fallas": [f["id"] for f, ok in zip(resultados, respuesta) if not ok],
    }


def markdown(reporte: dict) -> str:
    r = reporte["resumen"]
    lineas = [f"# Regresión del chat — modo «{reporte['modo']}» ({reporte['fecha']})", "",
              f"- Casos: {r['casos']}", f"- Respuesta correcta: {r['respuesta_correcta_pct']} %",
              f"- Cifras correctas: {r['cifras_correctas_pct']} %", f"- Decisión de dominio correcta: {r['decision_correcta_pct']} %",
              f"- Tiempo por pregunta: mediana {r['segundos_mediana']} s, máximo {r['segundos_max']} s"]
    if r["plan_completo_pct"] is not None:
        lineas.append(f"- Plan completo correcto: {r['plan_completo_pct']} %; por campo: {r['plan_por_campo_pct']}")
    if r["ms_por_etapa_mediana"]:
        lineas.append(f"- Mediana por etapa (ms): {r['ms_por_etapa_mediana']}")
    if r["metricas_media"]:
        lineas.append(f"- Métricas RAGAS (media): {r['metricas_media']}")
    lineas += [f"- Fallas: {', '.join(r['fallas']) or 'ninguna'}", "", "| Caso | Categoría | ¿Bien? | s | Motivo |", "|---|---|---|---|---|"]
    for f in reporte["resultados"]:
        ok = all(f["respuesta_ok"].values()) and all(f["plan_ok"].values())
        lineas.append(f"| {f['id']} | {f['categoria']} | {'sí' if ok else 'no'} | {f['segundos']} | {f['motivo']} |")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--modo", choices=["antes", "despues"], required=True)
    args.add_argument("--metricas", action="store_true")
    args.add_argument("--casos", default="")
    args.add_argument("--recalificar", action="store_true",
                      help="vuelve a calificar el reporte guardado del modo con el banco actual, sin preguntar al chat")
    a = args.parse_args()
    if a.recalificar:
        reporte = json.loads((SALIDA / f"regresion_{a.modo}.json").read_text(encoding="utf-8"))
        esperados = {c["id"]: c for c in json.loads(BANCO.read_text(encoding="utf-8"))["casos"]}
        for f in reporte["resultados"]:
            caso = esperados[f["id"]]
            f["respuesta_ok"] = comparar_respuesta(caso["esperado"], f)
            if f["plan_ok"]:
                f["plan_ok"] = comparar_plan(caso["plan_esperado"], f["plan"])
        reporte["resumen"] = resumir(reporte["resultados"], a.modo)
    else:
        reporte = evaluar(a.modo, a.metricas, set(a.casos.split(",")) if a.casos else None)
    SALIDA.mkdir(parents=True, exist_ok=True)
    nombre = f"regresion_{a.modo}"
    (SALIDA / f"{nombre}.json").write_text(json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDA / f"{nombre}.md").write_text(markdown(reporte), encoding="utf-8")
    print(json.dumps(reporte["resumen"], ensure_ascii=False, indent=1))
