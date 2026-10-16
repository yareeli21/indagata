"""DTOs de la asociación de KPIs desde el perfil semántico."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

OrigenJustificacion = Literal["llm", "llm_revisada", "plantilla", "plantilla_revisada"]


class EvidenciaOut(BaseModel):
    pregunta_id: str
    texto: str = Field(..., description="Texto de la pregunta (para mostrar).")
    similitud: float


class KpiPropuestoOut(BaseModel):
    kpi_id: int
    kpi_ref: str = Field(..., description="ID global del KPI (KPI-07).")
    nombre: str
    definicion: str = Field(..., description="texto_contexto_rag_vectorial (la columna que se embebe).")
    que_mide: str = Field(..., description="descripcion_ampliada_educativa.")
    dimension: str = Field(..., description="tipo_objetivo_estrategico.")
    polaridad: str = ""
    score: float
    componentes: dict[str, float] = Field(..., description="{g, p, c} de la fórmula.")
    evidencia: list[EvidenciaOut]
    justificacion: str
    justificacion_origen: Literal["llm", "plantilla"]


class PropuestasPerfilRequest(BaseModel):
    id_crudo: int
    justificar_con_llm: bool | None = Field(default=None, description="None = según configuración.")


class PropuestasPerfilResponse(BaseModel):
    id_crudo: int
    version: int
    n_preguntas: int = Field(..., description="Unidades de pregunta embebidas.")
    formula: dict[str, float]
    kpis: list[KpiPropuestoOut]


class EvidenciaIn(BaseModel):
    pregunta_id: str
    similitud: float = Field(..., ge=0, le=1)


class DecisionPerfilIn(BaseModel):
    kpi_id: int
    aceptado: bool
    score: float = Field(..., ge=0, le=1)
    componentes: dict[str, float] = Field(default_factory=dict)
    evidencia: list[EvidenciaIn] = Field(default_factory=list)
    justificacion: str = Field(default="", max_length=2000)
    justificacion_origen: Literal["llm", "plantilla"] = "plantilla"
    editada: bool = Field(default=False, description="El investigador editó la justificación.")


class ConfirmarPerfilRequest(BaseModel):
    id_crudo: int
    version: int
    decisiones: list[DecisionPerfilIn]


class KpiAsociadoOut(BaseModel):
    """Mismo formato que `kpis_asociados` en el documento final."""

    kpi_id: str
    nombre: str
    definicion: str
    dimension: str
    que_mide: str
    similitud: float
    evidencia: list[EvidenciaIn]
    justificacion: str
    justificacion_origen: OrigenJustificacion
    aceptado_por: str
    fecha: str


class ConfirmarPerfilResponse(BaseModel):
    id_crudo: int
    version: int
    estado: str
    kpis_asociados: list[KpiAsociadoOut]
    n_rechazados: int
