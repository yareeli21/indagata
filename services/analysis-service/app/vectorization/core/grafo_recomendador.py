"""Motor de score híbrido del Grafo de Recomendación de Instrumentos.

Combina dos señales para recomendar instrumentos complementarios a un conjunto
activo `A`:

  score(c) = w_sem * sim_semantica(c, A) + w_kpi * solape_kpi(c, A)

- `sim_semantica(c, A)`: máxima similitud coseno entre el vector de `c` y los
  vectores de `A` (colección `summary_instrument` de Chroma). Reutiliza
  `chroma_client.query` + `kpi_search._distance_to_score`; NO reimplementa coseno
  ni recalcula embeddings.
- `solape_kpi(c, A)`: coeficiente de Jaccard entre los KPIs de `c` y la unión de
  KPIs de `A` (desde `kpi_inferido` unido a `kpi.nombre`).

Degradación con gracia (RNF-4): si Chroma falla, `w_sem` se fuerza a 0,
`sim_semantica = 0` para todos, se marca `degradado_semantico=True` y se registra
un `logger.warning` (respuesta no fatal, solo-KPI).

El cliente Chroma es inyectable (`client=None`) para pruebas, igual que el seam ya
existente en `chroma_client`, `kpi_search` y `espacio`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.vectorization.core import chroma_client
from app.vectorization.core.kpi_search import _distance_to_score
from shared.db.core.config import settings
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.metadatos_dc import MetadatosDC
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

logger = logging.getLogger(__name__)

# Umbral sobre el score CRUDO de cada señal (no ponderado) para decidir la razón
# de recomendación. Constante de módulo nombrada y ajustable (design §2.3).
UMBRAL_ALTO = 0.5

# Mapeo canónico de `raw_data.tipo_instrumento` al literal del frontend. Réplica
# local de `instrument-service/app/services/map_instrumento.py::mapear_tipo`
# (no importable desde este servicio): mismo diccionario y misma regla.
_TIPO_MAP = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_TIPO_DEFAULT = "Encuesta"


@dataclass
class Recomendacion:
    """Un instrumento candidato recomendado, con sus scores y razón."""

    id: str
    idCrudo: str
    titulo: str
    tipo: str
    autorId: str
    autorNombre: str
    kpis: list[str]
    score: float
    score_semantico: float
    score_kpi: float
    razon: str
    kpis_compartidos: list[str] = field(default_factory=list)


@dataclass
class _Instrumento:
    """Datos de un instrumento del acervo (nodo del grafo)."""

    id_instrumento: int
    id_crudo: int
    titulo: str
    tipo_raw: str | None
    id_owner: int | None
    autor_nombre: str
    # Mapa kpi_id → nombre (preserva el emparejamiento id↔nombre, orden de inserción).
    kpis: dict[int, str] = field(default_factory=dict)

    @property
    def kpi_ids(self) -> set[int]:
        return set(self.kpis)

    @property
    def kpi_nombres(self) -> list[str]:
        return list(self.kpis.values())


def _mapear_tipo(tipo_raw: str | None) -> str:
    """Mapea `raw_data.tipo_instrumento` al literal del frontend.

    Desconocido → "Encuesta" + logger.warning (idéntico a `map_instrumento`).
    """
    clave = (tipo_raw or "").strip().lower()
    tipo = _TIPO_MAP.get(clave)
    if tipo is None:
        logger.warning("tipo_instrumento desconocido %r; se mapea a %r.", tipo_raw, _TIPO_DEFAULT)
        return _TIPO_DEFAULT
    return tipo


def _jaccard(set_a: set[int], set_b: set[int]) -> float:
    """Coeficiente de Jaccard entre dos conjuntos. Unión vacía → 0.0."""
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _clamp(valor: float, bajo: float, alto: float) -> float:
    """Acota `valor` al rango [bajo, alto]."""
    if valor < bajo:
        return bajo
    if valor > alto:
        return alto
    return valor


def _etiquetar_razon(
    score_semantico: float, score_kpi: float, kpis_compartidos: list[str]
) -> str:
    """Decide la razón de recomendación (design §2.3, sobre scores crudos [0,1]).

    Regla exacta y determinista; `UMBRAL_ALTO` es constante de módulo (no literal).
    """
    alto_sem = score_semantico >= UMBRAL_ALTO
    alto_kpi = score_kpi >= UMBRAL_ALTO

    if alto_sem and alto_kpi:
        return "Alta afinidad (contenido + KPIs)"
    if kpis_compartidos and score_kpi >= score_semantico:
        return "KPIs compartidos: " + ", ".join(kpis_compartidos)
    if score_semantico > score_kpi:
        return "Contenido similar"
    if kpis_compartidos:
        return "KPIs compartidos: " + ", ".join(kpis_compartidos)
    return "Contenido similar"


def cargar_acervo(db: Session) -> list[_Instrumento]:
    """Carga todos los instrumentos del acervo con sus KPIs (join ORM).

    Un instrumento aparece aunque no tenga KPIs (outer join a kpi_inferido/kpi).
    """
    filas = (
        db.query(
            InstrumentoProcesado.id_instrumento,
            RawData.id_crudo,
            RawData.tipo_instrumento,
            RawData.id_owner,
            RawData.nombre_archivo,
            MetadatosDC.dc_title,
            Usuario.nombre,
            KPIInferido.kpi_id,
            KPI.nombre,
        )
        .select_from(InstrumentoProcesado)
        .join(RawData, RawData.id_crudo == InstrumentoProcesado.id_crudo)
        .outerjoin(MetadatosDC, MetadatosDC.id_crudo == RawData.id_crudo)
        .outerjoin(Usuario, Usuario.usuario_id == RawData.id_owner)
        .outerjoin(KPIInferido, KPIInferido.id_procesado == InstrumentoProcesado.id_instrumento)
        .outerjoin(KPI, KPI.kpi_id == KPIInferido.kpi_id)
        .all()
    )

    por_id: dict[int, _Instrumento] = {}
    for (
        id_instrumento,
        id_crudo,
        tipo_instrumento,
        id_owner,
        nombre_archivo,
        dc_title,
        autor_nombre,
        kpi_id,
        kpi_nombre,
    ) in filas:
        inst = por_id.get(id_instrumento)
        if inst is None:
            inst = _Instrumento(
                id_instrumento=int(id_instrumento),
                id_crudo=int(id_crudo),
                titulo=str(dc_title or nombre_archivo or ""),
                tipo_raw=tipo_instrumento,
                id_owner=int(id_owner) if id_owner is not None else None,
                autor_nombre=str(autor_nombre or ""),
            )
            por_id[id_instrumento] = inst
        if kpi_id is not None:
            inst.kpis[int(kpi_id)] = str(kpi_nombre or "")

    return list(por_id.values())


def _sim_semantica_por_candidato(
    activos: list[_Instrumento],
    candidatos: list[_Instrumento],
    *,
    total_acervo: int,
    client=None,
) -> tuple[dict[int, float], bool]:
    """Calcula sim_semantica máxima por candidato leyendo vectores de Chroma.

    Para cada vector de A hace UNA query (top_k = len(acervo)); por candidato toma
    el máximo `_distance_to_score`. Candidato ausente de todas las queries → 0.0.

    Devuelve (mapa id_instrumento→sim, degradado_semantico).
    """
    sim: dict[int, float] = {c.id_instrumento: 0.0 for c in candidatos}
    try:
        coleccion = chroma_client.get_or_create_collection(
            settings.CHROMA_COLLECTION_SUMMARY, client=client
        )
        top_k = max(1, total_acervo)
        for activo in activos:
            punto = chroma_client.get_point(coleccion, str(activo.id_instrumento))
            if punto is None or punto.get("embedding") is None:
                continue
            res = chroma_client.query(coleccion, punto["embedding"], top_k=top_k)
            metadatas = (res.get("metadatas") or [[]])[0]
            distances = (res.get("distances") or [[]])[0]
            for meta, dist in zip(metadatas, distances):
                meta = meta or {}
                id_cand = meta.get("id_instrumento")
                if id_cand is None:
                    continue
                id_cand = int(id_cand)
                if id_cand not in sim:
                    continue
                score = _distance_to_score(dist)
                if score > sim[id_cand]:
                    sim[id_cand] = score
    except Exception:  # noqa: BLE001 -- degradación con gracia (RNF-4)
        logger.warning(
            "Chroma no disponible al calcular sim_semantica; se degrada a solo-KPI.",
            exc_info=True,
        )
        return {c.id_instrumento: 0.0 for c in candidatos}, True

    return sim, False


def recomendar(
    db: Session,
    instrumento_ids: list[int],
    *,
    autor_id: int | None = None,
    w_sem: float = 0.6,
    w_kpi: float = 0.4,
    top_n: int = 10,
    min_score: float = 0.15,
    excluir_propios: bool = False,
    client=None,
) -> tuple[list[Recomendacion], dict, bool]:
    """Calcula las recomendaciones para el set activo `instrumento_ids`.

    Args:
        db:              sesión de BD (ORM).
        instrumento_ids: ids del set activo (espacio id_instrumento).
        autor_id:        autor efectivo para `excluir_propios` (int o None).
        w_sem, w_kpi:    pesos de las señales (deben sumar 1.0; validado en router).
        top_n:           corte superior de resultados (clamp 1..100).
        min_score:       umbral mínimo de score combinado.
        excluir_propios: si True, excluye candidatos cuyo id_owner == autor_id.
        client:          cliente Chroma inyectable (pruebas).

    Returns:
        (recomendaciones ordenadas por score desc, parametros, degradado_semantico).
    """
    top_n = int(_clamp(float(top_n), 1, 100))
    activos_ids = {int(i) for i in instrumento_ids}

    acervo = cargar_acervo(db)
    activos = [i for i in acervo if i.id_instrumento in activos_ids]

    # Unión de KPIs (id→nombre) del set activo.
    kpis_union: dict[int, str] = {}
    for a in activos:
        kpis_union.update(a.kpis)
    union_ids = set(kpis_union)

    # Candidatos = acervo menos los ya activos; opcionalmente menos los del autor.
    candidatos: list[_Instrumento] = []
    for inst in acervo:
        if inst.id_instrumento in activos_ids:
            continue
        if excluir_propios and autor_id is not None and inst.id_owner == autor_id:
            continue
        candidatos.append(inst)

    sim_map, degradado = _sim_semantica_por_candidato(
        activos, candidatos, total_acervo=len(acervo), client=client
    )

    w_sem_eff = 0.0 if degradado else w_sem
    w_kpi_eff = w_kpi

    recomendaciones: list[Recomendacion] = []
    for cand in candidatos:
        score_semantico = sim_map.get(cand.id_instrumento, 0.0)
        score_kpi = _jaccard(cand.kpi_ids, union_ids)

        compartidos_ids = cand.kpi_ids & union_ids
        # Nombre por id, resuelto desde el candidato o la unión del set activo.
        kpis_compartidos = [
            cand.kpis.get(kid) or kpis_union.get(kid, "")
            for kid in cand.kpis
            if kid in compartidos_ids
        ]
        kpis_compartidos = [n for n in kpis_compartidos if n]

        score = w_sem_eff * score_semantico + w_kpi_eff * score_kpi
        if score < min_score:
            continue

        razon = _etiquetar_razon(score_semantico, score_kpi, kpis_compartidos)
        recomendaciones.append(
            Recomendacion(
                id=str(cand.id_instrumento),
                idCrudo=str(cand.id_crudo),
                titulo=cand.titulo,
                tipo=_mapear_tipo(cand.tipo_raw),
                autorId=str(cand.id_owner) if cand.id_owner is not None else "",
                autorNombre=cand.autor_nombre,
                kpis=cand.kpi_nombres,
                score=round(score, 4),
                score_semantico=round(score_semantico, 4),
                score_kpi=round(score_kpi, 4),
                razon=razon,
                kpis_compartidos=kpis_compartidos,
            )
        )

    recomendaciones.sort(key=lambda r: r.score, reverse=True)
    recomendaciones = recomendaciones[:top_n]

    parametros = {
        "w_sem": w_sem_eff,
        "w_kpi": w_kpi_eff,
        "top_n": top_n,
        "min_score": min_score,
    }
    return recomendaciones, parametros, degradado
