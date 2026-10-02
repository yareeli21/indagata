#El administrador gestiona este catálogo. Los KPIs no se eliminan
#físicamente para no romper el historial, sino que se desactiva

from pydantic import BaseModel, ConfigDict
from typing import Optional

class KPIBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    formula: Optional[str] = None
    unidad: Optional[str] = None
    umbral_referencia: Optional[str] = None
    activo: bool = True

class KPICreate(KPIBase):
    pass

class KPIUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    formula: Optional[str] = None
    unidad: Optional[str] = None
    umbral_referencia: Optional[str] = None
    activo: Optional[bool] = None

class KPIResponse(KPIBase):
    id_kpi: int
    model_config = ConfigDict(from_attributes=True)