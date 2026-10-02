from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class PreguntaKPIBase(BaseModel):
    id_instrumento: int
    id_kpi: int
    id_variable: str
    score_inferencia: Optional[float] = None

class PreguntaKPICreate(PreguntaKPIBase):
    pass

class PreguntaKPIResponse(PreguntaKPIBase):
    id_asignacion: int
    fecha_asignacion: datetime
    model_config = ConfigDict(from_attributes=True)