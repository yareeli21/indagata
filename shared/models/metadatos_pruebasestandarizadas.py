from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class MetadatosPruebasEstandarizadas(Base):
    __tablename__ = "metadatos_enriquecidos_pruebas"
    id_crudo = Column(Integer, ForeignKey("raw_data.id_crudo"), primary_key=True)
    institucion = Column(Text)
    grado = Column(Text)
    objetivo_de_evaluacion = Column(Text)