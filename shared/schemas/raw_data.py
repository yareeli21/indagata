from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# 2. Esquema Raw Data
class RawDataBase(BaseModel):
    id_owner: int
    tipo_instrumento: str
    nombre_archivo: str
    ruta: str
    fecha_carga: datetime