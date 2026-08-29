# app/models/usuario.py
"""
Modelo SQLAlchemy para la tabla `usuarios` (schema tt_rag).
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "tt_rag"}

    usuario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.usuario_id} usuario={self.usuario!r}>"