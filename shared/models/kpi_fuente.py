"""Modelo ORM: kpi_fuente — fuentes de referencia verificadas de cada KPI.

Se cargan desde `infrastructure/postgres/seed/KPI_Fuentes.csv` (ligadas por el
nombre del KPI) con `services/analysis-service/scripts/seed_kpis.py`. Respaldan la
definición del catálogo en el chat y en la pantalla de KPIs.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KPIFuente(Base):
    __tablename__ = "kpi_fuente"
    __table_args__ = {"schema": SCHEMA}

    kpi_fuente_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.kpi.kpi_id", ondelete="CASCADE"), nullable=False)
    organismo: Mapped[str] = mapped_column(Text, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    anio: Mapped[int | None] = mapped_column(Integer)
    nota: Mapped[str | None] = mapped_column(Text)
