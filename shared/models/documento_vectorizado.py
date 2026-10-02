#Registro de los chunks generados que vincula la base de datos 
# relacional con ChromaDB a través de vector_id

from datetime import datetime
from sqlalchemy import Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class DocumentoVectorizado(Base):
    __tablename__ = "documento_vectorizado"
    __table_args__ = {"schema": "tt_rag"}

    id_documento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_instrumento: Mapped[int] = mapped_column(ForeignKey("tt_rag.instrumento_procesado.id_instrumento"))
    id_prompt: Mapped[int] = mapped_column(ForeignKey("tt_rag.prompt.id_prompt"))
    tipo_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    col_id: Mapped[str] = mapped_column(Text, nullable=False)
    texto_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())