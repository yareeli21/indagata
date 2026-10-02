#Catálogo de prompts base con versionado histórico.

from datetime import datetime
from sqlalchemy import Integer, Text, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class Prompt(Base):
    __tablename__ = "prompt"
    __table_args__ = {"schema": "tt_rag"}

    id_prompt: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    temperatura: Mapped[float] = mapped_column(Numeric, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())