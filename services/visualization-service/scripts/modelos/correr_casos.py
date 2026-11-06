"""Hace en el chat real las preguntas de un archivo de casos, como la investigadora en la interfaz.

Cada caso es una conversación nueva; cada turno manda los últimos 4 mensajes como historial, con el `consultaId` de
las respuestas (igual que `historialReciente` en `pixel-perfect-pixel/src/api/chat.ts`). Usa el redactor que tenga el
servicio (`OLLAMA_MODEL`), sin elegir modelo, y deja cada respuesta en `rag_log` como cualquier consulta del chat. Al
final imprime la corrida (`modelo=primera-última`) para `juzgar.py`, `calificar.py` y `reporte.py`.

Se corre desde el host (no necesita la base, solo el gateway):

    .venv\\Scripts\\python.exe services/visualization-service/scripts/modelos/correr_casos.py casos.json casos_pru03.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

API = os.environ.get("INDAGATA_API", "http://localhost:8006")
AQUI = Path(__file__).resolve().parent


def pedir(ruta: str, datos: dict, token: str | None = None) -> dict:
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + ruta, data=json.dumps(datos).encode(), method="POST", headers=cabeceras)
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())


def entrar(email: str, clave: str) -> str:
    return pedir("/auth/login", {"email": email, "password": clave})["access_token"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("casos", nargs="+", help="archivos de casos en scripts/modelos (p. ej. casos.json)")
    p.add_argument("--email", default="admin@indagata.com")
    p.add_argument("--clave", default="admin123")
    args = p.parse_args()

    # El token dura 60 minutos y una corrida con un modelo lento dura más: se renueva antes de cada caso.
    ids: list[int] = []
    modelos: set[str] = set()
    for nombre in args.casos:
        datos = json.loads((AQUI / nombre).read_text(encoding="utf-8"))
        instrumento = str(datos["instrumento"])
        print(f"\n===== {nombre} (instrumento {instrumento}) =====", flush=True)
        for caso in datos["casos"]:
            token = entrar(args.email, args.clave)
            historial: list[dict] = []
            print(f"\n--- Caso {caso['caso']}: {caso['titulo']}", flush=True)
            for turno in caso["turnos"]:
                inicio = time.time()
                r = pedir("/rag/chat", {"pregunta": turno["texto"], "instrumentoIds": [instrumento],
                                        "stream": False, "historial": historial[-4:]}, token)
                ids.append(r["consultaId"])
                if r.get("modelo"):
                    modelos.add(r["modelo"])
                print(f"[{r['consultaId']}] {time.time() - inicio:5.1f} s  ruta {r.get('ruta')}  "
                      f"{turno['texto'][:70]}", flush=True)
                historial += [{"rol": "usuario", "texto": turno["texto"]},
                              {"rol": "asistente", "texto": r["respuesta"][:1500], "consultaId": r["consultaId"]}]
    if ids:
        modelo = ", ".join(sorted(modelos)) or "<modelo>"
        print(f"\nCorrida: {modelo}={min(ids)}-{max(ids)}  ({len(ids)} consultas)")


if __name__ == "__main__":
    main()
