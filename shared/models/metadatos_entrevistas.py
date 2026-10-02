from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class MetadatosEntrevistas(Base):
    __tablename__ = "metadatos_enriquecidos_entrevistas"
    id_crudo = Column(Integer, ForeignKey("raw_data.id_crudo"), primary_key=True)
    objetivo = Column(Text)
    metodologia = Column(Text)
    institucion = Column(Text)