"""Modelo ORM: usuario.

El rol determina quién puede subir y borrar instrumentos. La autorización la
valida la aplicación (no hay tabla de permisos).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str | None] = mapped_column(String(50))
    fecha_registro: Mapped[datetime] = mapped_column(server_default=func.now())
    # 2026_22: una cuenta desactivada no inicia sesión; 5 contraseñas incorrectas seguidas la bloquean 15 minutos.
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario id={self.usuario_id} nombre={self.nombre!r} rol={self.rol!r}>"
