"""Router — AUTENTICACIÓN (login JWT, usuario actual, alta de usuarios).

  POST /auth/login     → email + password → JWT firmado.
  GET  /auth/me        → datos del usuario del token.
  POST /auth/register  → alta de usuario (SOLO administrador).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.auth import service
from app.auth.dependencies import DBSession, UsuarioActual, require_rol
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from shared.auth import ROL_ADMINISTRADOR, crear_access_token
from shared.models.usuario import Usuario
from shared.schemas.usuario import UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión (email + password) y obtener un JWT",
)
def login(datos: LoginRequest, db: DBSession) -> TokenResponse:
    usuario = service.autenticar(db, datos.email, datos.password)
    token = crear_access_token(usuario_id=usuario.usuario_id, rol=usuario.rol)
    return TokenResponse(access_token=token, usuario=UsuarioRead.model_validate(usuario))


@router.get(
    "/me",
    response_model=UsuarioRead,
    summary="Datos del usuario autenticado (según el token)",
)
def me(usuario_actual: UsuarioActual) -> UsuarioRead:
    return UsuarioRead.model_validate(usuario_actual)


@router.post(
    "/register",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de usuario (solo administrador)",
    description=(
        "Crea una cuenta de investigador o administrador. Requiere un token de "
        "**administrador**. La contraseña se hashea con bcrypt."
    ),
)
def register(
    datos: RegisterRequest,
    db: DBSession,
    _admin: Annotated[Usuario, Depends(require_rol(ROL_ADMINISTRADOR))],
) -> UsuarioRead:
    usuario = service.registrar_usuario(db, datos)
    return UsuarioRead.model_validate(usuario)
