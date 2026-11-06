"""Tiempos del procesamiento de un instrumento, para la vista rápida del catálogo (Pruebas: duración).

Lee `tiempo_proceso` (lo escribe cada servicio con `shared.tiempos`) y la latencia de las respuestas del chat
(`rag_log.latencia_ms`) sobre ese instrumento. Distingue dos totales:
  - cómputo: la suma de los pasos, lo que tardaría la máquina sin esperas;
  - punta a punta: de la carga a la última operación, que incluye el tiempo que la persona tarda en decidir
    (y la indexación en segundo plano). Sirve para contrastar, no para estimar el servidor.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from shared.models.rag_log import RagLog
from shared.models.tiempo_proceso import TiempoProceso

ETIQUETAS = {
    "carga": "Carga y lectura del archivo",
    "limpieza_automatica": "Limpieza: fase automática",
    "limpieza_confirmar": "Limpieza: aplicar decisiones y guardar el CSV limpio",
    "propuesta_dublin_core": "Propuesta de Dublin Core",
    "propuesta_enriquecidos": "Propuesta de metadatos del tipo",
    "aprobacion": "Aprobación: JSON estandarizado",
    "indexacion_aprobacion": "Indexación al aprobar",
    "perfil": "Perfil semántico",
    "propuesta_kpis": "Propuesta de KPIs",
    "confirmar_kpis": "Confirmación de KPIs",
    "documento_final": "Documento final",
    "analisis_entrevista": "Análisis de respuestas de la entrevista",
    "publicacion": "Publicación del documento",
    "indexacion_rag": "Indexación al RAG",
}
SEGUNDO_PLANO = {"indexacion_rag", "analisis_entrevista"}
_MAX_CONSULTAS = 1000


def _percentil(valores: list[int], p: float) -> int | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p * (len(ordenados) - 1))))]


def tiempos(db: Session, id_crudo: int) -> dict[str, Any]:
    filas = db.query(TiempoProceso).filter(TiempoProceso.id_crudo == id_crudo).order_by(TiempoProceso.inicio).all()
    pasos = [{"paso": f.paso, "etiqueta": ETIQUETAS.get(f.paso, f.paso.replace("_", " ").capitalize()),
              "servicio": f.servicio, "inicio": f.inicio, "fin": f.fin, "duracion_ms": f.duracion_ms,
              "segundo_plano": f.paso in SEGUNDO_PLANO, "detalle": f.detalle or {}} for f in filas]
    punta = int((max(f.fin for f in filas) - min(f.inicio for f in filas)).total_seconds() * 1000) if filas else None
    # Latencia del chat sobre este instrumento (consultas recientes que lo tenían en el alcance).
    clave = str(id_crudo)
    latencias = [r.latencia_ms for r in db.query(RagLog).order_by(RagLog.rag_log_id.desc()).limit(_MAX_CONSULTAS)
                 if r.latencia_ms is not None and clave in [str(i) for i in (r.instrumentos or [])]]
    return {
        "id_crudo": id_crudo,
        "pasos": pasos,
        "computo_ms": sum(f.duracion_ms for f in filas),
        "punta_a_punta_ms": punta,
        "chat": {"consultas": len(latencias), "p50_ms": _percentil(latencias, 0.5), "p95_ms": _percentil(latencias, 0.95)},
    }
