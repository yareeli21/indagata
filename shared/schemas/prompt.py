#Catálogo de prompts base gestionado por el administrador. Guarda el historial de versiones 

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class PromptBase(BaseModel):
    nombre: str
    tipo: str
    texto: str
    version: int = 1
    temperatura: float
    activo: bool = True

class PromptCreate(PromptBase):
    pass

class PromptUpdate(BaseModel):
    activo: Optional[bool] = None

class PromptResponse(PromptBase):
    id_prompt: int
    fecha_creacion: datetime
    model_config = ConfigDict(from_attributes=True)