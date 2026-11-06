"""Matriz de aceptación de formatos: cada variante del corpus contra su resultado esperado.

Para cada variante de `corpus/encuestas/variantes.json`:
  - **rechazada**: la subida debe responder 422 con el motivo esperado;
  - **aceptada**: recorre los 7 pasos (decisiones sugeridas, como `tools/rag/procesar_instrumento.py`),
    espera la ingesta al RAG y comprueba la estructura (8 preguntas con el texto del original,
    2 dimensiones con α) y las preguntas de referencia del chat (cifras exactas, hechos clave,
    decisión de dominio).

Escribe `evidencias/formatos_<fecha>/encuestas.json` y `encuestas.md`, caso por caso.

Uso (con la app levantada):
    python tools/formatos/verificar_formatos.py [--solo E05,E07] [--reusar E01=71,E03=73]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "tools" / "rag"))
import procesar_instrumento as proc  # noqa: E402

GATEWAY = proc.GATEWAY
CORPUS = AQUI / "corpus" / "encuestas"
PREGUNTAS = {q["id"]: q for q in json.loads((RAIZ / "tools/rag/preguntas_referencia.json").read_text(encoding="utf-8"))["preguntas"]}

# Hechos que la respuesta debe contener (sin distinguir mayúsculas ni acentos) o decisión esperada.
CHAT = {
    "Q01": {"hechos": ["R017", "De acuerdo"]},
    "Q02": {"hechos": ["Ni de acuerdo ni en desacuerdo"]},
    "Q03": {"hechos": ["R002"]},
    "Q04": {"hechos": ["No existe"]},
    "Q05": {"hechos": ["13.3", "4", "30"]},
    "Q06": {"hechos": ["16.7", "10", "60"]},
    "Q14": {"hechos": ["evaluaci", "ambiente"]},
    "Q17": {"decision": "sin_informacion"},
    "Q18": {"decision": "privacidad"},
}


def _norm(t: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def _contiene(texto: str, hecho: str) -> bool:
    if re.fullmatch(r"\d+(\.\d+)?", hecho):  # cifras: como número completo, no dentro de otro
        return re.search(rf"(?<![\d.]){re.escape(hecho)}(?![\d])", texto) is not None
    return _norm(hecho) in _norm(texto)


def _subir(api: proc.Api, v: dict) -> tuple[int | None, str]:
    archivos = {"archivo": (v["archivo"], (CORPUS / v["archivo"]).read_bytes())}
    if v.get("original"):
        archivos["archivo_original"] = (v["original"], (CORPUS / v["original"]).read_bytes())
    r = api.cliente.post(f"{GATEWAY}/instrumentos/upload", headers=api.cabeceras,
                         data={"tipo_instrumento": "encuesta"}, files=archivos)
    if r.status_code >= 400:
        return None, f"{r.status_code}: {r.json().get('detail', r.text)}"
    c = r.json()
    return int(c.get("id_crudo") or c.get("idCrudo") or c["id"]), ""


def _procesar(api: proc.Api, id_crudo: int) -> None:
    ejec = api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones")
    decisiones = {h["id"]: h["sugerida"] or h["opciones"][0] for h in ejec["hallazgos"]}
    if decisiones:
        api.pedir("PATCH", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/decisiones", json={"decisiones": decisiones})
    api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/confirmar")
    proc._desde_metadatos(api, id_crudo, 2)


def _esperar_ingesta(api: proc.Api, id_crudo: int, minimo_chunks: int = 60, limite: float = 900) -> bool:
    """Al aprobar se indexa el JSON técnico (pocos chunks); el documento final llega después,
    en segundo plano, con al menos un chunk por respondente."""
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        r = api.cliente.get(f"{GATEWAY}/almacenamiento/indice/instrumentos/{id_crudo}", headers=api.cabeceras)
        if r.status_code < 400 and r.json().get("indexado") and r.json().get("chunks", 0) > minimo_chunks:
            return True
        time.sleep(5)
    return False


def _estructura(api: proc.Api, id_crudo: int, preguntas_original: list[str], v: dict) -> list[dict]:
    perfil = api.pedir("GET", f"{GATEWAY}/conocimiento/{id_crudo}/perfil")
    res = api.pedir("GET", f"{GATEWAY}/limpieza/{id_crudo}/resumen")
    textos = [q.get("texto", "") for s in (perfil.get("perfil") or {}).get("secciones") or [] for q in s.get("preguntas") or []]
    faltan = [p for p in preguntas_original if not any(_norm(t).startswith(_norm(p)[:35]) or _norm(p)[:35] in _norm(t) for t in textos)]
    bloques = [b for b in (res.get("estadistica") or {}).get("fiabilidad") or [] if b.get("bloque") != "Todas las escalas Likert"]
    return [
        {"prueba": "8 preguntas en el perfil", "ok": len(textos) == 8, "obtenido": len(textos)},
        {"prueba": "texto del original en cada pregunta", "ok": not faltan, "obtenido": f"faltan {len(faltan)}" if faltan else "todas"},
        {"prueba": f"{v.get('dimensiones', 0)} dimensiones con α", "ok": len(bloques) == v.get("dimensiones", 0),
         "obtenido": ", ".join(f"{b.get('bloque')} α={b.get('alfa')}" for b in bloques) or "solo α global"},
        {"prueba": "avisos del perfil", "ok": True, "obtenido": ", ".join(a.get("codigo", "") for a in perfil.get("avisos") or []) or "—"},
    ]


def _chat(api: proc.Api, id_crudo: int) -> list[dict]:
    salida = []
    for qid, esperado in CHAT.items():
        r = api.pedir("POST", f"{GATEWAY}/rag/chat", json={"pregunta": PREGUNTAS[qid]["pregunta"], "stream": False,
                                                          "instrumentoIds": [str(id_crudo)]})
        texto = r.get("respuesta") or ""
        if "decision" in esperado:
            ok, obtenido = r.get("decision") == esperado["decision"], r.get("decision")
        else:
            faltan = [h for h in esperado["hechos"] if not _contiene(texto, h)]
            ok, obtenido = r.get("decision") == "dentro" and not faltan, f"faltan {faltan}" if faltan else "ok"
        salida.append({"prueba": f"{qid} {PREGUNTAS[qid]['pregunta']}", "ok": ok, "obtenido": obtenido, "respuesta": texto})
    return salida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo", default="")
    ap.add_argument("--reusar", default="", help="CLAVE=id_crudo ya procesados (no se vuelven a subir)")
    ap.add_argument("--salida", default="")
    a = ap.parse_args()
    variantes = json.loads((CORPUS / "variantes.json").read_text(encoding="utf-8"))
    solo = {s for s in a.solo.split(",") if s}
    reusar = {k: int(v) for k, v in (p.split("=") for p in a.reusar.split(",") if p)}
    preguntas_original = [p.rstrip(".") for p in re.findall(r"^\d+\.\s+(.+)$",
                          (RAIZ / "storage/instrumentos_sinteticos/encuestas/enc_10_turno_original.txt").read_text(encoding="utf-8"), re.M)]
    destino = Path(a.salida) if a.salida else RAIZ / "evidencias" / f"formatos_{datetime.now():%Y-%m-%d}"
    destino.mkdir(parents=True, exist_ok=True)
    archivo_json = destino / "encuestas.json"
    resultados = json.loads(archivo_json.read_text(encoding="utf-8")) if archivo_json.exists() else {}
    api = proc.Api("admin@indagata.com", "admin123")

    for v in variantes:
        if solo and v["clave"] not in solo:
            continue
        print(f"=== {v['clave']} ({v['nivel']}) {v['descripcion']}", flush=True)
        caso = {"descripcion": v["descripcion"], "nivel": v["nivel"], "pruebas": []}
        id_crudo = reusar.get(v["clave"])
        if id_crudo is None:
            id_crudo, error = _subir(api, v)
            if v["nivel"] == "rechazado":
                caso["pruebas"].append({"prueba": "la subida se rechaza con el motivo", "ok": id_crudo is None and v["rechazo"] in error,
                                        "obtenido": error or f"se aceptó (id {id_crudo})"})
                resultados[v["clave"]] = caso
                archivo_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
                print("   ", caso["pruebas"][-1], flush=True)
                continue
            if id_crudo is None:
                caso["pruebas"].append({"prueba": "la subida se acepta", "ok": False, "obtenido": error})
                resultados[v["clave"]] = caso
                archivo_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
                continue
        caso["id_crudo"] = id_crudo
        try:
            if v["clave"] not in reusar:
                _procesar(api, id_crudo)
            caso["pruebas"].append({"prueba": "ingesta al RAG", "ok": _esperar_ingesta(api, id_crudo), "obtenido": ""})
            caso["pruebas"] += _estructura(api, id_crudo, preguntas_original, v) + _chat(api, id_crudo)
        except SystemExit as exc:  # procesar_instrumento termina con el error de la API: se registra y se sigue
            caso["pruebas"].append({"prueba": "procesamiento de los 7 pasos", "ok": False, "obtenido": str(exc.code)[:300]})
        resultados[v["clave"]] = caso
        archivo_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        for p in caso["pruebas"]:
            print("    ", "OK" if p["ok"] else "XX", p["prueba"][:70], "|", p["obtenido"], flush=True)

    # Resumen en Markdown.
    lineas = ["# Matriz de aceptación de formatos — encuestas", "", f"Corrida: {datetime.now():%Y-%m-%d %H:%M}. Datos sintéticos (enc_10_turno).", "",
              "| Variante | Nivel | id | Pruebas OK | Fallos |", "|---|---|---|---|---|"]
    total = ok = 0
    for clave, c in sorted(resultados.items()):
        n_ok = sum(p["ok"] for p in c["pruebas"])
        total += len(c["pruebas"])
        ok += n_ok
        fallos = "; ".join(f"{p['prueba'][:40]} ({p['obtenido']})" for p in c["pruebas"] if not p["ok"]) or "—"
        lineas.append(f"| {clave} {c['descripcion']} | {c['nivel']} | {c.get('id_crudo', '—')} | {n_ok}/{len(c['pruebas'])} | {fallos} |")
    lineas += ["", f"**Total: {ok}/{total} ({100 * ok / max(total, 1):.1f} %)**"]
    (destino / "encuestas.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Total {ok}/{total}. Reporte: {destino / 'encuestas.md'}")


if __name__ == "__main__":
    main()
