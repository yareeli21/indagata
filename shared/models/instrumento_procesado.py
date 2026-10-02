# app/models/instrumento.py
#Este es el registro definido en el diagrama ER.

from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class InstrumentoProcesado(Base):
    __tablename__ = "instrumento_procesado"
    __table_args__ = {"schema": "tt_rag"}

    id_instrumento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_instrumento: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_json: Mapped[str | None] = mapped_column(Text)
    ruta_sav: Mapped[str | None] = mapped_column(Text)
    ruta_crudo: Mapped[str | None] = mapped_column(Text)
    hash_md5: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="ingresado")
    fecha_ingesta: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<InstrumentoProcesado id={self.id_instrumento} nombre={self.nombre!r}>"