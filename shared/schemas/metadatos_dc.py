from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# 4. Esquema Metadatos DC (Completo)
class MetadatosDCBase(BaseModel):
    dc_title: str
    dc_creator: Optional[str] = None
    dc_description: Optional[str] = None
    dc_type: Optional[str] = None
    dc_date: Optional[str] = None
    dc_language: Optional[str] = None
    dc_coverage: Optional[str] = None
    dc_subject: Optional[str] = None
    dc_publisher: Optional[str] = None
    dc_rights: Optional[str] = None
    dc_format: Optional[str] = None
    dc_source: Optional[str] = None
    dc_relation: Optional[str] = None