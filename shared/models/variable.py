from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class Variable(Base):
    __tablename__ = "variable"
    variable_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_variable = Column(Text)
    tipo_dato = Column(String(20))