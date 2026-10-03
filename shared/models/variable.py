"""Modelo ORM: variable."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class Variable(Base):
    __tablename__ = "variable"
    __table_args__ = {"schema": SCHEMA}

    variable_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_variable: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    tipo_dato: Mapped[str | None] = mapped_column(String(20))
    unidad: Mapped[str | None] = mapped_column(Text)
