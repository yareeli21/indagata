from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class KPIInferidoBase(BaseModel):
    kpi_id: int
    razon: Optional[str] = None
    resultado: Optional[float] = None