"""Modelo ORM: metadatos_dc — Dublin Core adaptado, hija de raw_data."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class MetadatosDC(Base):
    __tablename__ = "metadatos_dc"
    __table_args__ = {"schema": SCHEMA}

    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        primary_key=True,
    )
    dc_title: Mapped[str] = mapped_column(Text, nullable=False)
    dc_creator: Mapped[str | None] = mapped_column(Text)
    dc_description: Mapped[str | None] = mapped_column(Text)
    dc_type: Mapped[str | None] = mapped_column(String(50))
    dc_date: Mapped[str | None] = mapped_column(String(100))
    dc_language: Mapped[str | None] = mapped_column(String(10))
    dc_coverage: Mapped[str | None] = mapped_column(Text)
    dc_subject: Mapped[str | None] = mapped_column(Text)
    dc_publisher: Mapped[str | None] = mapped_column(Text)
    dc_rights: Mapped[str | None] = mapped_column(String(255))
    dc_format: Mapped[str | None] = mapped_column(String(50))
    dc_source: Mapped[str | None] = mapped_column(Text)
    dc_relation: Mapped[str | None] = mapped_column(Text)
