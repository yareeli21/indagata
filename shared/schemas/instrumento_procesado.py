from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Esquema base con los atributos comunes
class InstrumentoBase(BaseModel):
    nombre: str
    tipo_instrumento: str
    ruta_json: Optional[str] = None
    ruta_sav: Optional[str] = None
    ruta_crudo: Optional[str] = None
    hash_md5: Optional[str] = None
    estado: str = "ingresado"

# Esquema para crear (recibe datos del frontend o del pipeline)
class InstrumentoCreate(InstrumentoBase):
    pass

# Esquema para actualizar rutas o estados
class InstrumentoUpdate(BaseModel):
    estado: Optional[str] = None
    ruta_json: Optional[str] = None
    ruta_sav: Optional[str] = None

# Esquema de salida (lo que se responde al frontend)
class InstrumentoResponse(InstrumentoBase):
    id_instrumento: int
    fecha_ingesta: datetime

    # Permite a Pydantic leer los objetos de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)