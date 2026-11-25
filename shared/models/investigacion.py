"""Modelo ORM: investigacion — las investigaciones de cada usuario y su conversación (2026_23).

Antes vivían solo en el navegador; ahora se guardan aquí para verlas desde cualquier dispositivo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class Investigacion(Base):
    __tablename__ = "investigacion"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    instrumentos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    sesion: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actualizada: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
