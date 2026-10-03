"""Modelo ORM: coleccion_vectorial — configuración de colección Chroma.

Una colección por configuración de embedding. La referencian prompts y
documento_vectorizado.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class ColeccionVectorial(Base):
    __tablename__ = "coleccion_vectorial"
    __table_args__ = {"schema": SCHEMA}

    coleccion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    chunk_size: Mapped[int | None] = mapped_column(Integer)
    chunk_overlap: Mapped[int | None] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
