"""Router — GRAFO DE RECOMENDACIÓN de instrumentos.

Expone la capa de inteligencia colaborativa sobre el acervo:

  GET  /grafo/acervo         → grafo base (todos los instrumentos como nodos +
                               aristas de KPI compartido).
  POST /grafo/recomendar     → recomendaciones en tiempo real para un set activo
                               (score híbrido semántico + Jaccard de KPIs).
  POST /grafo/investigacion  → persiste el snapshot del grafo y traduce los ids
                               (id_instrumento → id_crudo) para que el frontend
                               dispare /rag/index.

El frontend lo llama directo vía ANALYSIS_URL (el gateway no proxea /grafo/*),
igual que el catálogo de KPIs y el espacio vectorial. El grafo opera en el espacio
`id_instrumento`; /rag/index opera en `id_crudo`, por eso cada nodo expone ambos.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import SQLAlchemyError

from app.vectorization.core import grafo_recomendador
from app.vectorization.dependencies import DBSession, UsuarioActual
from shared.models.grafo_investigacion import GrafoInvestigacion
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grafo", tags=["grafo-recomendacion"])

# Cota de tamaño del snapshot serializado (design §3.2): 1 MB.
_MAX_SNAPSHOT_BYTES = 1_048_576


# ── Schemas ───────────────────────────────────────────────────────────────────


class RecomendarRequest(BaseModel):
    instrumentoIds: list[str] = Field(min_length=1)
    autorId: str | None = None
    w_sem: float = 0.6
    w_kpi: float = 0.4
    top_n: int = 10
    min_score: float = 0.15
    excluir_propios: bool = False

    @field_validator("min_score")
    @classmethod
    def _min_score_en_rango(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("min_score debe estar entre 0 y 1.")
        return v

    @model_validator(mode="after")
    def _pesos_validos(self) -> "RecomendarRequest":
        if not 0.0 <= self.w_sem <= 1.0 or not 0.0 <= self.w_kpi <= 1.0:
            raise ValueError("Los pesos w_sem y w_kpi deben estar entre 0 y 1.")
        if abs((self.w_sem + self.w_kpi) - 1.0) > 1e-6:
            raise ValueError("Los pesos w_sem y w_kpi deben sumar 1.0.")
        return self


class InvestigacionRequest(BaseModel):
    investigacionId: str = Field(min_length=1)
    instrumentoIds: list[str] = Field(min_length=1)
    grafo_snapshot: dict

    @field_validator("investigacionId")
    @classmethod
    def _investigacion_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El investigacionId no puede estar vacío.")
        return v

    @field_validator("grafo_snapshot")
    @classmethod
    def _snapshot_acotado(cls, v: dict) -> dict:
        try:
            tamano = len(json.dumps(v).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ValueError("El grafo_snapshot no es serializable a JSON.") from exc
        if tamano > _MAX_SNAPSHOT_BYTES:
            raise ValueError(
                "El grafo_snapshot excede el tamaño máximo permitido (1 MB)."
            )
        return v


# ── Helpers ─────────────────────────────────────────────────────────────────


def _a_int(valor: str) -> int | None:
    """Convierte un id string a int; None si no es convertible."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _autor_efectivo(autor_id: str | None, usuario_id: int) -> int:
    """Resuelve el autor efectivo en espacio int. autorId no convertible → 422."""
    if autor_id in (None, ""):
        return usuario_id
    convertido = _a_int(autor_id)  # type: ignore[arg-type]
    if convertido is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El autorId debe ser un identificador numérico.",
        )
    return convertido


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/acervo",
    status_code=status.HTTP_200_OK,
    summary="Grafo base del acervo (nodos + aristas de KPI compartido)",
    description=(
        "Devuelve todos los instrumentos del acervo como nodos (con sus KPIs, tipo, "
        "autor y si son propios del usuario) y las aristas de KPI compartido entre "
        "pares de instrumentos. Cada nodo expone `id` (= id_instrumento) e `idCrudo` "
        "(= id_crudo) por los dos espacios de identificadores."
    ),
)
def acervo(usuario_actual: UsuarioActual, db: DBSession) -> dict:
    try:
        instrumentos = grafo_recomendador.cargar_acervo(db)
    except SQLAlchemyError:
        logger.exception("Error al leer el acervo para el grafo de recomendación.")
        raise

    nodos = [
        {
            "id": str(inst.id_instrumento),
            "idCrudo": str(inst.id_crudo),
            "titulo": inst.titulo,
            "tipo": grafo_recomendador._mapear_tipo(inst.tipo_raw),
            "autorId": str(inst.id_owner) if inst.id_owner is not None else "",
            "autorNombre": inst.autor_nombre,
            "kpis": inst.kpi_nombres,
            "esPropio": inst.id_owner == usuario_actual.usuario_id,
        }
        for inst in instrumentos
    ]

    aristas = _construir_aristas(instrumentos)
    return {"nodos": nodos, "aristas": aristas}


def _construir_aristas(instrumentos: list) -> list[dict]:
    """Aristas de KPI compartido. Agrupa por kpi_id para evitar O(n²) denso."""
    # kpi_id → lista de instrumentos que lo tienen.
    por_kpi: dict[int, list] = {}
    for inst in instrumentos:
        for kpi_id in inst.kpi_ids:
            por_kpi.setdefault(kpi_id, []).append(inst)

    # (id_a, id_b) ordenado → {kpi_ids compartidos}.
    pares: dict[tuple[int, int], set[int]] = {}
    for kpi_id, insts in por_kpi.items():
        if len(insts) < 2:
            continue
        for i in range(len(insts)):
            for j in range(i + 1, len(insts)):
                a, b = insts[i], insts[j]
                clave = tuple(sorted((a.id_instrumento, b.id_instrumento)))
                pares.setdefault(clave, set()).add(kpi_id)

    nombre_por_id: dict[int, str] = {}
    for inst in instrumentos:
        nombre_por_id.update(inst.kpis)

    aristas: list[dict] = []
    for (origen, destino), kpi_ids in pares.items():
        aristas.append(
            {
                "origen": str(origen),
                "destino": str(destino),
                "tipo": "kpi_compartido",
                "peso": len(kpi_ids),
                "kpis": [nombre_por_id.get(k, "") for k in kpi_ids if nombre_por_id.get(k)],
            }
        )
    return aristas


@router.post(
    "/recomendar",
    status_code=status.HTTP_200_OK,
    summary="Recomendaciones en tiempo real para un set activo",
    description=(
        "Dado un conjunto de instrumentos activos, devuelve los instrumentos del "
        "acervo más afines combinando similitud semántica (vectores de Chroma) y "
        "solape de KPIs (Jaccard). Si Chroma no responde, degrada a solo-KPI "
        "(`degradado_semantico: true`)."
    ),
)
def recomendar(
    usuario_actual: UsuarioActual, db: DBSession, request: RecomendarRequest
) -> dict:
    autor_efectivo = _autor_efectivo(request.autorId, usuario_actual.usuario_id)

    ids = [i for i in (_a_int(x) for x in request.instrumentoIds) if i is not None]
    descartados = len(request.instrumentoIds) - len(ids)
    if descartados:
        logger.debug("Se descartaron %d instrumentoIds no numéricos.", descartados)

    try:
        recomendaciones, parametros, degradado = grafo_recomendador.recomendar(
            db,
            ids,
            autor_id=autor_efectivo,
            w_sem=request.w_sem,
            w_kpi=request.w_kpi,
            top_n=request.top_n,
            min_score=request.min_score,
            excluir_propios=request.excluir_propios,
        )
    except SQLAlchemyError:
        logger.exception("Error al calcular recomendaciones del grafo.")
        raise

    return {
        "recomendaciones": [vars(r) for r in recomendaciones],
        "parametros": parametros,
        "degradado_semantico": degradado,
    }


@router.post(
    "/investigacion",
    status_code=status.HTTP_200_OK,
    summary="Persistir el grafo de una investigación y traducir ids a id_crudo",
    description=(
        "Guarda el snapshot del grafo (set activo + recomendados mostrados) para "
        "trazabilidad y devuelve los `instrumentoIdsCrudo` (traducción de "
        "id_instrumento → id_crudo) para que el frontend dispare /rag/index."
    ),
)
def investigacion(
    usuario_actual: UsuarioActual, db: DBSession, request: InvestigacionRequest
) -> dict:
    ids = [i for i in (_a_int(x) for x in request.instrumentoIds) if i is not None]

    # Traducción id_instrumento → id_crudo por JOIN.
    ids_crudo: list[str] = []
    if ids:
        try:
            filas = (
                db.query(InstrumentoProcesado.id_instrumento, RawData.id_crudo)
                .join(RawData, RawData.id_crudo == InstrumentoProcesado.id_crudo)
                .filter(InstrumentoProcesado.id_instrumento.in_(ids))
                .all()
            )
        except SQLAlchemyError:
            logger.exception("Error al traducir id_instrumento → id_crudo.")
            raise
        por_instrumento = {int(i): int(c) for i, c in filas}
        for id_inst in ids:
            crudo = por_instrumento.get(id_inst)
            if crudo is None:
                logger.warning(
                    "id_instrumento=%s sin id_crudo asociado; se omite de la traducción.",
                    id_inst,
                )
                continue
            ids_crudo.append(str(crudo))

    registro = GrafoInvestigacion(
        investigacion_id=request.investigacionId,
        id_owner=usuario_actual.usuario_id,
        instrumento_ids=request.instrumentoIds,
        grafo_snapshot=request.grafo_snapshot,
        parametros=None,
    )
    try:
        db.add(registro)
        db.commit()
        db.refresh(registro)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error al guardar el grafo de investigación en tt_rag.grafo_investigacion.")
        raise

    return {
        "ok": True,
        "investigacionId": request.investigacionId,
        "grafoId": registro.grafo_id,
        "instrumentoIdsCrudo": ids_crudo,
    }
