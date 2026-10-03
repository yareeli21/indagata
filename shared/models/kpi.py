"""Modelo ORM: kpi."""
from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KPI(Base):
    __tablename__ = "kpi"
    __table_args__ = {"schema": SCHEMA}

    kpi_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_kpi: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(Text)
    ambito: Mapped[str | None] = mapped_column(Text)
    url_documentacion: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KPI kpi_id={self.kpi_id} nombre_kpi={self.nombre_kpi!r}>"
