"""Shared Pydantic models"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class InstrumentBase(BaseModel):
    titulo: str
    tipo_instrumento: str
    archivo_nombre: str
    archivo_hash: str
    creador_id: int

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentUpdate(BaseModel):
    titulo: Optional[str] = None
    estado: Optional[str] = None

class InstrumentResponse(InstrumentBase):
    id: int
    estado: str
    creado_en: datetime
    actualizado_en: datetime
    
    class Config:
        from_attributes = True

class KPIResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    score_inferencia: Optional[float]
    
    class Config:
        from_attributes = True

class DublinCoreMetadata(BaseModel):
    dc_title: str
    dc_creator: str
    dc_subject: List[str]
    dc_description: Optional[str]
    dc_publisher: str
    dc_type: str
    dc_format: str
    dc_date: datetime
    dc_language: str = "es"
    dc_coverage: Optional[str]
    dc_rights: Optional[str]
    dc_source: Optional[str]
    dc_relation: Optional[str]

class ErrorResponse(BaseModel):
    detail: str
    error_code: str
