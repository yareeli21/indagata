# app/routers/login.py
"""
Router: Login
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.services.login_service import autenticar_usuario

router = APIRouter(tags=["login"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def ver_login(request: Request):
    return templates.TemplateResponse(
        request, "pages/login/login.html", {"titulo": "Iniciar sesión"}
    )


@router.post("/login", response_class=HTMLResponse)
async def procesar_login(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario_autenticado = autenticar_usuario(db, usuario, password)

    if not usuario_autenticado:
        return templates.TemplateResponse(
            request,
            "pages/login/login.html",
            {"titulo": "Iniciar sesión", "error": "Usuario o contraseña incorrectos"},
        )

    response = RedirectResponse(url="/kpis", status_code=303)
    response.set_cookie(
        key="usuario_id",
        value=str(usuario_autenticado.usuario_id),
        httponly=True,
        max_age=3600,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def cerrar_sesion():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("usuario_id")
    return response