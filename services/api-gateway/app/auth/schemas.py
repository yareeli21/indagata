"""Schemas Pydantic del módulo de autenticación."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from shared.auth import ROL_INVESTIGADOR
from shared.schemas.usuario import UsuarioRead  # re-export conveniente


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
    password: str = Field(..., min_length=6)
    rol: str = Field(default=ROL_INVESTIGADOR, description="investigador | administrador")


__all__ = ["LoginRequest", "TokenResponse", "RegisterRequest", "UsuarioRead"]
