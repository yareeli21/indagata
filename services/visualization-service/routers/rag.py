"""Router RAG — POST /rag/index y POST /rag/chat (contrato estable con el frontend).

  POST /rag/index   asegura que los instrumentos de una investigación estén en el
                    RAG (la ingesta la hace el storage-service; los instrumentos sin
                    metadatos aprobados se reportan como omitidos).
  POST /rag/chat    responde fundamentado en los instrumentos de la investigación
                    (o en todo el acervo si no se indican), por SSE o JSON.
  GET  /rag/consultas/{id}/metricas   métricas automáticas de una respuesta (se
                    calculan en segundo plano: «calculando» → «listo»).
  GET  /rag/consultas/{id}            pregunta, respuesta, contexto usado y métricas
                    (para la evaluación fuera de línea, tools/rag/evaluar_ragas.py).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from dependencies import DBSession, Investigador
from models import ChatRequest, IndexRequest, IndexResponse, MetricasConsultaOut
from services import evaluacion, rag_service
from shared.models.rag_log import RagLog

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/index", response_model=IndexResponse, summary="Asegurar la ingesta de instrumentos")
def indexar(peticion: IndexRequest, _: Investigador) -> IndexResponse:
    return IndexResponse(**rag_service.indexar(peticion))


@router.post("/chat", summary="Chat RAG fundamentado (SSE o JSON)")
async def chat(peticion: ChatRequest, _: Investigador):
    return await rag_service.responder(peticion)


def _consulta(db, consulta_id: int) -> RagLog:  # noqa: ANN001
    fila = db.get(RagLog, consulta_id)
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consulta no encontrada.")
    return fila


def _metricas(db, fila: RagLog) -> dict:  # noqa: ANN001
    """Métricas públicas; una respuesta reutilizada de la caché muestra las de la original."""
    origen = (fila.metricas or {}).get("origen")
    original = db.get(RagLog, origen) if origen else None
    datos = evaluacion.estado_publico(original or fila)
    datos["consultaId"] = fila.rag_log_id
    return datos


@router.get("/consultas/{consulta_id}/metricas", response_model=MetricasConsultaOut, summary="Métricas automáticas de una respuesta")
def metricas(consulta_id: int, _: Investigador, db: DBSession) -> MetricasConsultaOut:
    return MetricasConsultaOut(**_metricas(db, _consulta(db, consulta_id)))


@router.get("/consultas/{consulta_id}", summary="Consulta registrada: respuesta, contexto usado y métricas")
def consulta(consulta_id: int, _: Investigador, db: DBSession) -> dict:
    fila = _consulta(db, consulta_id)
    return {"consultaId": fila.rag_log_id, "pregunta": fila.pregunta, "respuesta": fila.respuesta,
            "decision": fila.decision_dominio, "ruta": fila.ruta, "motivo": fila.motivo,
            "contexto": fila.contexto_usado or [], "metricas": _metricas(db, fila)}
