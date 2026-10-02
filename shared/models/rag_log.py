#Registro operacional de consultas procesadas para trazabilidad 
# y evaluación de calidad con MLLMOps.

from datetime import datetime
from sqlalchemy import Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class RagLog(Base):
    __tablename__ = "rag_log"
    __table_args__ = {"schema": "tt_rag"}

    id_consulta: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_instrumento: Mapped[int | None] = mapped_column(ForeignKey("tt_rag.instrumento_procesado.id_instrumento"))
    pregunta_usuario: Mapped[str] = mapped_column(Text, nullable=False)
    chunks_recuperados: Mapped[str | None] = mapped_column(Text)
    respuesta_llm: Mapped[str | None] = mapped_column(Text)
    modelo_usado: Mapped[str] = mapped_column(Text, nullable=False)
    latencia_ms: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())