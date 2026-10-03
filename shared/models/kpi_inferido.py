"""Modelo ORM: kpi_inferido — KPIs inferidos por instrumento (PK compuesta)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KPIInferido(Base):
    __tablename__ = "kpi_inferido"
    __table_args__ = {"schema": SCHEMA}

    id_procesado: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.instrumento_procesado.id_instrumento", ondelete="CASCADE"),
        primary_key=True,
    )
    kpi_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.kpi.kpi_id", ondelete="CASCADE"),
        primary_key=True,
    )
    razon: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[float | None] = mapped_column(Numeric)
    fecha_inferencia: Mapped[datetime] = mapped_column(server_default=func.now())
