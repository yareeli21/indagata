"""Modelo ORM: prompts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class Prompt(Base):
    __tablename__ = "prompts"
    __table_args__ = {"schema": SCHEMA}

    prompt_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    coleccion_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.coleccion_vectorial.coleccion_id", ondelete="SET NULL")
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
