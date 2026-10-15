"""Vecinos de un punto del espacio vectorial.

El parecido es SIEMPRE el coseno entre los embeddings originales (768-dim); la
distancia en el mapa 2D no se usa para nada. Según el tipo de origen:
  - KPI: instrumentos más asociados, KPIs parecidos y las preguntas (chunks) más
    cercanas de cualquier instrumento.
  - Instrumento: KPIs más cercanos, instrumentos parecidos y los chunks propios
    que mejor lo representan.
  - Chunk: KPIs e instrumentos más cercanos y chunks parecidos.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from services.espacio import algebra
from services.espacio.mapa import Elemento, Espacio, chunks_completos, obtener_espacio

TIPOS = ("kpi", "instrumento", "chunk")


class PuntoNoEncontrado(LookupError):
    """El punto pedido no está en el espacio vigente."""


def _ranking(origen: Elemento, candidatos: list[Elemento], k: int) -> list[tuple[Elemento, float]]:
    candidatos = [c for c in candidatos if c.id != origen.id]
    if not candidatos or k <= 0:
        return []
    sims = algebra.similitudes(origen.vector, np.vstack([c.vector for c in candidatos]))
    orden = np.argsort(-sims, kind="stable")[:k]
    return [(candidatos[i], float(sims[i])) for i in orden]


def _vecino(e: Elemento, similitud: float) -> dict[str, Any]:
    dto: dict[str, Any] = {
        "id": e.id,
        "tipo": e.tipo,
        "ref": e.ref,
        "etiqueta": e.etiqueta,
        "similitud": round(similitud, 4),
        "clusterId": e.cluster,
        "instrumentoId": e.instrumento_id,
    }
    if e.tipo == "chunk":
        dto["texto"] = e.texto
        dto["seccion"] = e.detalle
    return dto


def _buscar(espacio: Espacio, tipo: str, ref: str) -> Elemento:
    grupos = {"kpi": espacio.kpis, "instrumento": espacio.instrumentos}
    candidatos = grupos.get(tipo) if tipo != "chunk" else chunks_completos(espacio)
    for e in candidatos or []:
        if e.ref == ref:
            return e
    raise PuntoNoEncontrado(f"No hay un {tipo} con id {ref} en el espacio vectorial.")


def vecinos(db: Session, tipo: str, ref: str, k: int = 8) -> dict[str, Any]:
    espacio = obtener_espacio(db)
    origen = _buscar(espacio, tipo, ref)
    todos_chunks = chunks_completos(espacio)

    if tipo == "instrumento":
        # Chunks del propio instrumento que mejor lo representan.
        propios = [c for c in todos_chunks if c.instrumento_id == origen.ref]
        chunks = _ranking(origen, propios, k)
    elif tipo == "kpi":
        # «Qué preguntas miden este KPI»: chunks de pregunta de cualquier instrumento.
        preguntas = [c for c in todos_chunks if c.detalle == "pregunta"] or todos_chunks
        chunks = _ranking(origen, preguntas, k)
    else:
        chunks = _ranking(origen, todos_chunks, k)

    return {
        "origen": {
            "id": origen.id,
            "tipo": origen.tipo,
            "ref": origen.ref,
            "etiqueta": origen.etiqueta,
            "clusterId": origen.cluster,
            "texto": origen.texto if origen.tipo == "chunk" else None,
            "seccion": origen.detalle if origen.tipo == "chunk" else None,
        },
        "kpis": [_vecino(e, s) for e, s in _ranking(origen, espacio.kpis, k)],
        "instrumentos": [_vecino(e, s) for e, s in _ranking(origen, espacio.instrumentos, k)],
        "chunks": [_vecino(e, s) for e, s in chunks],
        "fuenteChunks": {"nombre": espacio.fuente.nombre, "provisional": espacio.fuente.provisional},
    }
