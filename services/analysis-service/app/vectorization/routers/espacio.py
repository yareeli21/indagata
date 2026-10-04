"""Router — ESPACIO VECTORIAL (read-only).

Expone una proyección 2D del espacio de embeddings para visualizarlo en el
frontend:

  GET /vectorizacion/espacio   → lee las colecciones `kpis` y `summary_instrument`
                                 de Chroma, apila sus embeddings, los proyecta a 2D
                                 con PCA (sobre el conjunto combinado) y devuelve los
                                 puntos coloreables por colección.

Es de SOLO LECTURA: nunca hace upsert ni escribe en Chroma. Reutiliza la lógica de
etiquetado y proyección del visor scratch (`chroma-viz/scratch/viewer/app.py`).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, status
from sklearn.decomposition import PCA

from app.vectorization.core.chroma_client import get_client, get_or_create_collection
from app.vectorization.dependencies import UsuarioActual

router = APIRouter(prefix="/vectorizacion", tags=["vectorizacion-espacio"])

# Colecciones a proyectar, en orden estable.
_COLECCIONES = ("kpis", "summary_instrument")


def _label_for(coleccion: str, meta: dict[str, Any] | None, doc: str | None, pid: str) -> str:
    """Etiqueta legible de un punto (misma precedencia que el visor scratch)."""
    meta = meta or {}
    if coleccion == "kpis":
        return str(meta.get("nombre_kpi") or doc or pid)
    # summary_instrument u otras
    for k in ("titulo", "Título", "nombre_archivo", "id_instrumento"):
        if meta.get(k):
            return str(meta[k])
    return str(pid)


def _gather() -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Lee las colecciones, aplica PCA conjunto y devuelve (puntos, resumen)."""
    client = get_client()
    puntos: list[dict[str, Any]] = []
    vectores: list[list[float]] = []
    resumen: dict[str, int] = {nombre: 0 for nombre in _COLECCIONES}

    for nombre in _COLECCIONES:
        collection = get_or_create_collection(nombre, client=client)
        data = collection.get(include=["embeddings", "metadatas", "documents"])
        ids = data.get("ids") or []
        embs = data.get("embeddings")
        metas = data.get("metadatas") or [None] * len(ids)
        docs = data.get("documents") or [None] * len(ids)
        if embs is None:
            continue
        for i, pid in enumerate(ids):
            emb = embs[i]
            if emb is None:
                continue
            vectores.append(list(emb))
            puntos.append(
                {
                    "id": str(pid),
                    "coleccion": nombre,
                    "label": _label_for(
                        nombre,
                        metas[i] if i < len(metas) else None,
                        docs[i] if i < len(docs) else None,
                        str(pid),
                    ),
                }
            )
            resumen[nombre] += 1

    if not vectores:
        return [], resumen

    arr = np.asarray(vectores, dtype=float)
    n_comp = 2 if arr.shape[0] >= 2 and arr.shape[1] >= 2 else 1
    coords = PCA(n_components=n_comp).fit_transform(arr)
    for j, p in enumerate(puntos):
        p["x"] = float(coords[j, 0])
        p["y"] = float(coords[j, 1]) if n_comp == 2 else 0.0

    return puntos, resumen


@router.get(
    "/espacio",
    status_code=status.HTTP_200_OK,
    summary="Mapa 2D del espacio vectorial (read-only)",
    description=(
        "Lee las colecciones `kpis` y `summary_instrument` de ChromaDB, apila sus "
        "embeddings (768-dim) y los proyecta a 2D con PCA sobre el conjunto combinado. "
        "Devuelve los puntos `{x, y, coleccion, label, id}` para pintar un dispersograma "
        "coloreado por colección. Es de solo lectura: no modifica Chroma."
    ),
)
def espacio_vectorial(usuario_actual: UsuarioActual) -> dict[str, Any]:
    try:
        puntos, resumen = _gather()
    except Exception as exc:  # noqa: BLE001 -- reporta el error de Chroma tal cual, como el visor
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {"puntos": puntos, "colecciones": resumen}
