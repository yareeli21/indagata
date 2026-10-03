"""Modelo ORM: documento_vectorizado — chunks vectorizados en Chroma."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class DocumentoVectorizado(Base):
    __tablename__ = "documento_vectorizado"
    __table_args__ = {"schema": SCHEMA}

    documento_vectorizado_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    instrumento_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.instrumento_procesado.id_instrumento", ondelete="CASCADE")
    )
    coleccion_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.coleccion_vectorial.coleccion_id", ondelete="SET NULL")
    )
    chroma_vector_id: Mapped[str | None] = mapped_column(Text)
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    seccion: Mapped[str | None] = mapped_column(Text)
    chunk_texto: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    n_tokens: Mapped[int | None] = mapped_column(Integer)
    almacenado_en: Mapped[datetime] = mapped_column(server_default=func.now())
