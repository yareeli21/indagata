# survey_intelligence/pipelines/__init__.py
"""
Estrategias por instrumento del SIS.

El facade selecciona una estrategia con `select_pipeline(instrument_type)` y delega
en ella las fases que divergen (construcción del canónico y análisis específico),
manteniendo el tronco común (S4..S9) en el orquestador.

Tipos soportados: 'encuesta', 'entrevista', 'prueba_estandarizada'. Cualquier valor
desconocido cae a la estrategia de encuesta (comportamiento histórico por defecto).
"""
from __future__ import annotations

from survey_intelligence.pipelines.base import (
    CanonicalBuild,
    InstrumentAnalysis,
    InstrumentPipeline,
    PipelineDeps,
    PipelineError,
)
from survey_intelligence.pipelines.encuesta import EncuestaPipeline
from survey_intelligence.pipelines.entrevista import EntrevistaPipeline
from survey_intelligence.pipelines.prueba_estandarizada import PruebaEstandarizadaPipeline

_PIPELINES: dict[str, InstrumentPipeline] = {
    "encuesta": EncuestaPipeline(),
    "entrevista": EntrevistaPipeline(),
    "prueba_estandarizada": PruebaEstandarizadaPipeline(),
}


def select_pipeline(instrument_type: str) -> InstrumentPipeline:
    """
    Devuelve la estrategia para el tipo de instrumento.

    Un tipo desconocido cae a la estrategia de encuesta (vía tabular), que es el
    comportamiento por defecto histórico del SIS.
    """
    return _PIPELINES.get(instrument_type, _PIPELINES["encuesta"])


__all__ = [
    "select_pipeline",
    "InstrumentPipeline",
    "PipelineDeps",
    "PipelineError",
    "CanonicalBuild",
    "InstrumentAnalysis",
]
