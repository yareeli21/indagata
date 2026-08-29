# app/routers/kpis.py
"""
Router: Catálogo de KPIs
Responsable de esta pantalla: Layla Hernández
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.services.kpi_service import obtener_todos_los_kpis

router = APIRouter(tags=["kpis"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/kpis", response_class=HTMLResponse)
async def ver_catalogo_kpis(request: Request, db: Session = Depends(get_db)):
    kpis = obtener_todos_los_kpis(db)
    return templates.TemplateResponse(
        request,
        "pages/catalogo_kpis/catalogo_kpis.html",
        {"titulo": "Catálogo de KPIs", "kpis": kpis},
    )