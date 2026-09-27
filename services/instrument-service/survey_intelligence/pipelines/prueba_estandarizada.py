# survey_intelligence/pipelines/prueba_estandarizada.py
"""
Estrategia de PRUEBAS ESTANDARIZADAS (vía documental).

ESTADO ACTUAL (esqueleto): se comporta EXACTAMENTE como hoy. Construye el canónico
documental (mismo que entrevista) y NO ejecuta análisis específico todavía: hoy una
prueba estandarizada solo se ingiere como texto, sin interpretación psicométrica.

  build_canonical -> canónico documental compartido (texto -> segmentos free_text)
  analyze         -> sin análisis propio (aún no hay reglas psicométricas definidas)

El resto (S4..S9) lo ejecuta el tronco común del facade, igual que antes.

TODO (pendiente de definir el proceso de pruebas estandarizadas):
  - Reglas de normalización específicas (ítems, claves de respuesta, puntajes).
  - Métricas psicométricas (dificultad, discriminación, fiabilidad, etc.).
  - Interpretación de resultados y su cara de conocimiento en el resultado.
Cuando se definan, se implementarán AQUÍ (y en engine/psychometrics/ + su contrato),
sin tocar encuestas ni entrevistas.
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.request import SurveyIngestionRequest
from survey_intelligence.pipelines._document import build_document_canonical_phase
from survey_intelligence.pipelines.base import (
    CanonicalBuild,
    EmitFn,
    InstrumentAnalysis,
    InstrumentPipeline,
    PipelineDeps,
)


class PruebaEstandarizadaPipeline(InstrumentPipeline):
    """Estrategia documental para pruebas estandarizadas (esqueleto, sin reglas propias)."""

    instrument_type = "prueba_estandarizada"

    def build_canonical(
        self,
        request: SurveyIngestionRequest,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> CanonicalBuild:
        return build_document_canonical_phase(request, emit)

    def analyze(
        self,
        request: SurveyIngestionRequest,
        canonical: CanonicalSurveyModel,
        build: CanonicalBuild,
        spss_by_id: dict,
        deps: PipelineDeps,
        emit: EmitFn,
    ) -> InstrumentAnalysis:
        # Aún sin análisis psicométrico. Comportamiento idéntico al actual: el tronco
        # común (S4..S9) ya corrió; aquí no se añade ninguna cara específica.
        return InstrumentAnalysis()
