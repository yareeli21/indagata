"""Modelo ORM: usuario.

El rol determina quién puede subir y borrar instrumentos. La autorización la
valida la aplicación (no hay tabla de permisos).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
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

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario id={self.usuario_id} nombre={self.nombre!r} rol={self.rol!r}>"
