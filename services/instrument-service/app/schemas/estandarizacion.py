"""Schemas Pydantic v2 de la etapa de estandarización (diseño §1.6).

Contratos de los endpoints `preview` y `estandarizar`. El vocabulario de `type`
es cerrado (frontera donde se valida el input del investigador):

    binaria | opcion_multiple | likert | numerica_continua | abierta
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

TipoPregunta = Literal[
    "binaria",
    "opcion_multiple",
    "likert",
    "numerica_continua",
    "abierta",
]


class TipoPreguntaDetectado(BaseModel):
    """Propuesta de tipo por pregunta que devuelve `preview` (no persiste)."""

    question_id: str
    text: str
    type: TipoPregunta
    options: list[str] | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    confianza: Literal["alta", "media", "baja"]
    es_demografica: bool = False


class PreviewResponse(BaseModel):
    """Respuesta de `POST /instrumentos/{id}/estandarizar/preview`."""

    id_crudo: int
    tipo_instrumento: str
    preguntas: list[TipoPreguntaDetectado]
    n_respondentes_detectados: int
    notas: list[str] = Field(default_factory=list)


class PreguntaConfirmada(BaseModel):
    """Pregunta CONFIRMADA/CORREGIDA por el investigador (entrada a estandarizar)."""

    question_id: str
    text: str
    type: TipoPregunta
    options: list[str] | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    es_demografica: bool = False

    @model_validator(mode="after")
    def _validar_escala(self) -> "PreguntaConfirmada":
        """Valida la escala SOLO si type == likert (1 <= min < max <= 100)."""
        if self.type != "likert":
            return self
        lo, hi = self.scale_min, self.scale_max
        if lo is None and hi is None:
            # El backend recalcula desde los datos (best-effort).
            return self
        if lo is None or hi is None:
            raise ValueError(
                "scale_min y scale_max deben indicarse juntos para una pregunta likert."
            )
        if not (1 <= lo < hi <= 100):
            raise ValueError(
                "La escala likert debe cumplir 1 <= scale_min < scale_max <= 100."
            )
        return self


class EstandarizarRequest(BaseModel):
    """Cuerpo de `POST /instrumentos/{id}/estandarizar`."""

    preguntas: list[PreguntaConfirmada] = Field(..., min_length=1)


class EstandarizarResponse(BaseModel):
    """Respuesta de `POST /instrumentos/{id}/estandarizar`."""

    id_crudo: int
    id_instrumento: int
    estado: str
    ruta_json: str
    json_instrumento: dict[str, Any]
    mensaje: str
