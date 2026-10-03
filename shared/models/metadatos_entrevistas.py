"""Modelo ORM: metadatos_enriquecidos_entrevistas — hija de raw_data."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class MetadatosEnriquecidosEntrevistas(Base):
    __tablename__ = "metadatos_enriquecidos_entrevistas"
    __table_args__ = {"schema": SCHEMA}

    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        primary_key=True,
    )
    identificador_propio: Mapped[str | None] = mapped_column(Text)
    objetivo: Mapped[str | None] = mapped_column(Text)
    metodologia: Mapped[str | None] = mapped_column(Text)
    institucion: Mapped[str | None] = mapped_column(Text)
    derechos: Mapped[str | None] = mapped_column(Text)
