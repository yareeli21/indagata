from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentoVectorizadoBase(BaseModel):
    id_instrumento: int
    id_prompt: int
    tipo_chunk: str
    col_id: str
    texto_chunk: str
    vector_id: str
    activo: bool = True

class DocumentoVectorizadoCreate(DocumentoVectorizadoBase):
    pass

class DocumentoVectorizadoResponse(DocumentoVectorizadoBase):
    id_documento: int
    fecha: datetime
    model_config = ConfigDict(from_attributes=True)