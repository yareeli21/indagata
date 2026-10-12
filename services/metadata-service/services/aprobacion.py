"""Aprobación de metadatos por el autor e ingesta al RAG.

Reglas:
  - Solo el autor del instrumento (raw_data.id_owner) o un administrador puede
    ver la propuesta, aprobarla, finalizarla o retirarla.
  - Aprobar exige el Dublin Core completo y los obligatorios del tipo.
  - Al aprobar: se genera el JSON estandarizado, el storage-service lo guarda
    (artefacto `metadata`), se persisten metadatos_dc + metadatos_enriquecidos_*,
    `instrumento_procesado` queda `estandarizado` con `fecha_aprobado`, y se pide
    la ingesta al índice vectorial (si falla, la aprobación se conserva y la
    respuesta lo informa para reintentar).
  - Re-aprobar (el autor corrige algo) sobrescribe los metadatos y reingiere.
  - Finalizar: añade al JSON los KPIs aceptados en el analysis-service
    (`kpi_inferido`) y lo guarda como artefacto `analysis`.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.kpi_inferido_chunk import KpiInferidoChunk
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from services import analizador, json_estandarizado, storage_client
from services.campos import CAMPOS_DC, campos_de
from services.dc_manager import DCManager
from services.enrichment_engine import EnrichmentEngine

logger = logging.getLogger("metadata-service")


@dataclass
class Contexto:
    raw: RawData
    procesado: InstrumentoProcesado
    autor: Usuario | None

    @property
    def tipo(self) -> str:
        return (self.raw.tipo_instrumento or "").lower()

    @property
    def aprobado(self) -> bool:
        return self.procesado.fecha_aprobado is not None

    @property
    def autor_nombre(self) -> str:
        return self.autor.nombre if self.autor else ""


def cargar_contexto(db: Session, usuario: Usuario, id_crudo: int, *, exigir_dueno: bool = True) -> Contexto:
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento (id_crudo={id_crudo}) no encontrado.")
    if exigir_dueno and usuario.rol != ROL_ADMINISTRADOR and raw.id_owner != usuario.usuario_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el autor del instrumento puede revisar y aprobar sus metadatos.",
        )
    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento no tiene registro de procesamiento.")
    try:
        campos_de(raw.tipo_instrumento)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return Contexto(raw=raw, procesado=procesado, autor=db.get(Usuario, raw.id_owner))


def error_storage(exc: storage_client.StorageError) -> HTTPException:
    if exc.status_code in (404, 422):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"No se pudo leer el instrumento: {exc}")
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"Almacenamiento no disponible: {exc}")


def analizar(ctx: Contexto) -> analizador.Analisis:
    try:
        return analizador.analizar(ctx.raw, ctx.procesado)
    except storage_client.StorageError as exc:
        raise error_storage(exc) from exc


def normalizar(ctx: Contexto, payload: dict[str, Any]) -> tuple[dict, dict, dict[str, dict[str, str]]]:
    dc = DCManager.normalizar(payload.get("dublin_core"))
    especificos = EnrichmentEngine.normalizar(ctx.tipo, payload.get("enriquecidos"))
    errores = {
        "dublin_core": DCManager.validar(dc),
        "enriquecidos": EnrichmentEngine.validar(ctx.tipo, especificos),
    }
    return dc, especificos, errores


def _mensaje_errores(ctx: Contexto, errores: dict[str, dict[str, str]]) -> str:
    etiquetas = {c.clave: c.etiqueta for c in (*CAMPOS_DC, *campos_de(ctx.tipo))}
    faltantes = [etiquetas.get(k, k) for grupo in errores.values() for k in grupo]
    detalle = " ".join(m for grupo in errores.values() for m in grupo.values())
    return f"Revisa los metadatos antes de aprobar ({', '.join(faltantes)}). {detalle}".strip()


def _ingerir(id_crudo: int) -> dict[str, Any]:
    try:
        r = storage_client.indexar(id_crudo, reindexar=True)
        return {"indexado": r.get("estado") == "indexado", "chunks": int(r.get("chunks") or 0), "motivo": r.get("motivo")}
    except storage_client.StorageError as exc:
        logger.warning("Ingesta al RAG pendiente para %s: %s", id_crudo, exc)
        return {"indexado": False, "chunks": 0, "motivo": str(exc)}


def _nombre_json(dc: dict[str, Any], id_crudo: int) -> str:
    return f"{(dc.get('dc_title') or f'instrumento_{id_crudo}')[:80]}.json"


def propuesta(
    db: Session, usuario: Usuario, id_crudo: int, grupo: str, usar_llm: bool | None
) -> dict[str, Any]:
    """Propuesta de un grupo de metadatos: `dublin_core` o `enriquecidos`.

    Si el autor ya aprobó, devuelve lo aprobado (origen `aprobado`).
    """
    from shared.db.core.config import settings

    from services import propuestas
    from services.campos import NOMBRE_TABLA_POR_TIPO, obligatorios

    ctx = cargar_contexto(db, usuario, id_crudo)
    campos = CAMPOS_DC if grupo == "dublin_core" else campos_de(ctx.tipo)
    base = {
        "id_crudo": id_crudo,
        "id_instrumento": ctx.procesado.id_instrumento,
        "tipo_instrumento": ctx.tipo,
        "tabla": "metadatos_dc" if grupo == "dublin_core" else NOMBRE_TABLA_POR_TIPO[ctx.tipo],
        "aprobado": ctx.aprobado,
        "fecha_aprobado": ctx.procesado.fecha_aprobado,
        "obligatorios": obligatorios(campos),
        "campos": [c.a_dict() for c in campos],
    }
    if ctx.aprobado:
        guardados = (
            DCManager.obtener(db, id_crudo)
            if grupo == "dublin_core"
            else EnrichmentEngine.obtener(db, ctx.tipo, id_crudo)
        )
        if guardados is not None:
            return {**base, "valores": guardados, "origen": {k: "aprobado" for k in guardados}}

    try:
        prop = propuestas.construir(
            ctx.raw,
            ctx.procesado,
            ctx.autor_nombre,
            usar_llm=settings.METADATA_USAR_LLM if usar_llm is None else usar_llm,
        )
    except storage_client.StorageError as exc:
        raise error_storage(exc) from exc
    if grupo == "dublin_core":
        return {**base, "valores": prop.dc, "origen": prop.dc_origen, "notas": prop.analisis.notas}
    return {**base, "valores": prop.especificos, "origen": prop.especificos_origen, "notas": prop.analisis.notas}


def vista_previa(db: Session, usuario: Usuario, id_crudo: int, payload: dict[str, Any]) -> dict[str, Any]:
    ctx = cargar_contexto(db, usuario, id_crudo)
    dc, especificos, errores = normalizar(ctx, payload)
    data = json_estandarizado.construir(
        ctx.raw, ctx.procesado, dc, especificos, analizar(ctx), aprobado_por=None, fecha_aprobado=None
    )
    return {
        "json_estandarizado": data,
        "valido": not any(errores.values()),
        "errores": errores,
    }


def aprobar(db: Session, usuario: Usuario, id_crudo: int, payload: dict[str, Any]) -> dict[str, Any]:
    ctx = cargar_contexto(db, usuario, id_crudo)
    dc, especificos, errores = normalizar(ctx, payload)
    if any(errores.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _mensaje_errores(ctx, errores))

    analisis = analizar(ctx)
    ahora = datetime.now(timezone.utc)
    data = json_estandarizado.construir(
        ctx.raw, ctx.procesado, dc, especificos, analisis, aprobado_por=usuario.nombre, fecha_aprobado=ahora
    )
    try:
        artefacto = storage_client.guardar_json(id_crudo, "metadata", data, _nombre_json(dc, id_crudo))
    except storage_client.StorageError as exc:
        raise error_storage(exc) from exc

    try:
        DCManager.guardar(db, id_crudo, dc)
        EnrichmentEngine.guardar(db, ctx.tipo, id_crudo, especificos)
        ctx.procesado.ruta_json = artefacto["ruta_absoluta"]
        ctx.procesado.estado = "estandarizado"
        ctx.procesado.fecha_aprobado = ahora.replace(tzinfo=None)  # columna TIMESTAMP (UTC)
        ctx.procesado.fecha_procesamiento = ahora.replace(tzinfo=None)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("No se pudieron guardar los metadatos de %s.", id_crudo)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No se pudieron guardar los metadatos.") from exc

    ingesta = _ingerir(id_crudo)
    db.refresh(ctx.procesado)
    mensaje = (
        "Metadatos aprobados e instrumento ingerido al RAG."
        if ingesta["indexado"]
        else "Metadatos aprobados. La ingesta al RAG quedó pendiente; se reintentará al armar una investigación."
    )
    return {
        "id_crudo": id_crudo,
        "id_instrumento": ctx.procesado.id_instrumento,
        "estado": ctx.procesado.estado,
        "aprobado": True,
        "fecha_aprobado": ctx.procesado.fecha_aprobado,
        "json_estandarizado": data,
        "texto_instrumento": json_estandarizado.texto_instrumento(data),
        "artefacto": {"key": artefacto["key"], "version": artefacto["version"]},
        "ingesta": ingesta,
        "mensaje": mensaje,
    }


def kpis_aceptados(db: Session, id_crudo: int) -> list[dict[str, Any]]:
    """KPIs aceptados por el autor (kpi_inferido) con su mejor score de evidencia."""
    ids_procesados = [
        p.id_instrumento
        for p in db.query(InstrumentoProcesado.id_instrumento).filter(InstrumentoProcesado.id_crudo == id_crudo)
    ]
    if not ids_procesados:
        return []
    filas = (
        db.query(KPIInferido.kpi_id, KPI.nombre, func.max(KpiInferidoChunk.score))
        .join(KPI, KPI.kpi_id == KPIInferido.kpi_id)
        .outerjoin(
            KpiInferidoChunk,
            (KpiInferidoChunk.id_procesado == KPIInferido.id_procesado)
            & (KpiInferidoChunk.kpi_id == KPIInferido.kpi_id),
        )
        .filter(KPIInferido.id_procesado.in_(ids_procesados))
        .group_by(KPIInferido.kpi_id, KPI.nombre)
        .order_by(KPIInferido.kpi_id)
        .all()
    )
    return [
        {"kpi_id": kpi_id, "nombre_kpi": nombre, "score": float(score) if score is not None else None}
        for kpi_id, nombre, score in filas
    ]


def finalizar(db: Session, usuario: Usuario, id_crudo: int) -> dict[str, Any]:
    ctx = cargar_contexto(db, usuario, id_crudo)
    if not ctx.aprobado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aprueba primero los metadatos del instrumento.")
    kpis = kpis_aceptados(db, id_crudo)
    try:
        base = storage_client.obtener_json(id_crudo, "metadata")
    except storage_client.StorageError as exc:
        raise error_storage(exc) from exc
    if base is None:
        # Sin artefacto (p. ej. storage reiniciado): se reconstruye desde la BD.
        dc = DCManager.obtener(db, id_crudo) or {}
        especificos = EnrichmentEngine.obtener(db, ctx.tipo, id_crudo) or {}
        base = json_estandarizado.construir(
            ctx.raw, ctx.procesado, dc, especificos, analizar(ctx),
            aprobado_por=ctx.autor_nombre, fecha_aprobado=ctx.procesado.fecha_aprobado,
        )

    data = copy.deepcopy(base)
    data["inferred_kpis"] = kpis
    pistas = list((data.get("design_reference") or {}).get("kpi_hints") or [])
    for k in kpis:
        if k["nombre_kpi"] not in pistas:
            pistas.append(k["nombre_kpi"])
    data["design_reference"] = {**(data.get("design_reference") or {}), "kpi_hints": pistas}
    data["finalized_at"] = datetime.now(timezone.utc).isoformat()

    titulo = (data.get("instrument") or {}).get("title") or ""
    try:
        artefacto = storage_client.guardar_json(id_crudo, "analysis", data, _nombre_json({"dc_title": titulo}, id_crudo))
    except storage_client.StorageError as exc:
        raise error_storage(exc) from exc
    ctx.procesado.ruta_json = artefacto["ruta_absoluta"]
    db.commit()
    ingesta = _ingerir(id_crudo)
    return {
        "id_crudo": id_crudo,
        "kpis": kpis,
        "artefacto": {"key": artefacto["key"], "version": artefacto["version"]},
        "ingesta": ingesta,
        "mensaje": f"Instrumento guardado con {len(kpis)} KPI(s) asociados.",
    }


def retirar(db: Session, usuario: Usuario, id_crudo: int) -> dict[str, Any]:
    """Elimina los metadatos aprobados y saca al instrumento del RAG."""
    ctx = cargar_contexto(db, usuario, id_crudo)
    habia_dc = DCManager.eliminar(db, id_crudo)
    habia_esp = EnrichmentEngine.eliminar(db, ctx.tipo, id_crudo)
    if not (habia_dc or habia_esp or ctx.aprobado):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El instrumento no tiene metadatos registrados.")
    ctx.procesado.fecha_aprobado = None
    ctx.procesado.estado = "limpio" if ctx.procesado.ruta_de_archivo_limpio else "recibido"
    db.commit()
    try:
        storage_client.desindexar(id_crudo)
    except storage_client.StorageError as exc:
        logger.warning("No se pudieron quitar los vectores de %s: %s", id_crudo, exc)
    return {"id_crudo": id_crudo, "mensaje": "Metadatos eliminados; el instrumento salió del RAG."}
