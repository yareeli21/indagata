"""Router — AUTENTICACIÓN y GESTIÓN DE USUARIOS.

  POST   /auth/login                        → email + password → JWT (bloqueo tras 5 intentos fallidos).
  GET    /auth/me                           → datos del usuario del token.
  POST   /auth/me/password                  → cambiar la propia contraseña (pide la actual).
  POST   /auth/register                     → alta de usuario (SOLO administrador).
  GET    /auth/usuarios                     → lista de usuarios con sus instrumentos (SOLO administrador).
  PATCH  /auth/usuarios/{id}                → nombre, rol o activo (SOLO administrador).
  POST   /auth/usuarios/{id}/password       → restablecer contraseña (SOLO administrador).
  DELETE /auth/usuarios/{id}                → eliminar una cuenta sin instrumentos (SOLO administrador).
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.auth import service
from app.auth.dependencies import DBSession, UsuarioActual, require_rol
from app.auth.schemas import (
    ActualizarUsuarioRequest,
    CambiarPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RestablecerPasswordRequest,
    TokenResponse,
    UsuarioAdmin,
)
from shared.auth import ROL_ADMINISTRADOR, crear_access_token
from shared.models.usuario import Usuario
from shared.schemas.usuario import UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])
Administrador = Annotated[Usuario, Depends(require_rol(ROL_ADMINISTRADOR))]


def _admin_out(usuario: Usuario, instrumentos: dict[int, int]) -> UsuarioAdmin:
    return UsuarioAdmin(**UsuarioRead.model_validate(usuario).model_dump(),
                        instrumentos=instrumentos.get(usuario.usuario_id, 0),
                        bloqueado=bool(usuario.bloqueado_hasta and usuario.bloqueado_hasta > datetime.now()))


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión (email + password) y obtener un JWT")
def login(datos: LoginRequest, db: DBSession) -> TokenResponse:
    usuario = service.autenticar(db, datos.email, datos.password)
    token = crear_access_token(usuario_id=usuario.usuario_id, rol=usuario.rol)
    return TokenResponse(access_token=token, usuario=UsuarioRead.model_validate(usuario))


@router.get("/me", response_model=UsuarioRead, summary="Datos del usuario autenticado (según el token)")
def me(usuario_actual: UsuarioActual) -> UsuarioRead:
    return UsuarioRead.model_validate(usuario_actual)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Cambiar mi contraseña")
def cambiar_mi_password(datos: CambiarPasswordRequest, db: DBSession, usuario_actual: UsuarioActual) -> Response:
    service.cambiar_mi_password(db, usuario_actual, datos.actual, datos.nueva)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED,
             summary="Alta de usuario (solo administrador)",
             description="Crea una cuenta de investigador o administrador. La contraseña se hashea con bcrypt.")
def register(datos: RegisterRequest, db: DBSession, _admin: Administrador) -> UsuarioRead:
    return UsuarioRead.model_validate(service.registrar_usuario(db, datos))


@router.get("/usuarios", response_model=list[UsuarioAdmin], summary="Lista de usuarios (solo administrador)")
def listar_usuarios(db: DBSession, _admin: Administrador) -> list[UsuarioAdmin]:
    instrumentos = service.instrumentos_por_usuario(db)
    return [_admin_out(u, instrumentos) for u in service.listar(db)]


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioAdmin, summary="Editar un usuario (solo administrador)")
def actualizar_usuario(usuario_id: int, datos: ActualizarUsuarioRequest, db: DBSession,
                       admin: Administrador) -> UsuarioAdmin:
    usuario = service.actualizar(db, usuario_id, datos, admin)
    return _admin_out(usuario, service.instrumentos_por_usuario(db))


@router.post("/usuarios/{usuario_id}/password", response_model=UsuarioAdmin,
             summary="Restablecer la contraseña de un usuario (solo administrador)")
def restablecer_password(usuario_id: int, datos: RestablecerPasswordRequest, db: DBSession,
                         _admin: Administrador) -> UsuarioAdmin:
    usuario = service.restablecer_password(db, usuario_id, datos.password)
    return _admin_out(usuario, service.instrumentos_por_usuario(db))


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar una cuenta sin instrumentos (solo administrador)")
def eliminar_usuario(usuario_id: int, db: DBSession, admin: Administrador) -> Response:
    service.eliminar(db, usuario_id, admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
