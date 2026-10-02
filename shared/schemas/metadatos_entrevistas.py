from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class MetadatosEntrevistasBase(BaseModel):
    identificador_propio: Optional[str] = None
    objetivo: Optional[str] = None
    metodologia: Optional[str] = None
    institucion: Optional[str] = None
    derechos: Optional[str] = None