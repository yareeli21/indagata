from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 13. tabla_chunks (Duplicada según lo solicitado)
class TablaChunks(Base):
    __tablename__ = "tabla_chunks"
    id_chunk = Column(Integer, primary_key=True, autoincrement=True)
    texto = Column(Text)