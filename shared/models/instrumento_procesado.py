"""Modelo ORM: instrumento_procesado — hija de raw_data por id_crudo.

PK propia (id_instrumento) para que las tablas de KPIs y vectorización puedan
relacionarse con ella.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class InstrumentoProcesado(Base):
    __tablename__ = "instrumento_procesado"
    __table_args__ = (
        CheckConstraint(
            "estado IN ("
            "'recibido',"
            "'limpieza_en_proceso',"
            "'limpio',"
            "'metadatos_registrados',"
            "'estandarizado',"
            "'vectorizado',"
            "'error'"
            ")",
            name="ck_instrumento_estado",
        ),
        {"schema": SCHEMA},
    )

    id_instrumento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        nullable=False,
    )
    ruta_de_archivo_limpio: Mapped[str | None] = mapped_column(String(255))
    ruta_json: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="recibido")
    fecha_procesamiento: Mapped[datetime] = mapped_column(server_default=func.now())
    fecha_aprobado: Mapped[datetime | None] = mapped_column()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<InstrumentoProcesado id_instrumento={self.id_instrumento} "
            f"estado={self.estado!r}>"
        )
