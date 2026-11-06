"""Matriz de aceptación de entrevistas: formato, análisis de respuestas y chat.

Para cada variante de `corpus/entrevistas/variantes.json` (la misma entrevista en otro formato):
  1. Recorre los 7 pasos con las decisiones sugeridas y el análisis de respuestas antes de publicar.
  2. **Pruebas que deben pasar**: participantes e intercambios esperados, cada respuesta unida a su
     pregunta del guion, cada unidad del análisis literal en su respuesta, y el chat calcula las
     posturas igual que el documento.
  3. **Acuerdo con la anotación de referencia** (`referencia.json`, hecha a mano): postura
     (exactitud y kappa de Cohen), núcleo con la frase que responde, contexto fuera del núcleo.
     Se reporta como métrica: el modelo de 3B no es determinista.

Escribe `evidencias/formatos_<fecha>/entrevistas.json` y `entrevistas.md`.

Uso: python tools/formatos/verificar_entrevistas.py [--solo I01,I03] [--reusar I01=90]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "tools" / "rag"))
import procesar_instrumento as proc  # noqa: E402

GATEWAY = proc.GATEWAY
CORPUS = AQUI / "corpus" / "entrevistas"
POSTURA_P1 = "¿Cuántos entrevistados creen que las actividades extracurriculares actualmente tienen impacto en sus calificaciones?"
DIJO_E02 = "¿Qué dijo el participante E02 sobre las tutorías?"


def _norm(t: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w\s]", " ", sin.lower()).split())


def _kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def _subir(api: proc.Api, v: dict) -> int:
    archivos = {"archivo": (v["archivo"], (CORPUS / v["archivo"]).read_bytes()),
                "archivo_original": (v["original"], (CORPUS / v["original"]).read_bytes())}
    r = api.cliente.post(f"{GATEWAY}/instrumentos/upload", headers=api.cabeceras, data={"tipo_instrumento": "entrevista"}, files=archivos)
    if r.status_code >= 400:
        sys.exit(f"subida {r.status_code}: {r.text[:300]}")
    c = r.json()
    return int(c.get("id_crudo") or c.get("idCrudo") or c["id"])


def _procesar(api: proc.Api, id_crudo: int) -> list[str]:
    ejec = api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones")
    decisiones = {h["id"]: h["sugerida"] or h["opciones"][0] for h in ejec["hallazgos"]}
    if decisiones:
        api.pedir("PATCH", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/decisiones", json={"decisiones": decisiones})
    api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/confirmar")
    proc._desde_metadatos(api, id_crudo, 2, analizar=True)
    return [f"{h['tipo']}={decisiones.get(h['id'])}" for h in ejec["hallazgos"]]


def _esperar_ingesta(api: proc.Api, id_crudo: int, minimo: int, limite: float = 900) -> bool:
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        r = api.cliente.get(f"{GATEWAY}/almacenamiento/indice/instrumentos/{id_crudo}", headers=api.cabeceras)
        if r.status_code < 400 and r.json().get("indexado") and r.json().get("chunks", 0) >= minimo:
            return True
        time.sleep(5)
    return False


def _evaluar(api: proc.Api, id_crudo: int, v: dict, referencia: list[dict]) -> tuple[list[dict], dict]:
    doc = api.pedir("GET", f"{GATEWAY}/conocimiento/{id_crudo}/documento/json")
    entrevistas = doc.get("entrevistas") or []
    intercambios = [(e["participante"].rsplit("-", 1)[-1], i) for e in entrevistas for i in e.get("intercambios") or []]
    sin_pregunta = [p for p, i in intercambios if not i.get("pregunta_id")]
    no_literales = [u["texto"] for _, i in intercambios for u in (i.get("analisis") or {}).get("unidades") or []
                    if _norm(u["texto"]) not in _norm(i["respuesta"])]
    pruebas = [
        {"prueba": f"{v['participantes']} participantes", "ok": len(entrevistas) == v["participantes"], "obtenido": len(entrevistas)},
        {"prueba": f"{v['participantes'] * 4} intercambios", "ok": len(intercambios) == v["participantes"] * 4, "obtenido": len(intercambios)},
        {"prueba": "cada respuesta unida a su pregunta del guion", "ok": not sin_pregunta, "obtenido": f"sin pregunta: {len(sin_pregunta)}"},
        {"prueba": "todas las respuestas analizadas", "ok": all(i.get("analisis") for _, i in intercambios), "obtenido": doc.get("esquema_version")},
        {"prueba": "cada unidad es literal de su respuesta", "ok": not no_literales, "obtenido": f"no literales: {len(no_literales)}"},
    ]
    # Acuerdo con la referencia (persona E0n, pregunta p0k).
    ref = {(r["persona"], r["pregunta"]): r for r in referencia}
    pares, nucleo_ok, contexto_ok, n_contexto, metodos = [], 0, 0, 0, Counter()
    for persona, i in intercambios:
        k = int(re.sub(r"\D", "", (i.get("pregunta_id") or "p0").rsplit("-", 1)[-1]) or 0)
        r, an = ref.get((persona, k)), i.get("analisis") or {}
        if not r or not an:
            continue
        metodos[an.get("metodo")] += 1
        pares.append((r["postura"], an.get("postura")))
        nucleo_ok += _norm(r["nucleo_contiene"]) in _norm(an.get("nucleo", ""))
        if r["contexto_contiene"]:
            n_contexto += 1
            contexto_ok += _norm(r["contexto_contiene"]) not in _norm(an.get("nucleo", ""))
    metricas = {
        "n": len(pares), "metodos": dict(metodos),
        "postura_exactitud": round(sum(a == b for a, b in pares) / len(pares), 3) if pares else None,
        "postura_kappa": _kappa([a for a, _ in pares], [b for _, b in pares]),
        "nucleo_correcto": round(nucleo_ok / len(pares), 3) if pares else None,
        "contexto_excluido": round(contexto_ok / n_contexto, 3) if n_contexto else None,
        "descartadas_no_literales": sum((i.get("analisis") or {}).get("descartadas", 0) for _, i in intercambios),
        "discrepancias": [{"persona": p, "pregunta": k, "referencia": a, "sistema": b} for (a, b), (p, k) in
                          zip(pares, [(p, int(re.sub(r"\D", "", (i.get("pregunta_id") or "p0").rsplit("-", 1)[-1]) or 0)) for p, i in intercambios]) if a != b],
    }
    # Chat: posturas calculadas = posturas del documento.
    p1 = [i.get("analisis", {}).get("postura") for _, i in intercambios if (i.get("pregunta_id") or "").endswith("p01")]
    esperado = Counter(p1)
    r = api.pedir("POST", f"{GATEWAY}/rag/chat", json={"pregunta": v.get("pregunta_postura", POSTURA_P1), "stream": False,
                                                      "instrumentoIds": [str(id_crudo)]})
    texto = r.get("respuesta") or ""
    sin_citas = re.sub(r"\[(?:Fuente|Glosario|Ayuda)[^\]]*\]", " ", texto)  # «[Fuente 1]» no es una cifra
    cifras_ok = all(re.search(rf"(?<!\d){n}(?!\d)", sin_citas) for n in [len(p1), *esperado.values()])
    pruebas.append({"prueba": "chat: posturas de p01 calculadas como en el documento", "ok": r.get("ruta") in ("estructurada", "mixta")
                    and cifras_ok, "obtenido": f"{r.get('ruta')} · esperado {dict(esperado)}", "respuesta": texto})
    if v["participantes"] > 1:
        r = api.pedir("POST", f"{GATEWAY}/rag/chat", json={"pregunta": v.get("pregunta_dijo", DIJO_E02), "stream": False,
                                                          "instrumentoIds": [str(id_crudo)]})
        texto = r.get("respuesta") or ""
        hechos = v.get("dijo_contiene", ["martes", "ha servido"])  # basta uno de los hechos clave de su respuesta
        hechos = [hechos] if isinstance(hechos, str) else hechos
        pruebas.append({"prueba": "chat: qué dijo E02 (pregunta abierta)", "ok": any(_norm(h) in _norm(texto) for h in hechos),
                        "obtenido": r.get("ruta"), "respuesta": texto})
    return pruebas, metricas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo", default="")
    ap.add_argument("--reusar", default="")
    ap.add_argument("--corpus", default="entrevistas", help="carpeta dentro de corpus/ (entrevistas | entrevistas_docentes)")
    a = ap.parse_args()
    global CORPUS
    CORPUS = AQUI / "corpus" / a.corpus
    variantes = json.loads((CORPUS / "variantes.json").read_text(encoding="utf-8"))
    referencia = json.loads((CORPUS / "referencia.json").read_text(encoding="utf-8"))
    solo = {s for s in a.solo.split(",") if s}
    reusar = {k: int(x) for k, x in (p.split("=") for p in a.reusar.split(",") if p)}
    destino = RAIZ / "evidencias" / f"formatos_{datetime.now():%Y-%m-%d}"
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / f"{a.corpus}.json"
    resultados = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    api = proc.Api("admin@indagata.com", "admin123")

    for v in variantes:
        if solo and v["clave"] not in solo:
            continue
        print(f"=== {v['clave']} ({v['nivel']}) {v['descripcion']}", flush=True)
        caso = {"descripcion": v["descripcion"], "nivel": v["nivel"], "pruebas": [], "metricas": {}}
        try:
            id_crudo = reusar.get(v["clave"]) or _subir(api, v)
            caso["id_crudo"] = id_crudo
            if v["clave"] not in reusar:
                caso["decisiones_limpieza"] = _procesar(api, id_crudo)
            ok = _esperar_ingesta(api, id_crudo, 6 if v["participantes"] == 1 else 15)
            caso["pruebas"].append({"prueba": "ingesta al RAG", "ok": ok, "obtenido": ""})
            pruebas, metricas = _evaluar(api, id_crudo, v, referencia)
            caso["pruebas"] += pruebas
            caso["metricas"] = metricas
        except SystemExit as exc:
            caso["pruebas"].append({"prueba": "procesamiento", "ok": False, "obtenido": str(exc.code)[:300]})
        resultados[v["clave"]] = caso
        archivo.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        for p in caso["pruebas"]:
            print("    ", "OK" if p["ok"] else "XX", p["prueba"][:60], "|", p["obtenido"], flush=True)
        print("     métricas:", {k: v2 for k, v2 in caso["metricas"].items() if k != "discrepancias"}, flush=True)

    lineas = ["# Matriz de aceptación de formatos — entrevistas", "",
              f"Corrida: {datetime.now():%Y-%m-%d %H:%M}. Datos sintéticos (respuestas que divagan, anotación de referencia a mano).", "",
              "| Variante | Nivel | id | Pruebas OK | Postura (exactitud / κ) | Núcleo correcto | Contexto excluido | Fallos |",
              "|---|---|---|---|---|---|---|---|"]
    total = ok = 0
    for clave, c in sorted(resultados.items()):
        n_ok = sum(p["ok"] for p in c["pruebas"])
        total, ok = total + len(c["pruebas"]), ok + n_ok
        m = c.get("metricas") or {}
        fallos = "; ".join(f"{p['prueba'][:40]} ({p['obtenido']})" for p in c["pruebas"] if not p["ok"]) or "—"
        lineas.append(f"| {clave} {c['descripcion']} | {c['nivel']} | {c.get('id_crudo', '—')} | {n_ok}/{len(c['pruebas'])} | "
                      f"{m.get('postura_exactitud')} / {m.get('postura_kappa')} | {m.get('nucleo_correcto')} | {m.get('contexto_excluido')} | {fallos} |")
    lineas += ["", f"**Pruebas: {ok}/{total} ({100 * ok / max(total, 1):.1f} %)**"]
    (destino / f"{a.corpus}.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Total {ok}/{total}. Reporte: {destino / (a.corpus + chr(46) + "md")}")


if __name__ == "__main__":
    main()
