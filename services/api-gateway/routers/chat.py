# app/routers/chat.py
"""
Router: Chat de IA (consulta RAG)

Responsable de esta pantalla: Arturo

TODO para quien desarrolle esta pantalla:
- Implementar POST /chat/consultar que reciba {pregunta, instrumento}
- Llamar al service de RAG para obtener la respuesta real
- Registrar la interacción en la tabla `rag_log` (PostgreSQL)
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["chat"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


class ConsultaRequest(BaseModel):
    pregunta: str
    instrumento: str  # "encuestas" | "entrevistas" | "pruebas_estandarizadas"


@router.get("/chat", response_class=HTMLResponse)
async def ver_chat_ia(request: Request):
    return templates.TemplateResponse(
        request, "pages/chat_ia/chat_ia.html", {"titulo": "Chat de IA"}
    )


@router.post("/chat/consultar")
async def consultar_rag(datos: ConsultaRequest):
    # TODO: reemplazar por llamada real al service de RAG
    return {
        "respuesta": f"[MOCKUP] Aquí iría la respuesta del RAG para: '{datos.pregunta}' "
                      f"sobre el instrumento '{datos.instrumento}'.",
        "chunks_recuperados": [],
    }