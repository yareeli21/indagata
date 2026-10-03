"""Modelo ORM: valor_variable_inferido — valores inferidos por variable.

PK compuesta (id_procesado, kpi_id, variable_id). FK compuesta
(id_procesado, kpi_id) -> kpi_inferido.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class ValorVariableInferido(Base):
    __tablename__ = "valor_variable_inferido"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_procesado", "kpi_id"],
            [
                f"{SCHEMA}.kpi_inferido.id_procesado",
                f"{SCHEMA}.kpi_inferido.kpi_id",
            ],
            ondelete="CASCADE",
        ),
        {"schema": SCHEMA},
    )

    id_procesado: Mapped[int] = mapped_column(primary_key=True)
    kpi_id: Mapped[int] = mapped_column(primary_key=True)
    variable_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.variable.variable_id", ondelete="CASCADE"),
        primary_key=True,
    )
    valor_numerico: Mapped[float | None] = mapped_column(Numeric)
    valor_texto: Mapped[str | None] = mapped_column(Text)
    valor_booleano: Mapped[bool | None] = mapped_column(Boolean)
    confianza_variable: Mapped[float | None] = mapped_column(Numeric)
