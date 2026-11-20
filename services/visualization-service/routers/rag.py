"""Router RAG — POST /rag/index y POST /rag/chat (contrato estable con el frontend).

  POST /rag/index   asegura que los instrumentos de una investigación estén en el
                    RAG (la ingesta la hace el storage-service; los instrumentos sin
                    metadatos aprobados se reportan como omitidos).
  POST /rag/chat    responde fundamentado en los instrumentos de la investigación
                    (o en todo el acervo si no se indican), por SSE o JSON.
  POST /rag/interpretar  plan JSON que la etapa de interpretación arma para una pregunta y su resultado
                    calculado (etapas 1 y 2, sin redacción), para revisar y depurar.
  GET  /rag/consultas/{id}/metricas   métricas automáticas de una respuesta («pendiente» →
                    «calculando» → «listo» o «calculada»).
  POST /rag/consultas/{id}/metricas   pide calcularlas (bajo demanda: solo cuando la persona abre la
                    evaluación, para no recargar el modelo después de cada pregunta); `?juez=<modelo>` las calcula
                    con otro juez (experimento redactor × juez); `?juez=claude-fable-5-2` vuelve a evaluarla con el juez
                    Fable (que ya evalúa cada respuesta en segundo plano, services/juez_fable.py).
  PUT  /rag/consultas/{id}/calificacion  calificación humana de una respuesta (0 mal, 1 parcial, 2 bien).
  GET  /rag/consultas/{id}            pregunta, respuesta, contexto usado y métricas
                    (para la evaluación fuera de línea, tools/rag/evaluar_ragas.py).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import DBSession, Investigador
from models import (CalificacionIn, CalificacionOut, ChatRequest, IndexRequest, IndexResponse, InterpretarOut,
                    MetricasConsultaOut)
from services import ejecutor, evaluacion, indicadores, interpretacion, juez_fable, rag_service
from services.catalogo import construir as construir_catalogo
from services.enrutador import cargar_documentos
from shared.models.rag_evaluacion import RagCalificacion
from shared.models.rag_log import RagLog

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/index", response_model=IndexResponse, summary="Asegurar la ingesta de instrumentos")
def indexar(peticion: IndexRequest, _: Investigador) -> IndexResponse:
    return IndexResponse(**rag_service.indexar(peticion))


@router.post("/chat", summary="Chat RAG fundamentado (SSE o JSON)")
async def chat(peticion: ChatRequest, _: Investigador):
    return await rag_service.responder(peticion)


@router.post("/interpretar", response_model=InterpretarOut, summary="Plan de interpretación de una pregunta")
async def interpretar(peticion: ChatRequest, _: Investigador, db: DBSession) -> InterpretarOut:
    """Etapa 1 del chat por separado: el plan que el LLM arma para la pregunta, validado contra el catálogo."""
    instrumentos = cargar_documentos(db, peticion.instrumentoIds)
    catalogos = [construir_catalogo(i.id_crudo, i.titulo, i.tipo, i.doc) for i in instrumentos]
    r = await interpretacion.interpretar(peticion.pregunta, [(m.rol, m.texto) for m in peticion.historial], catalogos)
    inicio = time.perf_counter()
    resultados = ejecutor.ejecutar(r.plan, instrumentos, ejecutor.fiabilidad_de(db, instrumentos)) if r.plan else []
    return InterpretarOut(plan=r.plan.model_dump(exclude_defaults=True) if r.plan else None, correcciones=r.correcciones,
                          intentos=r.intentos, ms=r.ms, error=r.error, ejecucion=[e.texto() for e in resultados],
                          ms_ejecucion=round((time.perf_counter() - inicio) * 1000))


def _consulta(db, consulta_id: int) -> RagLog:  # noqa: ANN001
    fila = db.get(RagLog, consulta_id)
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consulta no encontrada.")
    return fila


def _metricas(db, fila: RagLog) -> dict:  # noqa: ANN001
    """Métricas públicas, indicadores sin juez, evaluaciones por juez y calificación humana; una respuesta
    reutilizada de la caché muestra las métricas e indicadores de la original (la calificación es de cada fila)."""
    origen = (fila.metricas or {}).get("origen")
    original = (db.get(RagLog, origen) if origen else None) or fila
    datos = evaluacion.estado_publico(original)
    datos["consultaId"] = fila.rag_log_id
    datos["indicadores"] = indicadores.calcular(original)
    datos["jueces"] = evaluacion.jueces_de(db, original.rag_log_id)
    datos["juezFable"] = juez_fable.estado_publico(db, original.rag_log_id)
    calificacion = db.get(RagCalificacion, fila.rag_log_id)
    datos["calificacion"] = None if calificacion is None else {
        "calificacion": calificacion.calificacion, "entendio": calificacion.entendio,
        "fundamenta": calificacion.fundamenta, "comentario": calificacion.comentario, "fecha": calificacion.fecha}
    return datos


@router.get("/consultas/{consulta_id}/metricas", response_model=MetricasConsultaOut, summary="Métricas automáticas de una respuesta")
def metricas(consulta_id: int, _: Investigador, db: DBSession) -> MetricasConsultaOut:
    return MetricasConsultaOut(**_metricas(db, _consulta(db, consulta_id)))


@router.post("/consultas/{consulta_id}/metricas", response_model=MetricasConsultaOut, summary="Calcular las métricas de una respuesta")
async def calcular_metricas(
    consulta_id: int, _: Investigador, db: DBSession,
    juez: str | None = Query(default=None, max_length=100, description="Modelo juez; vacío = el juez por defecto"),
) -> MetricasConsultaOut:
    """Bajo demanda: pone a calcular las métricas de una respuesta pendiente (o de la original, si vino de la caché).

    Con `juez`, las calcula ese modelo y quedan en `rag_metrica_juez` (las del juez por defecto se muestran arriba en
    el panel; las de los demás, en la tabla por juez).
    """
    fila = _consulta(db, consulta_id)
    origen = (fila.metricas or {}).get("origen")
    objetivo = (db.get(RagLog, origen) if origen else None) or fila
    juez = (juez or "").strip() or None
    if juez == juez_fable.modelo():
        # El juez Fable ya evalúa cada respuesta solo; pedirlo vuelve a evaluarla (p. ej., tras configurar la clave).
        if (objetivo.metricas or {}).get("estado") != evaluacion.OMITIDA:
            juez_fable.solicitar(objetivo, db, rag_service.fabrica_sesiones, forzar=True)
    else:
        evaluacion.solicitar(objetivo, db, rag_service.fabrica_sesiones, juez)
    return MetricasConsultaOut(**_metricas(db, fila))


@router.put("/consultas/{consulta_id}/calificacion", response_model=CalificacionOut,
            summary="Calificación humana de una respuesta")
def calificar(consulta_id: int, datos: CalificacionIn, usuario: Investigador, db: DBSession) -> CalificacionOut:
    """Guarda (o reemplaza) la calificación humana: 0 mal, 1 parcial, 2 bien; si entendió y si fundamentó."""
    _consulta(db, consulta_id)
    fila = db.get(RagCalificacion, consulta_id) or RagCalificacion(rag_log_id=consulta_id)
    fila.calificacion, fila.entendio, fila.fundamenta = datos.calificacion, datos.entendio, datos.fundamenta
    fila.comentario = (datos.comentario or "").strip() or None
    fila.usuario_id = usuario.usuario_id
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return CalificacionOut(calificacion=fila.calificacion, entendio=fila.entendio, fundamenta=fila.fundamenta,
                           comentario=fila.comentario, fecha=fila.fecha)


@router.get("/consultas/{consulta_id}", summary="Consulta registrada: respuesta, contexto usado y métricas")
def consulta(consulta_id: int, _: Investigador, db: DBSession) -> dict:
    fila = _consulta(db, consulta_id)
    return {"consultaId": fila.rag_log_id, "pregunta": fila.pregunta, "respuesta": fila.respuesta,
            "decision": fila.decision_dominio, "ruta": fila.ruta, "motivo": fila.motivo,
            "contexto": fila.contexto_usado or [], "metricas": _metricas(db, fila),
            "plan": fila.plan, "tiempos": fila.tiempos, "latenciaMs": fila.latencia_ms}
