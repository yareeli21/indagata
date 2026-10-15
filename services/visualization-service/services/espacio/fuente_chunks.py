"""Acceso intercambiable a los chunks del RAG para el espacio vectorial.

Los chunks definitivos aún no existen: por ahora se leen los de la colección
`instrumentos` (los genera el storage-service cuando visualization-service pide la
ingesta con POST /rag/index) y se marcan como PROVISIONALES. Para cambiar de
fuente basta con añadir otra implementación de `FuenteChunks` y registrarla en
`_FUENTES`; la API y la interfaz no cambian (solo leen `nombre` y `provisional`).

La fuente activa se elige con la variable de entorno ESPACIO_FUENTE_CHUNKS.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from shared.db.core.config import settings

from services import vectores


@dataclass(frozen=True)
class Chunk:
    id: str
    instrumento_id: str
    texto: str
    seccion: str
    embedding: list[float]


class FuenteChunks(Protocol):
    """Contrato de una fuente de chunks."""

    nombre: str
    provisional: bool

    def todos(self, limite: int) -> list[Chunk]:
        """Hasta `limite` chunks (muestreo estable si hay más)."""
        ...

    def por_instrumento(self, instrumento_id: str) -> list[Chunk]:
        """Todos los chunks de un instrumento."""
        ...


def _a_chunks(datos: dict) -> list[Chunk]:
    ids = datos.get("ids") or []
    embs = datos.get("embeddings")
    embs = embs if embs is not None else [None] * len(ids)
    metas = datos.get("metadatas") or [{}] * len(ids)
    docs = datos.get("documents") or [""] * len(ids)
    salida: list[Chunk] = []
    for pid, emb, meta, doc in zip(ids, embs, metas, docs):
        vector = vectores.a_lista(emb)
        if vector is None:
            continue
        meta = meta or {}
        salida.append(
            Chunk(
                id=str(pid),
                instrumento_id=str(meta.get("instrumentoId") or ""),
                texto=str(doc or ""),
                seccion=str(meta.get("seccion") or ""),
                embedding=vector,
            )
        )
    return salida


class ChunksRagInstrumentos:
    """Chunks de la colección del RAG (`encabezado`, `pregunta`, `contenido`)."""

    nombre = "rag_instrumentos"
    provisional = True

    def _coleccion(self):
        return vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)

    def todos(self, limite: int) -> list[Chunk]:
        coleccion = self._coleccion()
        if coleccion is None or limite <= 0:
            return []
        chunks = sorted(
            _a_chunks(coleccion.get(include=["embeddings", "metadatas", "documents"])),
            key=lambda c: c.id,
        )
        if len(chunks) <= limite:
            return chunks
        paso = len(chunks) / limite
        return [chunks[int(i * paso)] for i in range(limite)]

    def por_instrumento(self, instrumento_id: str) -> list[Chunk]:
        coleccion = self._coleccion()
        if coleccion is None:
            return []
        return _a_chunks(
            coleccion.get(
                where={"instrumentoId": str(instrumento_id)},
                include=["embeddings", "metadatas", "documents"],
            )
        )


_FUENTES: dict[str, type] = {ChunksRagInstrumentos.nombre: ChunksRagInstrumentos}


def fuente_activa() -> FuenteChunks:
    nombre = os.getenv("ESPACIO_FUENTE_CHUNKS", ChunksRagInstrumentos.nombre)
    return _FUENTES.get(nombre, ChunksRagInstrumentos)()
