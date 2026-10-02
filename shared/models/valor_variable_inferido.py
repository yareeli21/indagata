from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 11. valor_variable_inferido
class ValorVariableInferido(Base):
    __tablename__ = "valor_variable_inferido"
    id_procesado = Column(Integer, primary_key=True)
    kpi_id = Column(Integer, primary_key=True)
    variable_id = Column(Integer, ForeignKey("variable.variable_id"), primary_key=True)
    valor_numerico = Column(Numeric)
    valor_texto = Column(Text)