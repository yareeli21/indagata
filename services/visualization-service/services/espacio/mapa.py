"""Mapa 2D del espacio de embeddings: KPIs, instrumentos y (opcional) chunks.

Pasos:
  1. Vectores: KPIs desde la colección `kpis` (o embebidos si faltan),
     instrumentos con `vectores_instrumento`, chunks con la fuente activa.
  2. PCA ajustado sobre KPIs + instrumentos (el conjunto «ancla»); chunks y, más
     adelante, consultas se proyectan con la MISMA transformación. Se calcula
     también una vista «alineada»: cada tipo se centra en su propio centroide
     antes del PCA, para quitar la brecha de modalidad (un KPI es una definición
     corta y un instrumento un texto largo, y eso separa los grupos aunque traten
     el mismo tema). Solo cambia el dibujo; el parecido se sigue midiendo con
     coseno sobre los vectores originales.
  3. Clusters semánticos de KPIs (k-means esférico sobre los vectores originales);
     cada instrumento hereda el cluster de su KPI más parecido (coseno).

El resultado se guarda en memoria y se recalcula solo cuando cambia la huella de
los datos (KPIs, instrumentos, colecciones), así el mapa escala con el acervo.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.models.kpi import KPI

from services import query_engine, vectores
from services.espacio import algebra
from services.espacio.fuente_chunks import FuenteChunks, fuente_activa
from services.espacio.vectores_instrumento import vectores_instrumentos

logger = logging.getLogger("visualization-service")

# Si PC1 + PC2 explican menos que esto, la UI advierte que el mapa simplifica mucho.
UMBRAL_VARIANZA_BAJA = 0.25
# Tope de chunks que se comparan al buscar vecinos (coseno exacto, en memoria).
LIMITE_CHUNKS_VECINOS = 20000


@dataclass
class Elemento:
    id: str  # único en el mapa: "kpi:5", "inst:12", "chunk:inst-12-3"
    tipo: str  # "kpi" | "instrumento" | "chunk"
    ref: str  # kpi_id, id_crudo o id del chunk
    etiqueta: str
    resumen: str
    detalle: str
    vector: np.ndarray
    instrumento_id: str | None = None
    origen_vector: str | None = None
    cluster: int | None = None
    x: float = 0.0
    y: float = 0.0
    # Texto completo (solo chunks), para el panel de detalle.
    texto: str = ""
    # Coordenadas en la vista alineada.
    xa: float = 0.0
    ya: float = 0.0


@dataclass
class Espacio:
    huella: str
    kpis: list[Elemento]
    instrumentos: list[Elemento]
    proyeccion: algebra.Proyeccion
    proyeccion_alineada: algebra.Proyeccion
    # Centroide de cada tipo («kpi», «instrumento», «chunk») para la vista alineada.
    medias: dict[str, np.ndarray]
    clusters: list[dict[str, Any]]
    fuente: FuenteChunks
    generado: datetime
    chunks: list[Elemento] = field(default_factory=list)
    limite_chunks: int = 0
    # Todos los chunks (sin muestreo) para buscar vecinos; se cargan al pedirlos.
    chunks_completos: list[Elemento] | None = None


_cache: dict[str, Espacio] = {}
_lock = threading.Lock()


def _primera_oracion(texto: str | None, maximo: int = 160) -> str:
    texto = re.sub(r"\s+", " ", (texto or "")).strip()
    if not texto:
        return ""
    corte = re.split(r"(?<=[.!?])\s", texto, maxsplit=1)[0]
    return corte if len(corte) <= maximo else corte[: maximo - 1].rstrip() + "…"


def _polaridad(texto: str | None) -> str:
    return (texto or "").split("(")[0].strip(" /") or ""


def _vectores_kpis(kpis: list[KPI]) -> dict[int, list[float]]:
    """Vector de cada KPI desde la colección `kpis`; los que falten se embeben."""
    salida: dict[int, list[float]] = {}
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_KPIS)
        if coleccion is not None:
            res = coleccion.get(ids=[str(k.kpi_id) for k in kpis], include=["embeddings"])
            embs = res.get("embeddings")
            for pid, emb in zip(res.get("ids") or [], embs if embs is not None else []):
                vector = vectores.a_lista(emb)
                if vector is not None and str(pid).isdigit():
                    salida[int(pid)] = vector
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudieron leer los vectores de KPIs: %s", exc)
    faltantes = [k for k in kpis if k.kpi_id not in salida]
    if faltantes:
        nuevos = vectores.embed_texts([k.texto_contexto_rag_vectorial or k.nombre for k in faltantes])
        salida.update({k.kpi_id: v for k, v in zip(faltantes, nuevos)})
    return salida


def _huella(kpis: list[KPI], fichas: list[query_engine.Ficha]) -> str:
    partes = [f"k{k.kpi_id}:{k.nombre}:{len(k.texto_contexto_rag_vectorial or '')}" for k in kpis]
    partes += [f"i{f.id}:{f.estado_backend}:{f.titulo}:{f.reactivos}:{bool(f.data)}" for f in fichas]
    for nombre in (
        settings.CHROMA_COLLECTION_KPIS,
        settings.CHROMA_COLLECTION_SUMMARY,
        settings.CHROMA_COLLECTION_INSTRUMENTOS,
    ):
        try:
            coleccion = vectores.coleccion_existente(nombre)
            partes.append(f"{nombre}:{coleccion.count() if coleccion is not None else 0}")
        except Exception:  # noqa: BLE001
            partes.append(f"{nombre}:?")
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def _construir(db: Session, huella: str, kpis: list[KPI], fichas: list[query_engine.Ficha]) -> Espacio:
    vec_kpis = _vectores_kpis(kpis)
    elementos_kpi = [
        Elemento(
            id=f"kpi:{k.kpi_id}",
            tipo="kpi",
            ref=str(k.kpi_id),
            etiqueta=k.nombre,
            resumen=_primera_oracion(k.descripcion_ampliada_educativa or k.texto_contexto_rag_vectorial),
            detalle=_polaridad(k.polaridad_rendimiento),
            vector=np.asarray(vec_kpis[k.kpi_id], dtype=float),
        )
        for k in kpis
        if k.kpi_id in vec_kpis
    ]

    por_id = {f.id: f for f in fichas}
    elementos_inst = []
    for fid, (vector, origen) in vectores_instrumentos(fichas).items():
        f = por_id[fid]
        elementos_inst.append(
            Elemento(
                id=f"inst:{f.id}",
                tipo="instrumento",
                ref=f.id,
                etiqueta=f.titulo,
                resumen=_primera_oracion(f.descripcion) or f"{f.reactivos} reactivos",
                detalle=f"{f.tipo} · {f.nivel} · {f.anio}",
                vector=np.asarray(vector, dtype=float),
                instrumento_id=f.id,
                origen_vector=origen,
            )
        )
    elementos_inst.sort(key=lambda e: int(e.ref) if e.ref.isdigit() else 0)

    ancla = elementos_kpi + elementos_inst
    dimension = len(ancla[0].vector) if ancla else 0
    matriz = np.vstack([e.vector for e in ancla]) if ancla else np.zeros((0, dimension))
    proyeccion = algebra.ajustar_pca(matriz) if len(ancla) else algebra.ajustar_pca(np.zeros((1, 2)))
    for e, (x, y) in zip(ancla, proyeccion.proyectar(matriz)):
        e.x, e.y = float(x), float(y)

    medias = {
        tipo: np.vstack([e.vector for e in grupo]).mean(axis=0)
        for tipo, grupo in (("kpi", elementos_kpi), ("instrumento", elementos_inst))
        if grupo
    }
    alineada = np.vstack([e.vector - medias[e.tipo] for e in ancla]) if ancla else matriz
    proyeccion_alineada = algebra.ajustar_pca(alineada) if len(ancla) else proyeccion
    for e, (x, y) in zip(ancla, proyeccion_alineada.proyectar(alineada)):
        e.xa, e.ya = float(x), float(y)

    clusters: list[dict[str, Any]] = []
    if elementos_kpi:
        mat_kpi = np.vstack([e.vector for e in elementos_kpi])
        etiquetas, centroides = algebra.kmeans_esferico(mat_kpi, algebra.k_sugerido(len(elementos_kpi)))
        for e, c in zip(elementos_kpi, etiquetas):
            e.cluster = int(c)
        normalizados = algebra.normalizar_filas(mat_kpi)
        for j, centroide in enumerate(centroides):
            miembros = [i for i, c in enumerate(etiquetas) if c == j]
            if not miembros:
                continue
            orden = sorted(miembros, key=lambda i: -float(normalizados[i] @ centroide))
            clusters.append(
                {
                    "id": j,
                    "etiqueta": elementos_kpi[orden[0]].etiqueta,
                    "representativos": [elementos_kpi[i].etiqueta for i in orden[:3]],
                    "tamano": len(miembros),
                }
            )
        for e in elementos_inst:
            sims = algebra.similitudes(e.vector, mat_kpi)
            e.cluster = elementos_kpi[int(np.argmax(sims))].cluster

    return Espacio(
        huella=huella,
        kpis=elementos_kpi,
        instrumentos=elementos_inst,
        proyeccion=proyeccion,
        proyeccion_alineada=proyeccion_alineada,
        medias=medias,
        clusters=clusters,
        fuente=fuente_activa(),
        generado=datetime.now(timezone.utc),
    )


def _elementos_chunk(espacio: Espacio, limite: int) -> list[Elemento]:
    chunks = espacio.fuente.todos(limite)
    instrumentos = {e.ref: e for e in espacio.instrumentos}
    elementos: list[Elemento] = []
    for c in chunks:
        padre = instrumentos.get(c.instrumento_id)
        titulo = padre.etiqueta if padre else f"Instrumento {c.instrumento_id}"
        elementos.append(
            Elemento(
                id=f"chunk:{c.id}",
                tipo="chunk",
                ref=c.id,
                etiqueta=f"{titulo} — {c.seccion or 'fragmento'}",
                resumen=_primera_oracion(c.texto, 140),
                texto=c.texto,
                detalle=c.seccion,
                vector=np.asarray(c.embedding, dtype=float),
                instrumento_id=c.instrumento_id,
                cluster=padre.cluster if padre else None,
            )
        )
    return elementos


def _agregar_chunks(espacio: Espacio, limite: int) -> None:
    """Proyecta los chunks con el PCA ya ajustado (no lo reajusta)."""
    elementos = _elementos_chunk(espacio, limite)
    if elementos:
        matriz = np.vstack([e.vector for e in elementos])
        for e, (x, y) in zip(elementos, espacio.proyeccion.proyectar(matriz)):
            e.x, e.y = float(x), float(y)
        espacio.medias["chunk"] = matriz.mean(axis=0)
        alineados = espacio.proyeccion_alineada.proyectar(matriz - espacio.medias["chunk"])
        for e, (x, y) in zip(elementos, alineados):
            e.xa, e.ya = float(x), float(y)
    espacio.chunks = elementos
    espacio.limite_chunks = limite


def chunks_completos(espacio: Espacio) -> list[Elemento]:
    """Todos los chunks de la fuente (para vecinos), cargados una vez por espacio."""
    if espacio.chunks_completos is None:
        with _lock:
            if espacio.chunks_completos is None:
                espacio.chunks_completos = _elementos_chunk(espacio, LIMITE_CHUNKS_VECINOS)
    return espacio.chunks_completos


def obtener_espacio(db: Session, *, chunks: bool = False, limite_chunks: int = 3000) -> Espacio:
    """Espacio vigente (desde caché si los datos no cambiaron)."""
    kpis = db.query(KPI).order_by(KPI.kpi_id).all()
    fichas = query_engine.cargar_fichas(db)
    huella = _huella(kpis, fichas)
    with _lock:
        espacio = _cache.get("vigente")
    if espacio is None or espacio.huella != huella:
        espacio = _construir(db, huella, kpis, fichas)
        with _lock:
            _cache["vigente"] = espacio
    if chunks and (not espacio.chunks or espacio.limite_chunks != limite_chunks):
        with _lock:
            _agregar_chunks(espacio, limite_chunks)
    return espacio


def precalentar() -> None:
    """Construye el espacio al arrancar el servicio (carga el modelo y llena la caché)."""
    from shared.db.session import SessionLocal

    try:
        with SessionLocal() as db:
            espacio = obtener_espacio(db)
        logger.info(
            "Espacio vectorial precalculado: %s KPIs, %s instrumentos.",
            len(espacio.kpis),
            len(espacio.instrumentos),
        )
    except Exception as exc:  # noqa: BLE001 — se calculará en la primera petición
        logger.warning("No se pudo precalcular el espacio vectorial: %s", exc)


def _punto(e: Elemento, alinear: bool) -> dict[str, Any]:
    return {
        "id": e.id,
        "tipo": e.tipo,
        "ref": e.ref,
        "etiqueta": e.etiqueta,
        "resumen": e.resumen,
        "detalle": e.detalle,
        "x": round(e.xa if alinear else e.x, 4),
        "y": round(e.ya if alinear else e.y, 4),
        "clusterId": e.cluster,
        "instrumentoId": e.instrumento_id,
        "origenVector": e.origen_vector,
    }


def mapa(
    db: Session, *, chunks: bool = False, limite_chunks: int = 3000, alinear: bool = False
) -> dict[str, Any]:
    """DTO del mapa para el frontend (`alinear`: vista con los grupos centrados)."""
    espacio = obtener_espacio(db, chunks=chunks, limite_chunks=limite_chunks)
    proyeccion = espacio.proyeccion_alineada if alinear else espacio.proyeccion
    elementos = espacio.kpis + espacio.instrumentos + (espacio.chunks if chunks else [])
    dimension = int(espacio.proyeccion.media.shape[0]) if espacio.kpis or espacio.instrumentos else 0
    return {
        "modelo": settings.EMBEDDING_MODEL,
        "dimension": dimension,
        "pca": {
            "varianza": [round(v, 4) for v in proyeccion.varianza],
            "varianzaTotal": round(proyeccion.varianza_total, 4),
            "varianzaBaja": proyeccion.varianza_total < UMBRAL_VARIANZA_BAJA,
        },
        "clusters": espacio.clusters,
        "fuenteChunks": {"nombre": espacio.fuente.nombre, "provisional": espacio.fuente.provisional},
        "conteos": {
            "kpis": len(espacio.kpis),
            "instrumentos": len(espacio.instrumentos),
            "chunks": len(espacio.chunks) if chunks else 0,
        },
        "puntos": [_punto(e, alinear) for e in elementos],
        "generadoEn": espacio.generado.isoformat(),
        "alineado": alinear,
    }
