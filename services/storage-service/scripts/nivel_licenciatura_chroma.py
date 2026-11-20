"""Deja el nivel educativo en «Licenciatura» en la colección `instrumentos` de Chroma (15 nov 2026).

Complemento de `infrastructure/postgres/migrations/2026_21_nivel_licenciatura.sql`: cambia solo el parámetro, sin
re-vectorizar.
  * metadato `nivel` distinto de «Licenciatura» → «Licenciatura» (solo metadato; Chroma no recalcula el embedding).
  * ficha (`seccion = encabezado`) con la línea «Nivel educativo: …» → «Nivel educativo: Licenciatura», enviando
    el MISMO embedding que ya tenía (es una palabra de la ficha; no vale la pena re-vectorizar).
Idempotente. `--ensayo` solo cuenta lo que cambiaría.

Ejecutar dentro del contenedor:
    docker compose exec storage-service python scripts/nivel_licenciatura_chroma.py [--ensayo]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICIO))
if not (_SERVICIO / "shared").exists():  # ejecución local: `shared` vive en la raíz del repo
    sys.path.insert(1, str(_SERVICIO.parents[1]))

from shared.db.core.config import settings  # noqa: E402

from services import vectores  # noqa: E402

NIVEL = "Licenciatura"
_LINEA = re.compile(r"Nivel educativo: [^\n]*")
_LOTE = 500


def main() -> int:
    ensayo = "--ensayo" in sys.argv
    col = vectores.coleccion(settings.CHROMA_COLLECTION_INSTRUMENTOS)

    # 1. Metadato `nivel` (sin documentos ni embeddings: solo cambia el metadato).
    ids = col.get(where={"nivel": {"$ne": NIVEL}}, include=[])["ids"]
    print(f"Fragmentos con nivel distinto de {NIVEL}: {len(ids)}")
    if not ensayo:
        for i in range(0, len(ids), _LOTE):
            lote = ids[i:i + _LOTE]
            col.update(ids=lote, metadatas=[{"nivel": NIVEL}] * len(lote))

    # 2. Texto de la ficha, conservando su embedding.
    fichas = col.get(where={"seccion": "encabezado"}, include=["documents", "embeddings"])
    cambiar = [(i, _LINEA.sub(f"Nivel educativo: {NIVEL}", d), e)
               for i, d, e in zip(fichas["ids"], fichas["documents"], fichas["embeddings"])
               if d and _LINEA.search(d) and _LINEA.sub(f"Nivel educativo: {NIVEL}", d) != d]
    print(f"Fichas con otro nivel en el texto: {len(cambiar)}")
    if not ensayo and cambiar:
        col.update(ids=[c[0] for c in cambiar], documents=[c[1] for c in cambiar],
                   embeddings=[list(map(float, c[2])) for c in cambiar])

    print("Ensayo: no se cambió nada." if ensayo else "Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
