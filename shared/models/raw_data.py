"""Modelo ORM: raw_data — tabla PADRE del pipeline.

Un registro por instrumento recibido en crudo. Guarda el archivo respondido
(raw_archivo) y el instrumento original sin respuestas (raw_archivo_original).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class RawData(Base):
    __tablename__ = "raw_data"
    __table_args__ = {"schema": SCHEMA}

    id_crudo: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_owner: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_instrumento: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    raw_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    raw_archivo_original: Mapped[str | None] = mapped_column(Text)
    fecha_carga: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RawData id_crudo={self.id_crudo} tipo={self.tipo_instrumento!r}>"
