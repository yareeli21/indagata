from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

# 1. usuario
class Usuario(Base):
    __tablename__ = "usuario"
    usuario_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    rol = Column(String(50))