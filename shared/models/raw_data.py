from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 2. raw_data
class RawData(Base):
    __tablename__ = "raw_data"
    id_crudo = Column(Integer, primary_key=True, autoincrement=True)
    id_owner = Column(Integer, ForeignKey("usuario.usuario_id"))
    tipo_instrumento = Column(String(50))
    nombre_archivo = Column(Text)
    ruta = Column(Text)