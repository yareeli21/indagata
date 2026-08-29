# app/routers/instrumentos.py
"""
Router: Catálogo de instrumentos
Responsable de esta pantalla: Yare
"""
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.services.instrumento_service import obtener_instrumentos

router = APIRouter(tags=["instrumentos"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/instrumentos", response_class=HTMLResponse)
async def ver_catalogo_instrumentos(request: Request, db: Session = Depends(get_db)):
    instrumentos = obtener_instrumentos(db)
    return templates.TemplateResponse(
        request,
        "pages/catalogo_instrumentos/catalogo_instrumentos.html",
        {"titulo": "Catálogo de instrumentos", "instrumentos": instrumentos},
    )


@router.get("/instrumentos/buscar", response_class=HTMLResponse)
async def buscar_instrumentos(
    request: Request, tipo: str = Query("todos"), db: Session = Depends(get_db)
):
    """Devuelve solo el fragmento de la rejilla, para reemplazar vía fetch."""
    instrumentos = obtener_instrumentos(db, tipo)
    return templates.TemplateResponse(
        request,
        "pages/catalogo_instrumentos/_rejilla_instrumentos.html",
        {"instrumentos": instrumentos},
    )