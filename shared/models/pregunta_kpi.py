#Tabla de asignación que registra qué KPI mide 
# cada variable, vinculando instrumento_procesado y kpi.

from datetime import datetime
from sqlalchemy import Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class PreguntaKPI(Base):
    __tablename__ = "pregunta_kpi"
    __table_args__ = {"schema": "tt_rag"}

    id_asignacion: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_instrumento: Mapped[int] = mapped_column(ForeignKey("tt_rag.instrumento_procesado.id_instrumento"))
    id_kpi: Mapped[int] = mapped_column(ForeignKey("tt_rag.kpi.id_kpi"))
    id_variable: Mapped[str] = mapped_column(Text, nullable=False)
    score_inferencia: Mapped[float | None] = mapped_column(Numeric)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())