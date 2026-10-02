from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 10. kpi_inferido (Sin puntuación LLM ni puntuación RAG)
class KPIInferido(Base):
    __tablename__ = "kpi_inferido"
    id_procesado = Column(Integer, ForeignKey("instrumento_procesado.id_procesado"), primary_key=True)
    kpi_id = Column(Integer, ForeignKey("kpi.kpi_id"), primary_key=True)
    razon = Column(Text)