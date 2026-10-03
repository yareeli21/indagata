"""Modelo ORM: kpi_inferido_chunk — puente con evidencia de la inferencia.

Registra qué chunks vectorizados sustentaron cada KPI inferido, con el score
de similitud de cada chunk. PK compuesta
(id_procesado, kpi_id, documento_vectorizado_id). FK compuesta
(id_procesado, kpi_id) -> kpi_inferido.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class KpiInferidoChunk(Base):
    __tablename__ = "kpi_inferido_chunk"
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
    documento_vectorizado_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.documento_vectorizado.documento_vectorizado_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    score: Mapped[float | None] = mapped_column(Numeric)
