from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# Esquemas Base
class UsuarioBase(BaseModel):
    nombre: str
    email: str
    rol: Optional[str] = None