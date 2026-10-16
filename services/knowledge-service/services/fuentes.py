"""Carga de las fuentes de un instrumento: autoría, limpieza confirmada, metadatos
aprobados, instrumento original, CSV limpio y JSON técnico.

knowledge-service solo LEE estas fuentes (base de datos compartida y
storage-service); no modifica nada de metadata-service ni de cleaning-service.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.models.metadatos_dc import MetadatosDC
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.metadatos_entrevistas import MetadatosEnriquecidosEntrevistas
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from services import estructura, original, storage_client
from services.estructura import Estructura

logger = logging.getLogger("knowledge-service")

_TABLA_ESPECIFICOS = {
    "encuesta": MetadatosEnriquecidosEncuestas,
    "entrevista": MetadatosEnriquecidosEntrevistas,
    "prueba_estandarizada": MetadatosEnriquecidosPruebas,
}
_CAMPOS_DC = (
    "dc_title", "dc_creator", "dc_subject", "dc_description", "dc_type", "dc_date", "dc_language",
    "dc_coverage", "dc_publisher", "dc_rights", "dc_format", "dc_source", "dc_relation",
)


@dataclass
class Contexto:
    raw: RawData
    procesado: InstrumentoProcesado
    limpieza: LimpiezaEjecucion | None

    @property
    def tipo(self) -> str:
        return self.raw.tipo_instrumento


def cargar(db: Session, usuario: Usuario, id_crudo: int) -> Contexto:
    """Instrumento del autor (o de cualquiera, si es admin) con su última limpieza confirmada."""
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento (id_crudo={id_crudo}) no encontrado.")
    if usuario.rol != ROL_ADMINISTRADOR and raw.id_owner != usuario.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el autor del instrumento puede construir su perfil.")
    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento no tiene registro de procesamiento.")
    limpieza = (
        db.query(LimpiezaEjecucion)
        .filter(
            LimpiezaEjecucion.id_crudo == id_crudo,
            LimpiezaEjecucion.estado == "confirmada",
            LimpiezaEjecucion.ruta_csv_limpio.isnot(None),
        )
        .order_by(LimpiezaEjecucion.version.desc())
        .first()
    )
    return Contexto(raw=raw, procesado=procesado, limpieza=limpieza)


def metadatos_aprobados(db: Session, ctx: Contexto) -> tuple[dict[str, Any], dict[str, Any]]:
    """(Dublin Core, específicos del tipo) tal como los aprobó el autor; 409 si aún no se aprueban."""
    dc = db.get(MetadatosDC, ctx.raw.id_crudo)
    if dc is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Primero aprueba los metadatos del instrumento.")
    tabla = _TABLA_ESPECIFICOS.get(ctx.tipo)
    esp = db.get(tabla, ctx.raw.id_crudo) if tabla else None
    datos_dc = {c: getattr(dc, c, None) for c in _CAMPOS_DC}
    datos_esp = {c.key: getattr(esp, c.key) for c in esp.__table__.columns if c.key != "id_crudo"} if esp else {}
    return datos_dc, datos_esp


def _error_storage(exc: storage_client.StorageError) -> HTTPException:
    if exc.status_code is None:
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo leer un archivo del instrumento: {exc}")


def texto_original(ctx: Contexto) -> str:
    """Texto del instrumento original (solo preguntas); cadena vacía si no se subió o no se puede leer."""
    ruta = ctx.raw.raw_archivo_original
    if not ruta or ruta == ctx.raw.raw_archivo:
        return ""
    try:
        return storage_client.texto(ruta)
    except storage_client.StorageError as exc:
        # El original es opcional: si falla su lectura se sigue con los encabezados.
        logger.warning("No se pudo leer el original de id_crudo=%s: %s", ctx.raw.id_crudo, exc)
        return ""


def filas_limpias(ctx: Contexto) -> list[dict[str, str]]:
    """Filas del CSV limpio como diccionarios (vacío si no hay limpieza confirmada)."""
    if ctx.limpieza is None:
        return []
    try:
        tabla = storage_client.tabla(ctx.limpieza.ruta_csv_limpio)
    except storage_client.StorageError as exc:
        raise _error_storage(exc) from exc
    encabezados = tabla.get("headers") or []
    return [dict(zip(encabezados, fila)) for fila in tabla.get("rows") or []]


def estructura_de(ctx: Contexto) -> Estructura:
    """Secciones y preguntas del instrumento a partir de la mejor fuente disponible."""
    texto = texto_original(ctx)
    instrumento_original = original.leer(texto) if texto.strip() else None
    id_crudo = ctx.raw.id_crudo

    if ctx.limpieza is not None:
        reporte = ctx.limpieza.reporte or {}
        if ctx.tipo == "encuesta":
            return estructura.encuesta(id_crudo, reporte, instrumento_original)
        if ctx.tipo == "entrevista":
            return estructura.entrevista(id_crudo, filas_limpias(ctx), instrumento_original)
        if ctx.tipo == "prueba_estandarizada":
            clave = ((reporte.get("especifico") or {}).get("prueba_estandarizada") or {}).get("clave")
            documento = "" if clave else "\n".join(f.get("texto", "") for f in filas_limpias(ctx))
            return estructura.prueba(id_crudo, reporte, instrumento_original, documento)

    # Instrumentos anteriores a la limpieza: el JSON técnico que ya existe en storage.
    try:
        tecnico = storage_client.obtener_json(id_crudo, "analysis") or storage_client.obtener_json(id_crudo, "metadata")
    except storage_client.StorageError as exc:
        raise _error_storage(exc) from exc
    if tecnico:
        return estructura.desde_json_tecnico(id_crudo, ctx.tipo, tecnico)
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        "El instrumento no tiene una limpieza confirmada: confirma la limpieza antes de generar su perfil.",
    )
