# app/models/kpi.py
#Catálogo centralizado de indicadores 
#clave de desempeño gestionado por el administrador

from sqlalchemy import Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class KPI(Base):
    __tablename__ = "kpi"
    __table_args__ = {"schema": "tt_rag"}

    id_kpi: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    unidad: Mapped[str | None] = mapped_column(Text)
    umbral_referencia: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<KPI id={self.id_kpi} nombre={self.nombre!r}>"