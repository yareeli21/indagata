"""Schemas Pydantic del módulo de autenticación y gestión de usuarios."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from shared.auth import ROL_INVESTIGADOR
from shared.schemas.usuario import UsuarioRead  # re-export conveniente

MIN_PASSWORD = 8


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token emitido tras un login exitoso."""

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioRead


class RegisterRequest(BaseModel):
    """Alta de un usuario (la ejecuta un administrador)."""

    nombre: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD)
    rol: str = Field(default=ROL_INVESTIGADOR, description="investigador | administrador")


class UsuarioAdmin(UsuarioRead):
    """Usuario en la lista del administrador: con su número de instrumentos y si está bloqueado."""

    instrumentos: int = 0
    bloqueado: bool = False


class ActualizarUsuarioRequest(BaseModel):
    """Cambios parciales que hace un administrador sobre una cuenta."""

    nombre: str | None = None
    rol: str | None = None
    activo: bool | None = None


class RestablecerPasswordRequest(BaseModel):
    password: str = Field(..., min_length=MIN_PASSWORD)


class CambiarPasswordRequest(BaseModel):
    actual: str
    nueva: str = Field(..., min_length=MIN_PASSWORD)


__all__ = ["LoginRequest", "TokenResponse", "RegisterRequest", "UsuarioRead", "UsuarioAdmin",
           "ActualizarUsuarioRequest", "RestablecerPasswordRequest", "CambiarPasswordRequest"]
