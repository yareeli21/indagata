"""Vector de cada instrumento para el espacio vectorial.

Un instrumento se representa por el embedding de sus METADATOS + PREGUNTAS (el
«summary» que usa el analysis-service para asociarlo con KPIs):
  1. si existe en la colección `summary_instrument` (id = id_instrumento), se usa;
  2. si no, se arma un texto equivalente (Dublin Core + metadatos del tipo +
     preguntas del JSON estandarizado) y se embebe con el mismo modelo. El
     resultado se guarda en memoria (no se escribe en Chroma).
"""
from __future__ import annotations

import hashlib
import threading
from typing import Any

from shared.db.core.config import settings

from services import vectores
from services.query_engine import Ficha, preguntas_de

# id del instrumento → (huella del texto, vector)
_cache: dict[str, tuple[str, list[float]]] = {}
_lock = threading.Lock()


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return ", ".join(t for t in (_texto(v) for v in valor) if t)
    if isinstance(valor, dict):
        return ""
    return str(valor).strip()


def texto_summary(ficha: Ficha) -> str:
    """Texto equivalente al summary del analysis-service (sin respuestas)."""
    data = ficha.data or {}
    metadata = data.get("metadata") or {}
    partes = ["## Metadatos del instrumento", f"Título: {ficha.titulo}", f"Tipo: {ficha.tipo}"]
    for clave, valor in (metadata.get("dublin_core") or {}).items():
        valor = _texto(valor)
        if valor and clave != "dc:title":
            partes.append(f"{clave.removeprefix('dc:').capitalize()}: {valor}")
    for clave, valor in (metadata.get("survey_specific") or {}).items():
        valor = _texto(valor)
        if valor:
            partes.append(f"{clave.replace('_', ' ').capitalize()}: {valor}")
    if ficha.descripcion:
        partes.append(f"Descripción: {ficha.descripcion}")
    preguntas = preguntas_de(data)
    if preguntas:
        partes += ["", "## Instrumento original"]
        partes += [f"{p['id']}. {p['texto']}".strip(". ") for p in preguntas]
    return "\n".join(partes)


def _desde_summary(fichas: list[Ficha]) -> dict[str, list[float]]:
    """Vectores ya calculados por el analysis-service (si la colección existe)."""
    coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_SUMMARY)
    por_procesado = {str(f.id_instrumento): f.id for f in fichas if f.id_instrumento is not None}
    if coleccion is None or not por_procesado:
        return {}
    res = coleccion.get(ids=list(por_procesado), include=["embeddings"])
    embs = res.get("embeddings")
    salida: dict[str, list[float]] = {}
    for pid, emb in zip(res.get("ids") or [], embs if embs is not None else []):
        vector = vectores.a_lista(emb)
        if vector is not None and str(pid) in por_procesado:
            salida[por_procesado[str(pid)]] = vector
    return salida


def vectores_instrumentos(fichas: list[Ficha]) -> dict[str, tuple[list[float], str]]:
    """{id_crudo: (vector, origen)} con origen "summary" o "calculado".

    Solo se incluyen instrumentos con contenido (JSON estandarizado).
    """
    con_datos = [f for f in fichas if f.data]
    try:
        resumidos = _desde_summary(con_datos)
    except Exception:  # noqa: BLE001 — sin Chroma se calcula todo
        resumidos = {}
    salida = {fid: (vec, "summary") for fid, vec in resumidos.items()}

    pendientes: list[tuple[Ficha, str, str]] = []
    for ficha in con_datos:
        if ficha.id in salida:
            continue
        texto = texto_summary(ficha)
        huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        with _lock:
            guardado = _cache.get(ficha.id)
        if guardado and guardado[0] == huella:
            salida[ficha.id] = (guardado[1], "calculado")
        else:
            pendientes.append((ficha, texto, huella))

    if pendientes:
        nuevos = vectores.embed_texts([t for _, t, _ in pendientes])
        with _lock:
            for (ficha, _, huella), vector in zip(pendientes, nuevos):
                _cache[ficha.id] = (huella, vector)
                salida[ficha.id] = (vector, "calculado")
    return salida
