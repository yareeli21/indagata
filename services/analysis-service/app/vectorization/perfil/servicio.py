"""Casos de uso: proponer y confirmar KPIs desde el perfil semántico.

Lee el perfil de la versión actual de `tt_rag.version_conocimiento` (lo escribe
knowledge-service al aprobar los metadatos) y, al confirmar, escribe en ESA MISMA
fila las decisiones (aceptadas y rechazadas) y `perfil.kpis_asociados`. Los KPIs
aceptados se siguen registrando en `kpi_inferido` / `kpi_inferido_chunk` como
siempre, porque los tableros de visualization-service los leen.

La colección `kpis` solo se LEE (vectores ya indexados de `texto_contexto_rag_vectorial`).
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.vectorization.core import chroma_client, embeddings
from app.vectorization.perfil import asociacion, justificacion, unidades
from app.vectorization.schemas.perfil_kpis import (
    ConfirmarPerfilRequest,
    ConfirmarPerfilResponse,
    PropuestasPerfilResponse,
)
from app.vectorization.schemas.vectorizacion import ConfirmarRequest, DecisionKPI
from app.vectorization.services.enrichment_service import EnrichmentService
from shared.auth import ROL_ADMINISTRADOR
from shared.db.core.config import settings
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

logger = logging.getLogger("analysis-service")

_EDITABLES = ("perfil_aprobado", "kpis_confirmados")


def kpi_ref(kpi_id: int) -> str:
    """ID global del KPI en los documentos (KPI-07)."""
    return f"KPI-{kpi_id:02d}"


def pesos() -> asociacion.Pesos:
    return asociacion.Pesos(
        general=settings.KPI_PESO_GENERAL,
        preguntas=settings.KPI_PESO_PREGUNTAS,
        cobertura=settings.KPI_PESO_COBERTURA,
        umbral_evidencia=settings.KPI_UMBRAL_EVIDENCIA,
        umbral_score=settings.KPI_SEARCH_MIN_SCORE,
        max_propuestas=settings.KPI_MAX_PROPUESTAS,
    )


def ficha_kpi(k: KPI) -> dict[str, Any]:
    """Campos del KPI para el documento (ver hallazgo 7 del plan)."""
    return {
        "nombre": k.nombre,
        "definicion": k.texto_contexto_rag_vectorial or "",
        "que_mide": k.descripcion_ampliada_educativa or "",
        "dimension": k.tipo_objetivo_estrategico or "",
        "polaridad": k.polaridad_rendimiento or "",
    }


def vectores_kpis(collection=None) -> list[tuple[int, list[float]]]:
    """Todos los vectores de la colección `kpis` (solo lectura; no se reindexa nada)."""
    coleccion = collection or chroma_client.get_or_create_collection(settings.CHROMA_COLLECTION_KPIS)
    res = coleccion.get(include=["embeddings", "metadatas"])
    metas = res.get("metadatas") or []
    vectores = res.get("embeddings")
    if vectores is None:
        return []
    salida = []
    for meta, vec in zip(metas, vectores):
        if meta and meta.get("kpi_id") is not None and vec is not None:
            salida.append((int(meta["kpi_id"]), [float(x) for x in vec]))
    return salida


def _version(db: Session, usuario: Usuario, id_crudo: int) -> VersionConocimiento:
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento (id_crudo={id_crudo}) no encontrado.")
    if usuario.rol != ROL_ADMINISTRADOR and raw.id_owner != usuario.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el autor del instrumento puede asociar sus KPIs.")
    fila = (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.estado != "reemplazado")
        .order_by(VersionConocimiento.version.desc())
        .first()
    )
    if fila is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento aún no tiene perfil semántico: aprueba sus metadatos.")
    return fila


def proponer(
    db: Session,
    usuario: Usuario,
    id_crudo: int,
    *,
    justificar_con_llm: bool | None = None,
    collection=None,
) -> PropuestasPerfilResponse:
    """KPIs sugeridos para el perfil de la versión actual, con evidencia y justificación."""
    fila = _version(db, usuario, id_crudo)
    perfil = fila.perfil or {}
    general = unidades.texto_general(perfil)
    preguntas = unidades.unidades_pregunta(perfil)
    vectores = embeddings.embed_texts([general] + [u.unidad for u in preguntas])
    kpis = vectores_kpis(collection)
    if not kpis:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "El catálogo de KPIs no está indexado.")

    propuestas = asociacion.asociar(
        vectores[0], [(u.pregunta_id, v) for u, v in zip(preguntas, vectores[1:])], kpis, pesos()
    )
    fichas = {k.kpi_id: ficha_kpi(k) for k in db.query(KPI).filter(KPI.kpi_id.in_([p.kpi_id for p in propuestas]))}
    texto_de = {u.pregunta_id: u.texto for u in preguntas}
    usar_llm = settings.KPI_JUSTIFICAR_LLM if justificar_con_llm is None else justificar_con_llm

    salida = []
    for p in propuestas:
        ficha = fichas.get(p.kpi_id)
        if ficha is None:
            continue  # vector huérfano en Chroma (KPI borrado de la BD)
        evidencia = [{"pregunta_id": e.pregunta_id, "texto": texto_de.get(e.pregunta_id, ""), "similitud": e.similitud} for e in p.evidencia]
        texto, origen = justificacion.justificar(
            ficha, perfil.get("objetivo") or "", [e["texto"] for e in evidencia], usar_llm=usar_llm
        )
        salida.append(
            {
                "kpi_id": p.kpi_id,
                "kpi_ref": kpi_ref(p.kpi_id),
                **ficha,
                "score": p.score,
                "componentes": p.componentes,
                "evidencia": evidencia,
                "justificacion": texto,
                "justificacion_origen": origen,
            }
        )
    w = pesos()
    return PropuestasPerfilResponse(
        id_crudo=id_crudo,
        version=fila.version,
        n_preguntas=len(preguntas),
        formula={"peso_general": w.general, "peso_preguntas": w.preguntas, "peso_cobertura": w.cobertura,
                 "umbral_evidencia": w.umbral_evidencia, "umbral_score": w.umbral_score},
        kpis=salida,
    )


def confirmar(db: Session, usuario: Usuario, cuerpo: ConfirmarPerfilRequest) -> ConfirmarPerfilResponse:
    """Guarda las decisiones en la versión del conocimiento y registra los aceptados."""
    fila = _version(db, usuario, cuerpo.id_crudo)
    if fila.version != cuerpo.version:
        raise HTTPException(status.HTTP_409_CONFLICT, "La versión del perfil cambió; vuelve a generar las sugerencias.")
    if fila.estado not in _EDITABLES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Los KPIs de esta versión ya no se pueden cambiar.")

    ids = [d.kpi_id for d in cuerpo.decisiones]
    if len(ids) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hay KPIs repetidos en las decisiones.")
    kpis = {k.kpi_id: k for k in db.query(KPI).filter(KPI.kpi_id.in_(ids))}
    faltantes = sorted(set(ids) - set(kpis))
    if faltantes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"KPIs inexistentes: {faltantes}.")
    preguntas_validas = {q.get("id") for s in (fila.perfil or {}).get("secciones") or [] for q in s.get("preguntas") or []}
    for d in cuerpo.decisiones:
        ajenas = [e.pregunta_id for e in d.evidencia if e.pregunta_id not in preguntas_validas]
        if ajenas:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"La evidencia cita preguntas que no están en el perfil: {ajenas}.")

    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == cuerpo.id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento no tiene registro de procesamiento.")

    ahora = datetime.now(timezone.utc)
    decisiones: list[dict[str, Any]] = []
    asociados: list[dict[str, Any]] = []
    for d in cuerpo.decisiones:
        origen = justificacion.origen_final(d.justificacion_origen, d.editada)
        texto = " ".join(d.justificacion.split())
        evidencia = [{"pregunta_id": e.pregunta_id, "similitud": round(e.similitud, 4)} for e in d.evidencia]
        decisiones.append(
            {
                "kpi_id": d.kpi_id,
                "decision": "aceptado" if d.aceptado else "rechazado",
                "score": round(d.score, 4),
                "componentes": d.componentes,
                "evidencia": evidencia,
                "justificacion": texto,
                "justificacion_origen": origen,
                "por": usuario.usuario_id,
                "fecha": ahora.isoformat(),
            }
        )
        if d.aceptado:
            ficha = ficha_kpi(kpis[d.kpi_id])
            asociados.append(
                {
                    "kpi_id": kpi_ref(d.kpi_id),
                    "nombre": ficha["nombre"],
                    "definicion": ficha["definicion"],
                    "dimension": ficha["dimension"],
                    "que_mide": ficha["que_mide"],
                    "similitud": round(d.score, 4),
                    "evidencia": evidencia,
                    "justificacion": texto,
                    "justificacion_origen": origen,
                    "aceptado_por": usuario.nombre,
                    "fecha": ahora.isoformat(),
                }
            )

    # 1) Registro de siempre (kpi_inferido + kpi_inferido_chunk) para los tableros.
    EnrichmentService.confirm(
        db,
        ConfirmarRequest(
            id_instrumento=procesado.id_instrumento,
            decisiones=[DecisionKPI(kpi_id=d.kpi_id, aceptado=d.aceptado, score=round(d.score, 4)) for d in cuerpo.decisiones],
            json_instrumento={},
        ),
    )
    aceptados = {d.kpi_id for d in cuerpo.decisiones if d.aceptado}
    for inferido in db.query(KPIInferido).filter(KPIInferido.id_procesado == procesado.id_instrumento):
        if inferido.kpi_id not in aceptados:
            db.delete(inferido)  # rechazado en esta versión (antes aceptado): ya no se asocia
        else:
            razon = next(x["justificacion"] for x in asociados if x["kpi_id"] == kpi_ref(inferido.kpi_id))
            inferido.razon = razon or inferido.razon

    # 2) Versión del conocimiento: decisiones (todas) y kpis_asociados (solo aceptados).
    perfil = copy.deepcopy(fila.perfil or {})
    perfil["kpis_asociados"] = asociados
    fila.perfil = perfil
    fila.decisiones_kpi = decisiones
    fila.estado = "kpis_confirmados"
    fila.fecha_kpis = ahora.replace(tzinfo=None)
    db.commit()
    db.refresh(fila)
    return ConfirmarPerfilResponse(
        id_crudo=cuerpo.id_crudo,
        version=fila.version,
        estado=fila.estado,
        kpis_asociados=asociados,
        n_rechazados=sum(1 for d in decisiones if d["decision"] == "rechazado"),
    )
