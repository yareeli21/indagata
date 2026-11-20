"""Compara enc_10_turno original (con secciones) contra sus variantes sin secciones.

Por instrumento: bloques de fiabilidad de la limpieza, perfil semántico (fuente, secciones,
avisos, textos de pregunta), documento final, KPIs aceptados y las preguntas de referencia
del chat que no dependen de los KPIs (Q01–Q06, Q14, Q17, Q18 de preguntas_referencia.json).

Uso: python comparar.py base=59,A=<id>,B=<id>,C=<id>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
GATEWAY = "http://localhost:8006"
CASOS = ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q14", "Q17", "Q18"]

ids = dict(p.split("=") for p in sys.argv[1].split(","))
refs = {q["id"]: q for q in json.loads((RAIZ / "tools/rag/preguntas_referencia.json").read_text(encoding="utf-8"))["preguntas"]}

http = httpx.Client(timeout=httpx.Timeout(connect=10, read=600, write=60, pool=10))
token = http.post(f"{GATEWAY}/auth/login", json={"email": "admin@indagata.com", "password": "admin123"}).json()["access_token"]
cab = {"Authorization": f"Bearer {token}"}


def get(ruta: str):  # noqa: ANN201
    r = http.get(f"{GATEWAY}{ruta}", headers=cab)
    return r.json() if r.status_code < 400 else {"error": r.status_code, "detalle": r.text[:300]}


salida: dict = {}
for nombre, i in ids.items():
    res = get(f"/limpieza/{i}/resumen")
    perfil = get(f"/conocimiento/{i}/perfil")
    doc = get(f"/conocimiento/{i}/documento/json")
    p = perfil.get("perfil") or {}
    d = doc.get("documento") if isinstance(doc.get("documento"), dict) else doc
    preguntas_doc = d.get("preguntas") or []
    salida[nombre] = {
        "id_crudo": i,
        "fiabilidad": [{"bloque": b.get("bloque"), "alfa": b.get("alfa"), "n_items": b.get("n_items")}
                       for b in (res.get("estadistica") or {}).get("fiabilidad") or []],
        "sugerencias": [s.get("texto") or s.get("mensaje") or s for s in res.get("sugerencias") or []],
        "perfil_fuente": perfil.get("fuente"),
        "perfil_n_preguntas": perfil.get("n_preguntas"),
        "perfil_avisos": [a.get("codigo") for a in perfil.get("avisos") or []],
        "perfil_secciones": [{"nombre": s.get("nombre"), "n": len(s.get("preguntas") or [])} for s in p.get("secciones") or []],
        "perfil_textos": [q.get("texto") for s in p.get("secciones") or [] for q in s.get("preguntas") or []],
        "doc_secciones": [s.get("nombre") for s in d.get("secciones") or []],
        "doc_n_preguntas": len(preguntas_doc),
        "doc_n_respondentes": len(d.get("respondentes") or []),
        "kpis": [k.get("nombre") or k.get("kpi") for k in d.get("kpis_asociados") or []],
        "chat": {},
    }
    for c in CASOS:
        q = refs[c]
        t0 = time.monotonic()
        r = http.post(f"{GATEWAY}/rag/chat", headers=cab,
                      json={"pregunta": q["pregunta"], "stream": False, "instrumentoIds": [i]}).json()
        salida[nombre]["chat"][c] = {"pregunta": q["pregunta"], "esperada": q["esperada"],
                                     "decision": r.get("decision"), "ruta": r.get("ruta"),
                                     "respuesta": (r.get("respuesta") or "").strip(),
                                     "segundos": round(time.monotonic() - t0, 1)}
        print(nombre, c, r.get("decision"), r.get("ruta"), flush=True)
    (AQUI / "comparacion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok")
