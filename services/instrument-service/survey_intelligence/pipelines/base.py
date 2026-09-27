# survey_intelligence/pipelines/base.py
"""
Capa de estrategia por instrumento del SIS.

El SIS sigue siendo UN solo sistema con un único orquestador
(`SurveyIntelligenceService.process`). Lo que cambia entre encuestas, entrevistas
y pruebas estandarizadas se encapsula en una estrategia (`InstrumentPipeline`) que
el facade selecciona una vez al inicio.

Cada estrategia controla las DOS fases que divergen hoy:

  1. `build_canonical(...)`  -> cómo se construye el CanonicalSurveyModel
       (encuesta: tabular S1+S2+S3; documento: S2 documental, sin S1/S3).
  2. `analyze(...)`          -> el análisis ESPECÍFICO del instrumento
       (encuesta: S8b resultados por columna/pregunta + perfiles de respondente;
        entrevista: S10 análisis de entrevista; prueba: aún sin reglas propias).

El TRONCO COMÚN (S4 suficiencia, S5 codebook, S6 auditoría, S7 enriquecimiento,
S7b KPIs, S8 gap analysis, S9 ensamblado, diagnósticos, degradación y armado del
SurveyIntelligenceResult) vive en el facade y NO se duplica por instrumento.

Las estrategias COMPONEN los stages existentes; no reimplementan su lógica.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.interview import InterviewAnalysis
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.contracts.results import ResultsFinding
from survey_intelligence.ports.clock_port import ClockPort
from survey_intelligence.ports.ids_port import IdGeneratorPort
from survey_intelligence.ports.llm_port import LLMPort

# Firma del emisor de diagnósticos que provee el facade. Cada estrategia lo usa
# para reportar sus etapas con los MISMOS nombres/estados que hoy (sin romper el
# contrato de diagnósticos ni los tests).
EmitFn = Callable[..., None]


def ms_since(t0: float) -> int:
    """Milisegundos transcurridos desde t0 (perf_counter)."""
    return int((time.perf_counter() - t0) * 1000)


class PipelineError(Exception):
    """Fallo fatal en la construcción del canónico (equivale a S1/S2 fatales)."""


@dataclass(frozen=True)
class PipelineDeps:
    """Dependencias inyectadas que las estrategias necesitan (subconjunto del facade)."""
    llm: LLMPort | None
    clock: ClockPort
    ids: IdGeneratorPort


@dataclass
class CanonicalBuild:
    """
    Resultado de la fase de construcción del canónico.

    `ingestion` solo lo produce la vía tabular (encuesta); el tronco común no lo
    necesita, pero la propia estrategia lo reusa en su fase `analyze`.
    `document_text` solo lo produce la vía documental (entrevista/prueba).
    """
    canonical: CanonicalSurveyModel
    ingestion: object | None = None
    document_text: str = ""


@dataclass
class InstrumentAnalysis:
    """
    Cara de conocimiento ESPECÍFICA del instrumento, aditiva sobre el tronco común.

    Cada campo es opcional: una estrategia solo llena lo suyo. El facade la fusiona
    en el SurveyIntelligenceResult final.
    """
    results_findings: list[ResultsFinding] = field(default_factory=list)
    interview_analysis: InterviewAnalysis | None = None
    llm_calls: int = 0
    degraded: bool = False


class InstrumentPipeline(Protocol):
    """
    Estrategia por tipo de instrumento. Compone los stages existentes; no los
    reimplementa. El facade la selecciona con `select_pipeline(instrument_type)`.
    """

    #: Etiqueta del instrumento (para diagnósticos/telemetría).
    instrument_type: str

    def build_canonical(
        self,
        request: SurveyIngestionRequest,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> CanonicalBuild:
        """
        Construye el CanonicalSurveyModel. Emite las etapas 'ingestion'/'canonical'/
        'profiling' con los estados que correspondan a la vía.

        Lanza PipelineError si una etapa fatal falla (el facade lo traduce a
        status=failed con diagnóstico, sin lanzar al host).
        """
        ...

    def analyze(
        self,
        request: SurveyIngestionRequest,
        canonical: CanonicalSurveyModel,
        build: CanonicalBuild,
        spss_by_id: dict,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> InstrumentAnalysis:
        """
        Ejecuta el análisis específico del instrumento (emite 'results_analysis',
        'interview_analysis', etc. según el tipo). Nunca lanza: degrada.
        """
        ...
