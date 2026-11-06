"""Casos de uso del análisis de respuestas de entrevista (sobre el documento final en borrador).

    POST  analizar   → corre en segundo plano: una llamada al LLM por intercambio
    GET   leer       → avance y análisis de cada intercambio
    PATCH corregir   → el investigador corrige unidades, postura o motivo («revisado»)

El análisis se guarda DENTRO del documento final (`intercambios[].analisis`, esquema 2.1):
cada guardado es una versión nueva del artefacto en storage-service y la fila de
`version_conocimiento` apunta a la última. Lo `revisado` nunca se vuelve a analizar.
El avance vive en memoria del proceso (un solo trabajador por instrumento).
"""
from __future__ import annotations

import logging
import time
import threading
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status
from shared import tiempos
from sqlalchemy.orm import Session

from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

from services import documento, fuentes, ollama, storage_client, versiones
from services.documento import analisis_entrevista as ae

logger = logging.getLogger("knowledge-service")
ESQUEMA_CON_ANALISIS = "2.1"
_GUARDAR_CADA = 20
_avance: dict[int, dict[str, Any]] = {}
_lock = threading.Lock()


def _borrador(db: Session, usuario: Usuario, id_crudo: int) -> tuple[VersionConocimiento, dict[str, Any]]:
    ctx = fuentes.cargar(db, usuario, id_crudo)
    if ctx.tipo != "entrevista":
        raise HTTPException(status.HTTP_409_CONFLICT, "El análisis de respuestas solo aplica a entrevistas.")
    fila = versiones.actual(db, id_crudo)
    if fila is None or fila.estado != "borrador" or not fila.ruta_documento:
        raise HTTPException(status.HTTP_409_CONFLICT, "Genera el documento final (borrador) antes de analizar las respuestas.")
    try:
        return fila, storage_client.descargar_json(fila.ruta_documento)
    except storage_client.StorageError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo leer el documento final: {exc}") from exc


def _guardar(db: Session, fila: VersionConocimiento, doc: dict[str, Any]) -> None:
    doc["esquema_version"] = ESQUEMA_CON_ANALISIS
    documento.validar(doc)
    ref = storage_client.guardar_json(fila.id_crudo, "documento", doc, f"v{fila.version}_documento_final")
    fila.ruta_documento, fila.sha256, fila.esquema_version = ref["key"], ref.get("sha256"), ESQUEMA_CON_ANALISIS
    db.commit()


def _intercambios(doc: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    return [(e["participante"], n, i) for e in doc.get("entrevistas") or [] for n, i in enumerate(e.get("intercambios") or [], start=1)]


def iniciar(db: Session, usuario: Usuario, id_crudo: int) -> dict[str, Any]:
    _, doc = _borrador(db, usuario, id_crudo)
    with _lock:
        if (_avance.get(id_crudo) or {}).get("estado") == "en_curso":
            return {**_avance[id_crudo], "nuevo": False}
        pendientes = sum(1 for *_, i in _intercambios(doc) if (i.get("analisis") or {}).get("estado") != "revisado")
        _avance[id_crudo] = {"estado": "en_curso", "hechos": 0, "total": pendientes}
        return {**_avance[id_crudo], "nuevo": True}


def correr(fabrica: Callable[[], Session], id_crudo: int, llm: Callable[[str], Any] | None = None) -> None:
    """Analiza en segundo plano los intercambios no revisados y guarda el documento."""
    llm = llm or ollama.generar_json  # se resuelve al ejecutar (las pruebas lo sustituyen)
    db = fabrica()
    inicio, t0 = tiempos._ahora(), time.perf_counter()
    try:
        fila = versiones.actual(db, id_crudo)
        doc = storage_client.descargar_json(fila.ruta_documento)
        hechos = 0
        for _, _, i in _intercambios(doc):
            if (i.get("analisis") or {}).get("estado") == "revisado":
                continue
            i["analisis"] = ae.analizar(i.get("pregunta") or "", i.get("respuesta") or "", llm)
            hechos += 1
            with _lock:
                _avance[id_crudo]["hechos"] = hechos
            if hechos % _GUARDAR_CADA == 0:
                _guardar(db, fila, doc)
        _guardar(db, fila, doc)
        with _lock:
            _avance[id_crudo]["estado"] = "listo"
        tiempos.registrar(db, id_crudo, "knowledge", "analisis_entrevista", inicio, tiempos._ahora(),
                          round((time.perf_counter() - t0) * 1000), {"respuestas_analizadas": hechos})
    except Exception as exc:  # noqa: BLE001 — se informa en el avance; el documento previo sigue válido
        logger.exception("Análisis de entrevista falló para id_crudo=%s", id_crudo)
        with _lock:
            _avance[id_crudo] = {**_avance.get(id_crudo, {}), "estado": "error", "mensaje": str(exc)[:300]}
    finally:
        db.close()


def leer(db: Session, usuario: Usuario, id_crudo: int) -> dict[str, Any]:
    fila, doc = _borrador(db, usuario, id_crudo)
    lista = [{"participante": p, "n": n, "pregunta_id": i.get("pregunta_id"), "pregunta": i.get("pregunta"),
              "respuesta": i.get("respuesta"), "analisis": i.get("analisis")} for p, n, i in _intercambios(doc)]
    con = [x for x in lista if x["analisis"]]
    with _lock:
        avance = dict(_avance.get(id_crudo) or {"estado": "listo" if con else "sin_analisis", "hechos": len(con), "total": len(lista)})
    return {**avance, "version": fila.version, "revisados": sum(1 for x in con if x["analisis"].get("estado") == "revisado"),
            "intercambios": lista}


def corregir(db: Session, usuario: Usuario, id_crudo: int, participante: str, n: int, cambios: dict[str, Any]) -> dict[str, Any]:
    fila, doc = _borrador(db, usuario, id_crudo)
    objetivo = next(((p, k, i) for p, k, i in _intercambios(doc)
                     if k == n and (p == participante or p.endswith(f"-{participante}"))), None)
    if objetivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el intercambio {n} de {participante}.")
    _, _, i = objetivo
    an = i.get("analisis") or ae.analizar_reglas(i.get("pregunta") or "", i.get("respuesta") or "")
    if (unidades := cambios.get("unidades")) is not None:
        base = ae._norm(i.get("respuesta") or "")
        for u in unidades:
            if ae._norm(u.get("texto") or "") not in base:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"El fragmento «{u.get('texto')}» no está en la respuesta.")
            if u.get("marco_temporal") not in ae.MARCOS or u.get("funcion") not in ae.FUNCIONES or u.get("postura") not in ae.POSTURAS:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Marco, función o postura no válidos.")
        an["unidades"] = [{k: u[k] for k in ("texto", "marco_temporal", "funcion", "postura")} for u in unidades]
        an["nucleo"] = ae._nucleo(an["unidades"])
    if (postura := cambios.get("postura")) is not None:
        if postura not in (*ae.POSTURAS, "sin_determinar"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Postura no válida.")
        an["postura"] = postura
    if (motivo := cambios.get("motivo")) is not None:
        an["motivo"] = " ".join(str(motivo).split())
    an["estado"] = "revisado"
    i["analisis"] = an
    _guardar(db, fila, doc)
    return {"participante": objetivo[0], "n": n, "analisis": an}
