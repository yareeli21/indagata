from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 4. metadatos_dc
class MetadatosDC(Base):
    __tablename__ = "metadatos_dc"
    id_crudo = Column(Integer, ForeignKey("raw_data.id_crudo"), primary_key=True)
    dc_title = Column(Text)
    dc_creator = Column(Text)
    dc_description = Column(Text)
    dc_type = Column(String(50))
    dc_languaje = Column(String(10))