"""Modelo ORM: rag_log — registro de consultas RAG."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class RagLog(Base):
    __tablename__ = "rag_log"
    __table_args__ = {"schema": SCHEMA}

    rag_log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pregunta: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta: Mapped[str | None] = mapped_column(Text)
    modelo_usado: Mapped[str | None] = mapped_column(String(100))
    chunks_usados: Mapped[int | None] = mapped_column(Integer)
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column("timestamp", server_default=func.now())
