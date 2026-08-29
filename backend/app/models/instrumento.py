# app/models/instrumento.py
from datetime import datetime

from sqlalchemy import String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InstrumentoProcesado(Base):
    __tablename__ = "instrumento_procesado"
    __table_args__ = {"schema": "tt_rag"}

    instrumento_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    plataforma: Mapped[str | None] = mapped_column(String(50))
    ruta_json: Mapped[str | None] = mapped_column(Text)
    ruta_sav: Mapped[str | None] = mapped_column(Text)
    metadatos: Mapped[dict | None] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="ingresado")
    fecha_procesamiento: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<InstrumentoProcesado id={self.instrumento_id} nombre={self.nombre!r}>"