#Registro operacional para MLLMOps y auditoría de la pantalla de Chat 

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class RagLogBase(BaseModel):
    id_instrumento: Optional[int] = None
    pregunta_usuario: str
    chunks_recuperados: Optional[str] = None
    respuesta_llm: Optional[str] = None
    modelo_usado: str
    latencia_ms: int

class RagLogCreate(RagLogBase):
    pass

class RagLogResponse(RagLogBase):
    id_consulta: int
    fecha: datetime
    model_config = ConfigDict(from_attributes=True)