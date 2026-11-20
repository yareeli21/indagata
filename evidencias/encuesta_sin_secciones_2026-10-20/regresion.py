"""Regresión: preguntas de referencia (enc_10=59, pru_01=55, ent_01=60) tras la ficha completa.

Compara la decisión de dominio con la esperada y guarda las respuestas (sin métricas).
"""
import json
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
IDS = {"enc_10": "59", "pru_01": "55", "ent_01": "60"}
refs = json.loads((AQUI.parents[1] / "tools/rag/preguntas_referencia.json").read_text(encoding="utf-8"))["preguntas"]
http = httpx.Client(timeout=600)
tok = http.post("http://localhost:8006/auth/login", json={"email": "admin@indagata.com", "password": "admin123"}).json()["access_token"]
salida = []
for q in refs:
    alcance = q.get("alcance") or []
    if any(a not in IDS for a in alcance):
        continue
    r = http.post("http://localhost:8006/rag/chat", headers={"Authorization": f"Bearer {tok}"},
                  json={"pregunta": q["pregunta"], "stream": False, "instrumentoIds": [IDS[a] for a in alcance]}).json()
    ok = r.get("decision") == q.get("decision_esperada")
    salida.append({"id": q["id"], "pregunta": q["pregunta"], "esperada": q["esperada"], "decision": r.get("decision"),
                   "decision_esperada": q.get("decision_esperada"), "ruta": r.get("ruta"), "respuesta": r.get("respuesta")})
    print(q["id"], "OK " if ok else "XX ", r.get("decision"), r.get("ruta"), "|", (r.get("respuesta") or "")[:200].replace("\n", " "), flush=True)
(AQUI / "regresion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
