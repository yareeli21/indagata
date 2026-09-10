from pydantic import BaseModel, Field
from typing import Optional


class KpiBase(BaseModel):

    kpi_id: int = Field(..., alias="KPI_ID")
    nombrekpi: str = Field(..., alias="Nombre del KPI", nullable=False)
    descripcion: str = Field(..., alias="Descripción") 
    direccion_deseada: str = Field(..., alias="Direccion deseada")
    razon: str = Field(..., alias="Razón") 
    formula: str = Field(..., alias="Fórmula") 
    umbral_bajo: float = Field(..., alias="Umbral bajo") 
    umbral_medio: float = Field(..., alias="Umbral medio") 
    umbral_alto: float = Field(..., alias="Umbral alto") 
    unidad: str = Field(..., alias="Unidad")
    activo: bool = Field(..., alias="Activo")


class KpiCreate(KpiBase):
    pass


class KpiUpdate(KpiBase):
    pass


class KpiResponse(KpiBase):
    class Config:
        orm_mode = True
        from_atributes = True
        allow_population_by_field_name = True
        populate_by_name = True