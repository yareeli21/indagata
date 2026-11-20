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
    # Dónde: cada caso con su fila, columna y valor antes y después (los primeros cientos; el total va en
    # «afectados»), y cuántos cambios hubo por columna.
    casos: list[dict[str, Any]] = Field(default_factory=list)
    columnas: dict[str, int] = Field(default_factory=dict)


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


class SugerenciaOut(BaseModel):
    """Una sugerencia de análisis derivada de las medidas estadísticas (shared/conocimiento/sugerencias.py)."""

    nivel: Literal["bien", "info", "atencion", "alerta"]
    texto: str
    porque: str


class ResumenLimpiezaOut(BaseModel):
    """Medidas de la última limpieza confirmada y sugerencias de análisis (sin filas de muestra)."""

    idCrudo: int
    version: int
    tipoInstrumento: str
    fechaConfirmacion: datetime | None = None
    cifras: list[CifraOut] = Field(default_factory=list)
    estadistica: dict[str, Any] | None = None
    estadistica_antes: dict[str, Any] | None = None
    resumen: list[FraseResumenOut] = Field(default_factory=list)
    sugerencias: list[SugerenciaOut] = Field(default_factory=list)


class CodigoOut(BaseModel):
    codigo: str
    n: int | None = None


class ColumnaCodigosOut(BaseModel):
    """Una columna (o reactivo) a la que se le puede dar texto y significado de sus códigos."""

    clave: str
    etiqueta: str
    tipo: str | None = None
    encabezado_codigo: bool = False
    codigos: list[CodigoOut] = Field(default_factory=list)
    pregunta: str | None = None
    etiquetas: dict[str, str] = Field(default_factory=dict)
    origen: str | None = None  # diccionario | investigador | anterior


class DiccionarioOut(BaseModel):
    nombre: str = ""
    emparejadas: int = 0
    sin_columna: list[str] = Field(default_factory=list)
    n_sin_columna: int = 0


class CodigosOut(BaseModel):
    columnas: list[ColumnaCodigosOut] = Field(default_factory=list)
    diccionario: DiccionarioOut | None = None


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
    codigos: CodigosOut | None = None
    vistaFinal: VistaFinalOut | None = None


class SignificadoIn(BaseModel):
    pregunta: str | None = Field(default=None, max_length=2000)
    valores: dict[str, str] = Field(default_factory=dict)


class SignificadosIn(BaseModel):
    """Guardado parcial: {columna: {pregunta, valores: {código: etiqueta}}}. null borra su significado."""

    significados: dict[str, SignificadoIn | None] = Field(min_length=1)


class DecisionesIn(BaseModel):
    """Guardado parcial: {id_hallazgo: opción elegida}. null borra la decisión."""

    decisiones: dict[str, str | None] = Field(min_length=1)
