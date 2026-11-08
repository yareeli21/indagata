"""Recalcula la polaridad de las preguntas de una encuesta SOBRE SU DOCUMENTO VIGENTE (7 nov 2026).

La polaridad no entra en los chunks, así que no hace falta una versión nueva ni reingestar al RAG: se guarda el
documento con la polaridad nueva como otro artefacto en storage-service y la fila vigente apunta a él (igual que
`analisis._guardar`). Lo revisado por el investigador no se toca.

Uso (dentro del contenedor, con Ollama libre):
    docker compose exec -T knowledge-service python scripts/recalcular_polaridad.py 127 61
    # comparar otro modelo SIN guardar nada:
    docker compose exec -T knowledge-service python scripts/recalcular_polaridad.py 127 --modelo llama3.2:3b --solo-ver
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import documento, ollama, storage_client  # noqa: E402
from services.documento import polaridad  # noqa: E402


def recalcular(id_crudo: int, modelo: str | None = None, guardar: bool = True) -> None:
    db = SessionLocal()
    try:
        fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo, estado="vigente").one()
        doc = storage_client.descargar_json(fila.ruta_documento)
        if doc.get("respondentes") is None:
            print(f"{id_crudo}: no es encuesta, se omite")
            return
        for p in doc.get("preguntas") or []:
            if not polaridad.aplica(p) or (p.get("polaridad") or {}).get("estado") == "revisado":
                continue
            p["polaridad"] = polaridad.inferir(p, lambda pr: ollama.generar_json(pr, modelo))
            po = p["polaridad"]
            print(f"{id_crudo} {p['id']}: {po['origen']} | favorables {po['favorables']} | desfavorables {po['desfavorables']}",
                  flush=True)
        if not guardar:
            return
        documento.validar(doc)
        ref = storage_client.guardar_json(fila.id_crudo, "documento", doc, f"v{fila.version}_documento_final")
        fila.ruta_documento, fila.sha256 = ref["key"], ref.get("sha256")
        db.commit()
        print(f"{id_crudo}: guardado en {ref['key']}")
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="+", type=int)
    ap.add_argument("--modelo", default=None, help="modelo de Ollama (por defecto OLLAMA_MODEL)")
    ap.add_argument("--solo-ver", action="store_true", help="imprime la polaridad sin guardar el documento")
    a = ap.parse_args()
    for i in a.ids:
        recalcular(i, a.modelo, guardar=not a.solo_ver)
