from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# 5. Esquemas de Metadatos Enriquecidos (Completos)
class MetadatosEncuestasBase(BaseModel):
    n_respondentes: Optional[int] = None
    n_poblacion: Optional[int] = None
    tipo_muestreo: Optional[str] = None
    representatividad: Optional[str] = None
    modalidad_aplicacion: Optional[str] = None
    referencia_bibliografica: Optional[str] = None
    notas_contextuales: Optional[str] = None
    secciones: Optional[Any] = None