"""Schemas Pydantic: usuario.

Refleja 1:1 la tabla `tt_rag.usuario` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioBase(BaseModel):
    """Campos editables por el cliente al crear/actualizar un usuario."""

    nombre: str
    email: EmailStr
    rol: str | None = None


class UsuarioCreate(UsuarioBase):
    """Alta de usuario. La contraseña llega en claro y la app la hashea."""

    password: str


class UsuarioUpdate(BaseModel):
    """Actualización parcial: todos los campos opcionales."""

    nombre: str | None = None
    email: EmailStr | None = None
    rol: str | None = None
    password: str | None = None


class UsuarioRead(UsuarioBase):
    """Representación de salida. Nunca expone password_hash."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    fecha_registro: datetime | None = None
