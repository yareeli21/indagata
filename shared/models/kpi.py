"""Modelo ORM: kpi."""
from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KPI(Base):
    __tablename__ = "kpi"
    __table_args__ = {"schema": SCHEMA}

    kpi_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    polaridad_rendimiento: Mapped[str | None] = mapped_column(Text)
    tipo_objetivo_estrategico: Mapped[str | None] = mapped_column(Text)
    formula_metrica_calculo: Mapped[str | None] = mapped_column(Text)
    descripcion_ampliada_educativa: Mapped[str | None] = mapped_column(Text)
    comportamiento_direccional_causalidad: Mapped[str | None] = mapped_column(Text)
    razon_estrategica_decisiones: Mapped[str | None] = mapped_column(Text)
    texto_contexto_rag_vectorial: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KPI kpi_id={self.kpi_id} nombre={self.nombre!r}>"
