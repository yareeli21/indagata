from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class VariableBase(BaseModel):
    nombre_variable: str
    tipo_dato: Optional[str] = None