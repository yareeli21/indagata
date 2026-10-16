"""DTOs HTTP del cleaning-service.

La interfaz NUNCA recibe el reporte_limpieza en crudo: estos DTOs son una vista
derivada, pensada para la fase asistida y la vista final.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EstadoLimpieza = Literal["esperando_decisiones", "confirmada", "fallida"]


class HallazgoOut(BaseModel):
    """Una decisión pendiente o tomada de la fase asistida."""

    id: str
    tipo: str
    tema: str
    objetivo: str
    titulo: str
    descripcion: str
    opciones: list[str]
    sugerida: str | None = None
    obligatoria: bool = False
    detalle: dict[str, Any] = Field(default_factory=dict)
    # Valor elegido por el investigador (None = aún no decide; se usará la sugerida).
    decision: str | None = None


class TransformacionOut(BaseModel):
    """Una transformación automática aplicada (se muestra como resumen)."""

    regla: str
    detalle: str
    afectados: int | None = None


class CifraOut(BaseModel):
    etiqueta: str
    valor: int | float | str


class ComparacionOut(BaseModel):
    """Una métrica antes y después de la limpieza."""

    metrica: str
    antes: float | None = None
    despues: float | None = None
    formato: Literal["num", "pct", "dec"] = "num"


class FraseResumenOut(BaseModel):
    """Una frase del resumen «En pocas palabras» de las medidas estadísticas."""

    nivel: Literal["bien", "info", "atencion", "alerta"]
    texto: str


class VistaFinalOut(BaseModel):
    """Lo que ve el investigador al terminar: cifras clave, una muestra del resultado
    y las medidas estadísticas (descriptivos, fiabilidad, análisis de reactivos)."""

    cifras: list[CifraOut]
    forma: Literal["tabla", "turnos"]
    columnas: list[str]
    filas: list[list[str]]
    total_filas: int
    comparacion: list[ComparacionOut] = Field(default_factory=list)
    estadistica: dict[str, Any] | None = None
    estadistica_antes: dict[str, Any] | None = None
    resumen: list[FraseResumenOut] = Field(default_factory=list)


class EjecucionOut(BaseModel):
    """Estado de una ejecución de limpieza para la interfaz."""

    idCrudo: int
    version: int
    estado: EstadoLimpieza
    tipoInstrumento: str
    fechaCreacion: datetime | None = None
    fechaActualizacion: datetime | None = None
    fechaConfirmacion: datetime | None = None
    error: str | None = None
    avisos: list[str] = Field(default_factory=list)
    metricasAntes: dict[str, Any] = Field(default_factory=dict)
    transformaciones: list[TransformacionOut] = Field(default_factory=list)
    hallazgos: list[HallazgoOut] = Field(default_factory=list)
    pendientesObligatorias: int = 0
    vistaFinal: VistaFinalOut | None = None


class DecisionesIn(BaseModel):
    """Guardado parcial: {id_hallazgo: opción elegida}. null borra la decisión."""

    decisiones: dict[str, str | None] = Field(min_length=1)
