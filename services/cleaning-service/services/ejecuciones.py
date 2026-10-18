"""Ciclo de vida de una ejecución de limpieza (tabla `limpieza_ejecucion`).

    crear ──▶ esperando_decisiones ──(decisiones parciales)──▶ confirmar ──▶ confirmada
       └──▶ fallida (error claro para el investigador; no se envía nada a metadata)

- Cada ejecución es una VERSIÓN (1, 2, 3…) del mismo instrumento. Repetir la
  limpieza de una versión confirmada crea otra versión; el crudo nunca cambia.
- Las decisiones se guardan conforme el investigador las toma, para que pueda
  retomar la fase asistida si cierra la página.
- Al confirmar se repite la fase automática sobre el crudo (determinista) y se
  aplican las decisiones; el CSV limpio va a storage-service y el reporte a JSONB.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from services import VERSION_SERVICIO, configuracion, motores, storage_client
from services.motores import Entrada, ErrorLimpieza, Hallazgo, MotorNoDisponible, ResultadoAutomatico
from services.motores.resumen import resumir

logger = logging.getLogger("cleaning-service")

ESQUEMA_REPORTE = "reporte_limpieza/1"
_MENSAJE_INESPERADO = (
    "Ocurrió un error inesperado al limpiar el archivo. Revisa que no esté dañado "
    "e inténtalo de nuevo; si persiste, avisa al administrador."
)


# Estados de instrumento_procesado que la limpieza puede actualizar. Un instrumento que
# ya avanzó (metadatos, estandarizado, vectorizado) no retrocede por repetir la limpieza.
_ESTADOS_PREVIOS = ("recibido", "limpieza_en_proceso", "limpio", "error")


def _avanzar_estado(procesado: InstrumentoProcesado, estado: str) -> None:
    if procesado.estado in _ESTADOS_PREVIOS:
        procesado.estado = estado


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ── Contexto del instrumento ───────────────────────────────────────────────────


@dataclass
class Contexto:
    raw: RawData
    procesado: InstrumentoProcesado


def cargar_contexto(db: Session, usuario: Usuario, id_crudo: int) -> Contexto:
    """Instrumento del autor (o de cualquiera, si es admin) con su registro de procesamiento."""
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento (id_crudo={id_crudo}) no encontrado.")
    if usuario.rol != ROL_ADMINISTRADOR and raw.id_owner != usuario.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el autor del instrumento puede limpiarlo.")
    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El instrumento no tiene registro de procesamiento.")
    return Contexto(raw=raw, procesado=procesado)


_ESTADOS_APROBADOS = {"estandarizado", "vectorizado"}


def leer_resumen_permitido(db: Session, usuario: Usuario, id_crudo: int) -> RawData:
    """Para el resumen de la limpieza: el autor o un admin siempre; otro investigador
    solo si el instrumento ya está aprobado (son cifras agregadas, sin filas)."""
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento (id_crudo={id_crudo}) no encontrado.")
    if usuario.rol == ROL_ADMINISTRADOR or raw.id_owner == usuario.usuario_id:
        return raw
    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None or not (procesado.fecha_aprobado is not None or procesado.estado in _ESTADOS_APROBADOS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El instrumento aún no está aprobado por su autor.")
    return raw


def _extension(raw: RawData) -> str:
    """Extensión del crudo: la de la key en storage o, si no tiene, la del nombre original."""
    ext = PurePosixPath(raw.raw_archivo or "").suffix or PurePosixPath(raw.nombre_archivo or "").suffix
    return ext.lower()


def _entrada(raw: RawData) -> Entrada:
    """Descarga el crudo (y la clave, si hay) desde storage-service."""
    try:
        contenido = storage_client.descargar(raw.raw_archivo)
        clave = storage_client.descargar(raw.raw_archivo_clave) if raw.raw_archivo_clave else None
    except storage_client.StorageError as exc:
        if exc.status_code is None:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"No se pudo leer el archivo crudo del instrumento: {exc}"
        ) from exc
    return Entrada(
        id_crudo=raw.id_crudo,
        tipo_instrumento=raw.tipo_instrumento,
        nombre_archivo=raw.nombre_archivo,
        extension=_extension(raw),
        contenido=contenido,
        clave=clave,
        extension_clave=PurePosixPath(raw.raw_archivo_clave).suffix.lower() if raw.raw_archivo_clave else None,
    )


# ── Consultas ──────────────────────────────────────────────────────────────────


def ultima(db: Session, id_crudo: int) -> LimpiezaEjecucion | None:
    return (
        db.query(LimpiezaEjecucion)
        .filter(LimpiezaEjecucion.id_crudo == id_crudo)
        .order_by(LimpiezaEjecucion.version.desc())
        .first()
    )


def ultima_confirmada(db: Session, id_crudo: int) -> LimpiezaEjecucion | None:
    """La versión que debe usar metadata-service (la última confirmada)."""
    return (
        db.query(LimpiezaEjecucion)
        .filter(LimpiezaEjecucion.id_crudo == id_crudo, LimpiezaEjecucion.estado == "confirmada")
        .order_by(LimpiezaEjecucion.version.desc())
        .first()
    )


def obtener(db: Session, id_crudo: int, version: int) -> LimpiezaEjecucion:
    ejecucion = (
        db.query(LimpiezaEjecucion)
        .filter(LimpiezaEjecucion.id_crudo == id_crudo, LimpiezaEjecucion.version == version)
        .first()
    )
    if ejecucion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la versión {version} de la limpieza.")
    return ejecucion


def _siguiente_version(db: Session, id_crudo: int) -> int:
    maximo = db.query(func.max(LimpiezaEjecucion.version)).filter(LimpiezaEjecucion.id_crudo == id_crudo).scalar()
    return int(maximo or 0) + 1


# ── Reporte ────────────────────────────────────────────────────────────────────


def _reporte_inicial(
    ctx: Contexto, version: int, automatico: ResultadoAutomatico, decisiones: dict[str, Any]
) -> dict[str, Any]:
    salida = configuracion.reglas().get("salida", {})
    return {
        "esquema": ESQUEMA_REPORTE,
        "id_crudo": ctx.raw.id_crudo,
        "tipo_instrumento": ctx.raw.tipo_instrumento,
        "version": version,
        "version_servicio": VERSION_SERVICIO,
        "fecha": _ahora().isoformat(),
        "fecha_confirmacion": None,
        "archivos": {
            "crudo": ctx.raw.raw_archivo,
            "clave": ctx.raw.raw_archivo_clave,
            "limpio": None,
            "formato_limpio": {
                "separador": salida.get("separador", ";"),
                "codificacion": salida.get("codificacion", "utf-8-sig"),
            },
        },
        "metricas": {"antes": automatico.metricas, "despues": None},
        "estadistica": {"antes": automatico.estadistica, "despues": None},
        "transformaciones": [dict(t, origen="automatica") for t in automatico.transformaciones],
        "hallazgos": [h.a_dict() for h in automatico.hallazgos],
        "decisiones": decisiones,
        "avisos": list(automatico.avisos),
        "especifico": {ctx.raw.tipo_instrumento: automatico.especifico},
    }


def _hallazgos(reporte: dict[str, Any]) -> list[Hallazgo]:
    return [Hallazgo(**h) for h in reporte.get("hallazgos", [])]


def pendientes_obligatorias(reporte: dict[str, Any]) -> list[str]:
    """Hallazgos obligatorios que el investigador aún no decide."""
    decisiones = reporte.get("decisiones", {})
    return [h["id"] for h in reporte.get("hallazgos", []) if h.get("obligatoria") and h["id"] not in decisiones]


# ── Operaciones ────────────────────────────────────────────────────────────────


def crear(db: Session, usuario: Usuario, id_crudo: int, *, nueva: bool = False) -> LimpiezaEjecucion:
    """Corre la fase automática y crea una versión nueva.

    Sin `nueva`, si ya hay una versión esperando decisiones se devuelve esa (retomar).
    Con `nueva`, sobre una versión confirmada, se precargan sus decisiones.
    """
    ctx = cargar_contexto(db, usuario, id_crudo)
    anterior = ultima(db, id_crudo)
    if anterior is not None and anterior.estado == "esperando_decisiones" and not nueva:
        return anterior

    try:
        motor = motores.obtener(ctx.raw.tipo_instrumento, _extension(ctx.raw))
    except MotorNoDisponible as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc

    entrada = _entrada(ctx.raw)
    version = _siguiente_version(db, id_crudo)
    ejecucion = LimpiezaEjecucion(id_crudo=id_crudo, version=version, id_investigador=usuario.usuario_id)

    try:
        automatico = motor.automatica(entrada)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo del motor deja la versión como fallida
        mensaje = str(exc) if isinstance(exc, ErrorLimpieza) else _MENSAJE_INESPERADO
        if not isinstance(exc, ErrorLimpieza):
            logger.exception("Fallo inesperado limpiando id_crudo=%s", id_crudo)
        ejecucion.estado = "fallida"
        ejecucion.error = mensaje
        ejecucion.reporte = {"esquema": ESQUEMA_REPORTE, "id_crudo": id_crudo, "version": version, "error": mensaje}
        db.add(ejecucion)
        db.commit()
        db.refresh(ejecucion)
        return ejecucion

    # Al repetir una limpieza confirmada se precargan las decisiones que sigan aplicando.
    decisiones: dict[str, Any] = {}
    if anterior is not None and anterior.estado == "confirmada":
        opciones = {h.id: h.opciones for h in automatico.hallazgos}
        for hid, dec in (anterior.reporte or {}).get("decisiones", {}).items():
            if hid in opciones and dec.get("valor") in opciones[hid] and dec.get("origen") == "investigador":
                decisiones[hid] = dec

    ejecucion.estado = "esperando_decisiones"
    ejecucion.reporte = _reporte_inicial(ctx, version, automatico, decisiones)
    _avanzar_estado(ctx.procesado, "limpieza_en_proceso")
    db.add(ejecucion)
    return _guardar_nueva(db, ejecucion, id_crudo, nueva)


def _guardar_nueva(db: Session, ejecucion: LimpiezaEjecucion, id_crudo: int, nueva: bool) -> LimpiezaEjecucion:
    """Inserta la versión. Si otra petición simultánea ganó ese número de versión
    (p. ej. un doble clic o un doble montaje del navegador), se retoma la que ganó.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ganadora = ultima(db, id_crudo)
        if ganadora is not None and ganadora.estado == "esperando_decisiones" and not nueva:
            return ganadora
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Se está creando otra versión de esta limpieza al mismo tiempo. Inténtalo de nuevo.",
        ) from None
    db.refresh(ejecucion)
    return ejecucion


def guardar_decisiones(
    db: Session, usuario: Usuario, ejecucion: LimpiezaEjecucion, cambios: dict[str, str | None]
) -> LimpiezaEjecucion:
    """Guarda (merge) decisiones parciales. Valida que cada opción exista en su hallazgo."""
    if ejecucion.estado != "esperando_decisiones":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta versión de la limpieza ya no admite cambios.")
    reporte = dict(ejecucion.reporte or {})
    hallazgos = {h["id"]: h for h in reporte.get("hallazgos", [])}
    decisiones = dict(reporte.get("decisiones", {}))
    for hid, valor in cambios.items():
        if hid not in hallazgos:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Hallazgo desconocido: {hid}")
        if valor is None:
            decisiones.pop(hid, None)
            continue
        if valor not in hallazgos[hid]["opciones"]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Opción no válida para «{hallazgos[hid]['titulo']}»: {valor}",
            )
        decisiones[hid] = {
            "valor": valor,
            "origen": "investigador",
            "por": usuario.usuario_id,
            "fecha": _ahora().isoformat(),
        }
    reporte["decisiones"] = decisiones
    ejecucion.reporte = reporte  # reasignar: SQLAlchemy no detecta cambios internos del JSON
    ejecucion.fecha_actualizacion = _ahora().replace(tzinfo=None)
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def _csv(encabezados: list[str], filas: list[list[str]]) -> bytes:
    """CSV limpio con el separador y la codificación configurados (`;` y UTF-8 con BOM)."""
    salida = configuracion.reglas().get("salida", {})
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=salida.get("separador", ";"), lineterminator="\n")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return buffer.getvalue().encode(salida.get("codificacion", "utf-8-sig"))


def confirmar(db: Session, usuario: Usuario, ejecucion: LimpiezaEjecucion) -> LimpiezaEjecucion:
    """Aplica las decisiones, guarda el CSV limpio y cierra el reporte."""
    if ejecucion.estado != "esperando_decisiones":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta versión de la limpieza ya no se puede confirmar.")
    reporte = dict(ejecucion.reporte or {})
    faltan = pendientes_obligatorias(reporte)
    if faltan:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Faltan {len(faltan)} decisión(es) obligatoria(s) antes de confirmar.",
        )

    ctx = cargar_contexto(db, usuario, ejecucion.id_crudo)
    try:
        motor = motores.obtener(ctx.raw.tipo_instrumento, _extension(ctx.raw))
    except MotorNoDisponible as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc
    entrada = _entrada(ctx.raw)

    # Las decisiones no tomadas usan la opción sugerida y quedan registradas como tales.
    decisiones = dict(reporte.get("decisiones", {}))
    for h in _hallazgos(reporte):
        if h.id not in decisiones and h.sugerida is not None:
            decisiones[h.id] = {"valor": h.sugerida, "origen": "sugerida", "por": None, "fecha": _ahora().isoformat()}
    valores = {hid: d["valor"] for hid, d in decisiones.items()}

    try:
        automatico = motor.automatica(entrada)
        final = motor.aplicar(entrada, automatico, valores)
    except Exception as exc:  # noqa: BLE001
        mensaje = str(exc) if isinstance(exc, ErrorLimpieza) else _MENSAJE_INESPERADO
        if not isinstance(exc, ErrorLimpieza):
            logger.exception("Fallo inesperado confirmando id_crudo=%s v%s", ejecucion.id_crudo, ejecucion.version)
        ejecucion.estado = "fallida"
        ejecucion.error = mensaje
        db.commit()
        db.refresh(ejecucion)
        return ejecucion

    nombre = f"v{ejecucion.version}_{ctx.raw.tipo_instrumento}_limpio.csv"
    try:
        ruta = storage_client.guardar_limpio(ejecucion.id_crudo, nombre, _csv(final.encabezados, final.filas))
    except storage_client.StorageError as exc:
        # Fallo de infraestructura: la versión sigue esperando y se puede reintentar.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo guardar el archivo limpio: {exc}") from exc

    ahora = _ahora()
    reporte["decisiones"] = decisiones
    reporte["fecha_confirmacion"] = ahora.isoformat()
    reporte["archivos"] = dict(reporte.get("archivos", {}), limpio=ruta)
    reporte["metricas"] = {"antes": automatico.metricas, "despues": final.metricas}
    reporte["estadistica"] = {"antes": automatico.estadistica, "despues": final.estadistica}
    reporte["transformaciones"] = [dict(t, origen="automatica") for t in automatico.transformaciones] + [
        dict(t, origen="decision") for t in final.transformaciones
    ]
    reporte["especifico"] = {ctx.raw.tipo_instrumento: final.especifico}
    # Muestra pequeña para la vista final (evita volver a leer el CSV de storage).
    reporte["vista_final"] = {
        "cifras": final.cifras,
        **final.vista,
        "total_filas": len(final.filas),
        "comparacion": comparacion(automatico.metricas, final.metricas, automatico.estadistica, final.estadistica),
        "estadistica": final.estadistica or None,
        "estadistica_antes": automatico.estadistica or None,
    }

    ejecucion.reporte = reporte
    ejecucion.estado = "confirmada"
    ejecucion.ruta_csv_limpio = ruta
    ejecucion.fecha_confirmacion = ahora.replace(tzinfo=None)
    ejecucion.fecha_actualizacion = ahora.replace(tzinfo=None)
    ejecucion.error = None
    _avanzar_estado(ctx.procesado, "limpio")
    # metadata-service y las descargas leen el archivo limpio desde aquí.
    ctx.procesado.ruta_de_archivo_limpio = ruta
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


# ── Vista para la interfaz ─────────────────────────────────────────────────────

# Métricas que se comparan antes y después de limpiar: (ruta en el dict, etiqueta, formato).
_COMPARABLES = (
    ("n_respondentes", "Respondentes", "num"),
    ("n_columnas", "Columnas", "num"),
    ("pct_completitud", "Completitud", "pct"),
    ("pct_nulos", "Celdas vacías", "pct"),
    ("n_duplicados", "Filas duplicadas", "num"),
    ("n_imposibles", "Valores fuera de rango", "num"),
    ("n_linea_recta", "Respuestas en línea recta", "num"),
    ("n_incompletos", "Encuestados incompletos", "num"),
    ("n_alumnos", "Alumnos", "num"),
    ("n_ids_duplicados", "IDs repetidos", "num"),
    ("conteos.nula", "Respuestas nulas", "num"),
    ("conteos.NR", "No respondidas", "num"),
    ("pct_correctas_validas", "Aciertos entre respuestas válidas", "pct"),
    ("kr20", "Fiabilidad KR-20", "dec"),
    ("n_turnos", "Turnos", "num"),
    ("n_palabras", "Palabras", "num"),
    ("ruido_detectado", "Ruido detectado", "num"),
)


def _valor(datos: dict[str, Any] | None, ruta: str) -> float | None:
    actual: Any = datos or {}
    for parte in ruta.split("."):
        actual = actual.get(parte) if isinstance(actual, dict) else None
    return actual if isinstance(actual, (int, float)) and not isinstance(actual, bool) else None


def comparacion(
    antes: dict[str, Any], despues: dict[str, Any], est_antes: dict[str, Any], est_despues: dict[str, Any]
) -> list[dict[str, Any]]:
    """Filas «métrica · antes · después» para la vista final (incluye el alfa por bloque)."""
    filas = []
    for ruta, etiqueta, formato in _COMPARABLES:
        a, d = _valor(antes, ruta), _valor(despues, ruta)
        if a is not None or d is not None:
            filas.append({"metrica": etiqueta, "antes": a, "despues": d, "formato": formato})
    # Alfa de Cronbach por bloque Likert (encuestas); en pruebas la fiabilidad es el KR-20 de arriba.
    def bloques(estadistica: dict[str, Any] | None) -> list[dict[str, Any]]:
        fiabilidad = (estadistica or {}).get("fiabilidad")
        return fiabilidad if isinstance(fiabilidad, list) else []

    alfa_antes = {b["bloque"]: b.get("alfa") for b in bloques(est_antes)}
    for bloque in bloques(est_despues):
        if bloque.get("alfa") is not None or alfa_antes.get(bloque["bloque"]) is not None:
            filas.append(
                {"metrica": f"Alfa de Cronbach · {bloque['bloque']}", "antes": alfa_antes.get(bloque["bloque"]), "despues": bloque.get("alfa"), "formato": "dec"}
            )
    return filas



def a_dto(ejecucion: LimpiezaEjecucion, tipo_instrumento: str) -> dict[str, Any]:
    """Vista derivada del reporte para la UI (nunca el reporte en crudo)."""
    reporte = ejecucion.reporte or {}
    decisiones = reporte.get("decisiones", {})

    def decision_del_investigador(hid: str) -> str | None:
        # Solo lo que eligió el investigador; las sugeridas se muestran como preselección.
        dec = decisiones.get(hid) or {}
        return dec.get("valor") if dec.get("origen") == "investigador" else None

    hallazgos = [dict(h, decision=decision_del_investigador(h["id"])) for h in reporte.get("hallazgos", [])]
    vista = reporte.get("vista_final") if ejecucion.estado == "confirmada" else None
    if vista and vista.get("estadistica"):
        # Se calcula al servirlo: así también lo tienen las limpiezas ya confirmadas.
        metricas = reporte.get("metricas") or {}
        vista = dict(vista, resumen=resumir(tipo_instrumento, vista["estadistica"], metricas.get("antes"), metricas.get("despues")))
    return {
        "idCrudo": ejecucion.id_crudo,
        "version": ejecucion.version,
        "estado": ejecucion.estado,
        "tipoInstrumento": tipo_instrumento,
        "fechaCreacion": ejecucion.fecha_creacion,
        "fechaActualizacion": ejecucion.fecha_actualizacion,
        "fechaConfirmacion": ejecucion.fecha_confirmacion,
        "error": ejecucion.error,
        "avisos": reporte.get("avisos", []),
        "metricasAntes": (reporte.get("metricas") or {}).get("antes") or {},
        "transformaciones": [
            {"regla": t.get("regla", ""), "detalle": t.get("detalle", ""), "afectados": t.get("afectados")}
            for t in reporte.get("transformaciones", [])
            if t.get("origen", "automatica") == "automatica"
        ],
        "hallazgos": hallazgos,
        "pendientesObligatorias": len(pendientes_obligatorias(reporte)),
        "vistaFinal": vista,
    }
