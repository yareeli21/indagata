# survey_intelligence/contracts/canonical.py
"""
Canonical Survey Model: representación normalizada y determinística.

Es la verdad estructural del instrumento. Se construye solo con parsing + profiling
(sin LLM) y es reproducible al 100%. Aquí viven TODAS las métricas y datos
administrativos (design.md §4.1). El Enriched Model NO debe contener nada de esto.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.enums import (
    CanonicalQuestionType,
    ColumnClass,
    DataType,
    ScaleKind,
    SourceEncoding,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SourceInfo(BaseModel):
    model_config = _FROZEN

    platform_guess: str | None = None
    file_name: str
    sheet: str | None = None


class Dimensions(BaseModel):
    model_config = _FROZEN

    n_rows: int
    n_columns: int


class ScaleAnomaly(BaseModel):
    """Valor de escala sospechoso de error de escritura (distancia de edición 1)."""
    model_config = _FROZEN

    value: str
    occurrences: int
    canonical_guess: str


class DetectedScale(BaseModel):
    model_config = _FROZEN

    kind: ScaleKind
    points: int | None = None
    labels: list[str] = Field(default_factory=list)
    consistent: bool = True
    anomalies: list[ScaleAnomaly] = Field(default_factory=list)


class MatrixGroup(BaseModel):
    """Descomposición de una pregunta matriz con patrón `tronco [ítem]`."""
    model_config = _FROZEN

    stem: str
    item: str


class ValueDistribution(BaseModel):
    model_config = _FROZEN

    n_non_null: int
    n_null: int
    null_ratio: float
    cardinality: int
    n_structural_null: int = 0
    top_values: list[dict] = Field(default_factory=list)


class ProfilingStats(BaseModel):
    model_config = _FROZEN

    min: float | None = None
    max: float | None = None
    mean: float | None = None
    entropy: float | None = None


class CanonicalVariable(BaseModel):
    model_config = _FROZEN

    variable_id: str
    raw_header: str
    normalized_name: str
    position: int
    column_class: ColumnClass = ColumnClass.UNKNOWN
    inferred_data_type: DataType = DataType.UNKNOWN
    detected_scale: DetectedScale | None = None
    matrix_group: MatrixGroup | None = None
    value_distribution: ValueDistribution | None = None
    profiling_stats: ProfilingStats | None = None


# ───────────────────────────────────────────────────────────────────────────
# Rediseño v2 — modelos "pregunta como unidad lógica" (aditivos, opcionales).
# Ver docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md. NO reemplazan a CanonicalVariable todavía;
# conviven con él (capa de compatibilidad) hasta que S2 v2 esté activo.
# ───────────────────────────────────────────────────────────────────────────

class QuestionOption(BaseModel):
    """Una alternativa de respuesta (opción única/múltiple, escala)."""
    model_config = _FROZEN

    option_id: str
    label: str


class QuestionItem(BaseModel):
    """Una fila/aspecto de una pregunta matriz o likert multi-ítem."""
    model_config = _FROZEN

    item_id: str
    label: str


class QuestionScale(BaseModel):
    """Escala ordinal de una pregunta likert/escala."""
    model_config = _FROZEN

    points: int | None = None
    labels: list[str] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None


class SourceColumn(BaseModel):
    """
    Trazabilidad de una columna del archivo original que respalda una pregunta.

    `maps_to` indica a qué parte de la pregunta corresponde (option_id / item_id / rank / scale).
    """
    model_config = _FROZEN

    raw_header: str
    position: int
    encoding: SourceEncoding = SourceEncoding.SINGLE_CELL
    maps_to: dict = Field(default_factory=dict)


class QuestionResponse(BaseModel):
    """Respuesta reconstruida de un respondente a una pregunta (ids internos + labels legibles)."""
    model_config = _FROZEN

    respondent_id: str
    # value: forma libre según tipo (str | list | dict). Se guarda tal cual, sin inventar.
    value: object | None = None
    labels: object | None = None


class QuestionDistributionBin(BaseModel):
    """Una barra de distribución (por opción/ítem/valor según el tipo)."""
    model_config = _FROZEN

    label: str
    option_id: str | None = None
    item_id: str | None = None
    frequency: int = 0
    percentage: float = 0.0


class CanonicalQuestion(BaseModel):
    model_config = _FROZEN

    question_id: str
    variable_ids: list[str]
    text: str
    length_chars: int
    length_words: int

    # ── Campos v2 (aditivos, opcionales; None/vacío en el modelo actual v1) ──
    type: CanonicalQuestionType | None = None
    platform_type: str | None = None
    type_confidence: float | None = None
    type_fallback: CanonicalQuestionType | None = None
    options: list[QuestionOption] = Field(default_factory=list)
    items: list[QuestionItem] = Field(default_factory=list)
    scale: QuestionScale | None = None
    source_columns: list[SourceColumn] = Field(default_factory=list)
    responses: list[QuestionResponse] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    distribution: list[QuestionDistributionBin] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class OpenAnswer(BaseModel):
    """Respuesta abierta preservada íntegra como evidencia textual (perfil de respondente)."""
    model_config = _FROZEN

    question_id: str
    pregunta: str
    texto: str


class RespondentProfile(BaseModel):
    """
    Perfil determinista de un respondente (rediseño v2). Se genera SIN LLM:
    resumen por plantillas desde preguntas estructuradas + respuestas abiertas íntegras.
    """
    model_config = _FROZEN

    respondent_id: str
    n_respondidas: int = 0
    n_omitidas: int = 0
    respuestas: list[dict] = Field(default_factory=list)
    resumen: str | None = None
    respuestas_abiertas: list[OpenAnswer] = Field(default_factory=list)
    trazabilidad: dict = Field(default_factory=dict)


class CanonicalSurveyModel(BaseModel):
    """Modelo canónico completo. `canonical_id` es un hash del contenido normalizado."""
    model_config = _FROZEN

    canonical_id: str
    source: SourceInfo
    dimensions: Dimensions
    variables: list[CanonicalVariable]
    questions: list[CanonicalQuestion] = Field(default_factory=list)
    # v2 (aditivo): orden estable de respondentes (fila del archivo). Vacío en v1.
    respondents_index: list[str] = Field(default_factory=list)
