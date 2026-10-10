"""Modelo ORM: kpi_calculo — resultado del cálculo real de un KPI para un instrumento."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import NUMERIC, TEXT, TIMESTAMP, CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KpiCalculo(Base):
    __tablename__ = "kpi_calculo"
    __table_args__ = (
        CheckConstraint("nivel_semaforo IN ('bueno','neutro','riesgo','informativo','sin_calculo')"),
        {"schema": SCHEMA},
    )
    kpi_calculo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_procesado: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA}.instrumento_procesado.id_instrumento", ondelete="CASCADE"), nullable=False)
    kpi_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA}.kpi.kpi_id", ondelete="CASCADE"), nullable=False)
    variables_input: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resultado_valor: Mapped[Decimal | None] = mapped_column(NUMERIC(12, 4))
    resultado_unidad: Mapped[str | None] = mapped_column(TEXT)
    referencia_valor: Mapped[Decimal | None] = mapped_column(NUMERIC(12, 4))
    referencia_contexto: Mapped[str | None] = mapped_column(TEXT)
    nivel_semaforo: Mapped[str | None] = mapped_column(TEXT)
    formula_usada: Mapped[str | None] = mapped_column(TEXT)
    calculado_por: Mapped[int | None] = mapped_column(Integer, ForeignKey(f"{SCHEMA}.usuario.usuario_id"))
    fecha_calculo: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
