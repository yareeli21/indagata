"""Router RAG — POST /rag/index y POST /rag/chat (contrato estable con el frontend).

  POST /rag/index   asegura que los instrumentos de una investigación estén en el
                    RAG (la ingesta la hace el storage-service; los instrumentos sin
                    metadatos aprobados se reportan como omitidos).
  POST /rag/chat    responde fundamentado en los instrumentos de la investigación
                    (o en todo el acervo si no se indican), por SSE o JSON.
"""
from __future__ import annotations

from fastapi import APIRouter

from dependencies import Investigador
from models import ChatRequest, IndexRequest, IndexResponse
from services import rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/index", response_model=IndexResponse, summary="Asegurar la ingesta de instrumentos")
def indexar(peticion: IndexRequest, _: Investigador) -> IndexResponse:
    return IndexResponse(**rag_service.indexar(peticion))


@router.post("/chat", summary="Chat RAG fundamentado (SSE o JSON)")
async def chat(peticion: ChatRequest, _: Investigador):
    return await rag_service.responder(peticion)
