"""Llena `respuesta_interpretada` con los documentos finales que ya estaban vigentes
y pide su reingesta al RAG (desde el documento final).

Desde la migración 2026_12_rag, publicar un documento escribe sus respuestas en
formato largo y reingiere el instrumento. Los publicados ANTES de esa migración no
tienen filas ni chunks del documento: este script los pone al día. Es idempotente
(reemplaza las filas de cada instrumento).

Uso (dentro del contenedor):
    docker compose exec knowledge-service python scripts/poblar_respuestas.py [--sin-reingesta]
"""
from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))
if not (_RAIZ / "shared").exists():
    sys.path.insert(1, str(_RAIZ.parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import respuestas, storage_client  # noqa: E402


def main(reingerir: bool) -> int:
    db = SessionLocal()
    errores = 0
    try:
        vigentes = db.query(VersionConocimiento).filter(VersionConocimiento.estado == "vigente").all()
        print(f"Documentos vigentes: {len(vigentes)}")
        for fila in vigentes:
            try:
                doc = storage_client.descargar_json(fila.ruta_documento)
                n = respuestas.reemplazar(db, doc, fila.id_crudo, fila.version)
                db.commit()
                chunks = storage_client.indexar(fila.id_crudo).get("chunks") if reingerir else "-"
                print(f"  {fila.id_crudo} (v{fila.version}): {n} respuestas, {chunks} chunks")
            except storage_client.StorageError as exc:
                db.rollback()
                errores += 1
                print(f"  {fila.id_crudo}: error ({exc})")
    finally:
        db.close()
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main(reingerir="--sin-reingesta" not in sys.argv))
