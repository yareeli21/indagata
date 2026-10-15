"""Búsqueda semántica en vivo sobre el espacio vectorial.

La frase se embebe con el MISMO modelo que KPIs, instrumentos y chunks y se
proyecta con el MISMO PCA del mapa; sus vecinos se ordenan por coseno contra los
vectores originales (como hace el RAG al buscar fuentes).

Para la vista alineada la consulta debe centrarse como un grupo más. Una sola
frase no tiene centroide propio, así que se centra con el centroide del grupo al
que más se parece (KPIs, instrumentos o chunks): su «estilo» de texto.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from services import vectores
from services.espacio import algebra
from services.espacio.mapa import Elemento, chunks_completos, obtener_espacio
from services.espacio.vecinos import _ranking, _vecino


def buscar(db: Session, texto: str, k: int = 6) -> dict[str, Any]:
    espacio = obtener_espacio(db)
    vector = np.asarray(vectores.embed_text(texto), dtype=float)
    consulta = Elemento(
        id="consulta", tipo="consulta", ref="", etiqueta=texto, resumen="", detalle="", vector=vector
    )
    todos_chunks = chunks_completos(espacio)

    x, y = espacio.proyeccion.proyectar(vector)[0]

    medias = dict(espacio.medias)
    if todos_chunks and "chunk" not in medias:
        medias["chunk"] = np.vstack([c.vector for c in todos_chunks]).mean(axis=0)
    grupo = None
    xa, ya = x, y
    if medias:
        nombres = list(medias)
        sims = algebra.similitudes(vector, np.vstack([medias[n] for n in nombres]))
        grupo = nombres[int(np.argmax(sims))]
        xa, ya = espacio.proyeccion_alineada.proyectar(vector - medias[grupo])[0]

    return {
        "texto": texto,
        "posicion": {"x": round(float(x), 4), "y": round(float(y), 4)},
        "posicionAlineada": {"x": round(float(xa), 4), "y": round(float(ya), 4)},
        "grupoReferencia": grupo,
        "kpis": [_vecino(e, s) for e, s in _ranking(consulta, espacio.kpis, k)],
        "instrumentos": [_vecino(e, s) for e, s in _ranking(consulta, espacio.instrumentos, k)],
        "chunks": [_vecino(e, s) for e, s in _ranking(consulta, todos_chunks, k)],
        "fuenteChunks": {"nombre": espacio.fuente.nombre, "provisional": espacio.fuente.provisional},
    }
