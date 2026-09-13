# app/models/usuario.py
"""
Modelo SQLAlchemy para la tabla `usuarios` (schema tt_rag).
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


#Estructura de la tabla usuario


class Usuario(Base):
    __tablename__ = "usuarios"

    usuario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    correo: Mapped[str] = mapped_column(String(60), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    ) 