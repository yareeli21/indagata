from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# 9. kpi_variable
class KPIVariable(Base):
    __tablename__ = "kpi_variable"
    kpi_id = Column(Integer, ForeignKey("kpi.kpi_id"), primary_key=True)
    variable_id = Column(Integer, ForeignKey("variable.variable_id"), primary_key=True)