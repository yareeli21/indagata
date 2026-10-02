from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 5. metadatos enriquecidos (Encuestas)
class MetadatosEncuestas(Base):
    __tablename__ = "metadatos_enriquecidos_encuestas"
    id_crudo = Column(Integer, ForeignKey("raw_data.id_crudo"), primary_key=True)
    n_respondentes = Column(Integer)
    n_poblacion = Column(Integer)
    tipo_investigacion = Column(Text)
    secciones = Column(JSONB)