"""Modelo ORM: metadatos_enriquecidos_encuestas — hija de raw_data."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class MetadatosEnriquecidosEncuestas(Base):
    __tablename__ = "metadatos_enriquecidos_encuestas"
    __table_args__ = {"schema": SCHEMA}

    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        primary_key=True,
    )
    n_respondentes: Mapped[int | None] = mapped_column(Integer)
    n_poblacion: Mapped[int | None] = mapped_column(Integer)
    carrera: Mapped[str | None] = mapped_column(Text)
    poblacion_objetivo: Mapped[str | None] = mapped_column(Text)
    notas_contextuales: Mapped[str | None] = mapped_column(Text)
    notas_interpretacion: Mapped[str | None] = mapped_column(Text)
