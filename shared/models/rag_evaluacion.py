"""Modelos ORM: rag_metrica_juez y rag_calificacion — evaluación de las respuestas del chat.

- `rag_metrica_juez`: una evaluación (fidelidad, relevancia, precisión del contexto) por respuesta y por modelo juez,
  para comparar jueces sobre las mismas respuestas (experimento redactor × juez). `rag_log.metricas` conserva la del
  juez por defecto, que es la que muestra la interfaz.
- `rag_calificacion`: la calificación humana de una respuesta (0 mal, 1 parcial, 2 bien), si entendió lo que se pidió
  y si fundamentó (NULL = no aplica).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class RagMetricaJuez(Base):
    __tablename__ = "rag_metrica_juez"
    __table_args__ = (UniqueConstraint("rag_log_id", "modelo_juez"), {"schema": SCHEMA})

    rag_metrica_juez_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rag_log_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.rag_log.rag_log_id", ondelete="CASCADE"), nullable=False)
    modelo_juez: Mapped[str] = mapped_column(String(100), nullable=False)
    metricas: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'"))
    version: Mapped[str | None] = mapped_column(String(10))
    fecha: Mapped[datetime | None] = mapped_column(server_default=func.now())


class RagCalificacion(Base):
    __tablename__ = "rag_calificacion"
    __table_args__ = (CheckConstraint("calificacion BETWEEN 0 AND 2"), {"schema": SCHEMA})

    rag_log_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.rag_log.rag_log_id", ondelete="CASCADE"), primary_key=True)
    calificacion: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    entendio: Mapped[bool | None] = mapped_column(Boolean)
    fundamenta: Mapped[bool | None] = mapped_column(Boolean)
    comentario: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="SET NULL"))
    fecha: Mapped[datetime | None] = mapped_column(server_default=func.now())
