# app/models/kpi.py
from sqlalchemy import String, Text, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Kpi(Base):
    __tablename__ = "kpi"
    __table_args__ = {"schema": "tt_rag"}

    kpi_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombrekpi: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    direccion_deseada: Mapped[str | None] = mapped_column(Text)
    razon: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    umbral_bajo: Mapped[float | None] = mapped_column(Numeric)
    umbral_medio: Mapped[float | None] = mapped_column(Numeric)
    umbral_alto: Mapped[float | None] = mapped_column(Numeric)
    unidad: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Kpi id={self.kpi_id} nombre={self.nombrekpi!r}>"