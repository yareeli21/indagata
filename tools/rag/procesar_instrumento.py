"""Procesa un instrumento por la API hasta publicar su documento final (sin la interfaz).

Recorre los mismos 7 pasos del asistente «Subir instrumento», tomando en cada
decisión la opción SUGERIDA por el sistema (como si la investigadora aceptara todo):

  1. Archivo      POST /instrumentos/upload
  2. Limpieza     fase automática → decisiones sugeridas → confirmar
  3-4. Metadatos  propuesta Dublin Core y del tipo
  5. Aprobar      /api/metadata/{id}/aprobar → perfil semántico
  6. KPIs         propuestas por perfil → se aceptan los N primeros
  7. Guardar      documento final → finalizar → publicar (reingesta al RAG)

Sirve para preparar los instrumentos de la verificación de punta a punta y de la
evaluación fuera de línea del RAG (por ejemplo enc_10, la encuesta con turno).

Uso (con la app levantada):
    python tools/rag/procesar_instrumento.py storage/instrumentos_sinteticos/encuestas/enc_10_turno_respondido.csv \
        --tipo encuesta --original storage/instrumentos_sinteticos/encuestas/enc_10_turno_original.txt [--kpis 2]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx

GATEWAY = "http://localhost:8006"
ANALYSIS = "http://localhost:8002"
_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)


def _texto(valor: Any) -> str:
    """Valor propuesto → texto del formulario (igual que el frontend)."""
    if valor is None:
        return ""
    if isinstance(valor, list):
        return ", ".join(map(str, valor))
    if isinstance(valor, dict):
        return "\n".join(f"{k}: {v}" for k, v in valor.items())
    return str(valor)


class Api:
    def __init__(self, email: str, password: str) -> None:
        self.cliente = httpx.Client(timeout=_TIMEOUT)
        r = self.cliente.post(f"{GATEWAY}/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        self.cabeceras = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def pedir(self, metodo: str, url: str, **kwargs: Any) -> Any:
        r = self.cliente.request(metodo, url, headers=self.cabeceras, **kwargs)
        if r.status_code >= 400:
            sys.exit(f"{metodo} {url} → {r.status_code}: {r.text[:500]}")
        return r.json()


def procesar(api: Api, archivo: Path, tipo: str, original: Path | None, n_kpis: int) -> int:
    archivos = {"archivo": (archivo.name, archivo.read_bytes())}
    if original:
        archivos["archivo_original"] = (original.name, original.read_bytes())
    carga = api.pedir("POST", f"{GATEWAY}/instrumentos/upload", data={"tipo_instrumento": tipo}, files=archivos)
    id_crudo = int(carga.get("id_crudo") or carga.get("idCrudo") or carga["id"])
    print(f"1. Archivo: id_crudo={id_crudo}")

    ejec = api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones")
    decisiones = {h["id"]: h["sugerida"] or h["opciones"][0] for h in ejec["hallazgos"]}
    if decisiones:
        api.pedir("PATCH", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/decisiones", json={"decisiones": decisiones})
    api.pedir("POST", f"{GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/confirmar")
    print(f"2. Limpieza: v{ejec['version']} confirmada con {len(decisiones)} decisiones sugeridas")

    dc = api.pedir("GET", f"{GATEWAY}/api/metadata/{id_crudo}/propuesta")["valores"]
    enr = api.pedir("GET", f"{GATEWAY}/api/enrichment/{id_crudo}/propuesta")["valores"]
    cuerpo = {"dublin_core": {k: _texto(v) for k, v in dc.items() if k.startswith("dc_")},
              "enriquecidos": {k: _texto(v) for k, v in enr.items()}}
    print(f"3-4. Metadatos: «{cuerpo['dublin_core'].get('dc_title')}»")

    api.pedir("POST", f"{GATEWAY}/api/metadata/{id_crudo}/aprobar", json=cuerpo)
    perfil = api.pedir("POST", f"{GATEWAY}/conocimiento/{id_crudo}/perfil")
    print(f"5. Aprobado; perfil v{perfil.get('version')}")

    prop = api.pedir("POST", f"{ANALYSIS}/vectorizacion/perfil/propuestas", json={"id_crudo": id_crudo})
    decis = [{"kpi_id": k["kpi_id"], "aceptado": i < n_kpis, "score": k["score"], "componentes": k["componentes"],
              "evidencia": [{"pregunta_id": e["pregunta_id"], "similitud": e["similitud"]} for e in k["evidencia"]],
              "justificacion": k["justificacion"], "justificacion_origen": k["justificacion_origen"], "editada": False}
             for i, k in enumerate(prop["kpis"])]
    if decis:
        api.pedir("POST", f"{ANALYSIS}/vectorizacion/perfil/confirmar",
                  json={"id_crudo": id_crudo, "version": prop["version"], "decisiones": decis})
    print(f"6. KPIs: {min(n_kpis, len(decis))} aceptados de {len(decis)} sugeridos: "
          f"{[k['nombre'] for k in prop['kpis'][:n_kpis]]}")

    doc = api.pedir("POST", f"{GATEWAY}/conocimiento/{id_crudo}/documento")
    api.pedir("POST", f"{GATEWAY}/api/metadata/{id_crudo}/finalizar")
    api.pedir("POST", f"{GATEWAY}/conocimiento/{id_crudo}/documento/{doc['version']}/publicar")
    print(f"7. Documento v{doc['version']} publicado (la reingesta al RAG sigue en segundo plano)")
    return id_crudo


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("archivo", type=Path)
    p.add_argument("--tipo", required=True, choices=["encuesta", "entrevista", "prueba_estandarizada"])
    p.add_argument("--original", type=Path)
    p.add_argument("--kpis", type=int, default=2, help="KPIs sugeridos que se aceptan (los de mayor puntaje)")
    p.add_argument("--email", default="admin@indagata.com")
    p.add_argument("--password", default="admin123")
    a = p.parse_args()
    procesar(Api(a.email, a.password), a.archivo, a.tipo, a.original, a.kpis)


if __name__ == "__main__":
    main()
