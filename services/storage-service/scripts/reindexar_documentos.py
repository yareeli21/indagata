"""Reingiere al RAG los instrumentos que ya tienen documento final vigente.

Desde que la ingesta prefiere el documento final (`chunks_documento.py`), los
instrumentos publicados antes de ese cambio siguen indexados con chunks del JSON
técnico. Este script los recorre y los reindexa (reemplaza sus chunks).

Ejecutar dentro del contenedor:
    docker compose exec storage-service python scripts/reindexar_documentos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICIO))
if not (_SERVICIO / "shared").exists():  # ejecución local: `shared` vive en la raíz del repo
    sys.path.insert(1, str(_SERVICIO.parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import chroma_indexer  # noqa: E402


def main() -> int:
    db = SessionLocal()
    errores = 0
    try:
        ids = sorted({fila.id_crudo for fila in db.query(VersionConocimiento).filter(VersionConocimiento.estado == "vigente")})
        print(f"Instrumentos con documento vigente: {len(ids)}")
        for id_crudo in ids:
            try:
                r = chroma_indexer.indexar_instrumento(db, id_crudo, reindexar=True)
                print(f"  {id_crudo}: {r['chunks']} chunks")
            except chroma_indexer.IndiceError as exc:
                db.rollback()
                errores += 1
                print(f"  {id_crudo}: omitido ({exc})")
    finally:
        db.close()
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
