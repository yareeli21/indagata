# app/routers/login.py
"""
Router: Login
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from core.config import settings
from db.database import get_db
from services.login_service import autenticar_usuario, UserService
from schemas.schemas_login import LoginCreate

router = APIRouter(tags=["login"])

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# main.py is in backend, __file__ is in backend/routers, so parent.parent is backend. Wait, parent is backend, parent.parent is indagata.
# Let's fix that:
BASE_DIR_BACKEND = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR_BACKEND.parent / "frontend" / "landing" / "templates"))

# --- Schemas para APIs ---
class LoginRequest(BaseModel):
    usuario: str
    password: str

class ForgotPasswordRequest(BaseModel):
    correo: EmailStr
    nueva_password: str

# --- Endpoints HTML (Plantillas) ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def ver_login(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"titulo": "Iniciar sesión"}
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
            request=request,
            name="index.html",
            context={"titulo": "Iniciar sesión", "error": "Usuario o contraseña incorrectos"},
        )

    response = RedirectResponse(url="/home", status_code=303)
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

# --- Endpoints JSON (Para React/Fetch) ---

@router.post("/api/register")
async def api_register(user_in: LoginCreate, db: Session = Depends(get_db)):
    nuevo_usuario = UserService.create_new_user(db, user_in)
    return {"message": "Usuario registrado exitosamente", "usuario_id": nuevo_usuario.usuario_id}

@router.post("/api/login")
async def api_login(user_in: LoginRequest, db: Session = Depends(get_db)):
    usuario_autenticado = autenticar_usuario(db, user_in.usuario, user_in.password)
    if not usuario_autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    return {
        "message": "Login exitoso",
        "usuario_id": usuario_autenticado.usuario_id,
        "usuario": usuario_autenticado.usuario
    }

@router.post("/api/forgot-password")
async def api_forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    usuario = UserService.reset_password(db, req.correo, req.nueva_password)
    return {"message": "Contraseña actualizada exitosamente", "usuario_id": usuario.usuario_id}