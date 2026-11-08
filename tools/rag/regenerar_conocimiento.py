"""Regenera el conocimiento de un instrumento ya publicado CONSERVANDO las decisiones de KPIs de la versión vigente.

Sirve cuando cambia cómo se arma el perfil o el documento final (7 nov 2026: textos de pregunta pegados en la
encuesta 127, indicaciones del entrevistador pegadas a p01 en la entrevista 129, polaridad de encuestas y análisis
de lo que se cuenta en entrevistas). Pasos, por la API:

  1. Perfil semántico nuevo (versión N+1).
  2. KPIs: las MISMAS decisiones de la versión vigente (aceptados, rechazados, justificaciones y si fueron editadas);
     de la evidencia se quitan las preguntas que ya no existen.
  3. Documento final; en encuestas la polaridad se infiere sola y en entrevistas se pide el análisis de respuestas.
     Se espera a que termine.
  4. Finalizar (JSON técnico) y publicar (reingesta al RAG en segundo plano).

Uso (con la app levantada):
    python tools/rag/regenerar_conocimiento.py 127 129
    python tools/rag/regenerar_conocimiento.py 60 --sin-modelo   # entrevista grande: análisis solo con reglas
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
GATEWAY = "http://localhost:8006"
ANALYSIS = "http://localhost:8002"


def _psql(sql: str) -> str:
    salida = subprocess.run(["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "indagata_db",
                             "-At", "-c", sql], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=True)
    return salida.stdout.strip()


def _decisiones_vigentes(id_crudo: int) -> list[dict]:
    return json.loads(_psql("select coalesce(decisiones_kpi, '[]') from tt_rag.version_conocimiento "
                            f"where id_crudo = {int(id_crudo)} and estado = 'vigente'") or "[]")


def regenerar(http: httpx.Client, cab: dict, id_crudo: int, modelo: bool = True) -> None:
    previas = _decisiones_vigentes(id_crudo)
    perfil = http.post(f"{GATEWAY}/conocimiento/{id_crudo}/perfil", headers=cab).raise_for_status().json()
    version = perfil["version"]
    existentes = set(re.findall(r"INS-\d{4}-[pr]\d+", json.dumps(perfil.get("perfil") or {})))
    print(f"{id_crudo}: perfil v{version} ({len(existentes)} preguntas)")
    decisiones = [{
        "kpi_id": int(d["kpi_id"]), "aceptado": d.get("decision") == "aceptado", "score": d.get("score") or 0,
        "componentes": d.get("componentes") or {},
        "evidencia": [e for e in d.get("evidencia") or [] if not existentes or e["pregunta_id"] in existentes],
        "justificacion": d.get("justificacion") or "",
        "justificacion_origen": "llm" if str(d.get("justificacion_origen", "")).startswith("llm") else "plantilla",
        "editada": bool(d.get("editada")),
    } for d in previas]
    if decisiones:
        http.post(f"{ANALYSIS}/vectorizacion/perfil/confirmar", headers=cab,
                  json={"id_crudo": id_crudo, "version": version, "decisiones": decisiones}).raise_for_status()
    print(f"   KPIs: {sum(d['aceptado'] for d in decisiones)} aceptados de {len(decisiones)}, como en la versión vigente")
    doc = http.post(f"{GATEWAY}/conocimiento/{id_crudo}/documento", headers=cab).raise_for_status().json()
    if _psql(f"select tipo_instrumento from tt_rag.raw_data where id_crudo = {int(id_crudo)}") == "entrevista":
        http.post(f"{GATEWAY}/conocimiento/{id_crudo}/documento/analisis", headers=cab,
                  params={"modelo": str(modelo).lower()}).raise_for_status()
    inicio = time.monotonic()
    while True:
        a = http.get(f"{GATEWAY}/conocimiento/{id_crudo}/documento/analisis", headers=cab)
        estado = a.json().get("estado") if a.status_code == 200 else "sin_analisis"
        if estado != "en_curso":
            break
        if time.monotonic() - inicio > 3 * 3600:
            sys.exit("El análisis no terminó en 3 horas.")
        print(f"   análisis: {a.json().get('hechos')} de {a.json().get('total')}", flush=True)
        time.sleep(30)
    print(f"   análisis del documento: {estado}")
    http.post(f"{GATEWAY}/api/metadata/{id_crudo}/finalizar", headers=cab).raise_for_status()
    http.post(f"{GATEWAY}/conocimiento/{id_crudo}/documento/{doc['version']}/publicar", headers=cab).raise_for_status()
    print(f"   documento v{doc['version']} publicado (la reingesta sigue en segundo plano)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="+", type=int)
    ap.add_argument("--sin-modelo", action="store_true", help="análisis de entrevistas solo con reglas (sin LLM)")
    ap.add_argument("--email", default="admin@indagata.com")
    ap.add_argument("--password", default="admin123")
    a = ap.parse_args()
    http = httpx.Client(timeout=httpx.Timeout(connect=10, read=900, write=60, pool=10))
    token = http.post(f"{GATEWAY}/auth/login", json={"email": a.email, "password": a.password}).json()["access_token"]
    cab = {"Authorization": f"Bearer {token}"}
    for id_crudo in a.ids:
        regenerar(http, cab, id_crudo, modelo=not a.sin_modelo)


if __name__ == "__main__":
    main()
