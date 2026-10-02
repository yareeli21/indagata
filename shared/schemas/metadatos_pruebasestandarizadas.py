from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class MetadatosPruebasEstandarizadasBase(BaseModel):
    unidad_de_aprendizaje: Optional[str] = None
    mapeo_de_reactivos_por_seccion: Optional[Any] = None
    institucion: Optional[str] = None
    campus: Optional[str] = None
    grado: Optional[str] = None
    grupo: Optional[str] = None
    ciclo_escolar: Optional[str] = None
    tipo_de_prueba: Optional[str] = None
    version: Optional[str] = None
    taxonomia_bloom: Optional[str] = None
    nivel_educativo: Optional[str] = None
    objetivo_de_evaluacion: Optional[str] = None
    subareas: Optional[str] = None
    competencias: Optional[str] = None