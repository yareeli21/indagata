"""Modelo ORM: grafo_investigacion — trazabilidad del grafo de recomendación.

Persiste el snapshot del grafo que un investigador armó (set activo +
recomendados mostrados) junto con los parámetros del score, para auditoría y
análisis de uso (RF-8 de la spec).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class GrafoInvestigacion(Base):
    __tablename__ = "grafo_investigacion"
    __table_args__ = {"schema": SCHEMA}

    grafo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investigacion_id: Mapped[str] = mapped_column(Text, nullable=False)
    id_owner: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="CASCADE")
    )
    instrumento_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    grafo_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parametros: Mapped[dict | None] = mapped_column(JSONB)
    fecha_creacion: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
