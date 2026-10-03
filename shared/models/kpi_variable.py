"""Modelo ORM: kpi_variable — relación N:M entre KPI y variable."""
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KPIVariable(Base):
    __tablename__ = "kpi_variable"
    __table_args__ = {"schema": SCHEMA}

    kpi_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.kpi.kpi_id", ondelete="CASCADE"), primary_key=True
    )
    variable_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.variable.variable_id", ondelete="CASCADE"),
        primary_key=True,
    )
