# survey_intelligence/engine/heuristics/context_sufficiency.py
"""
Evaluación determinística de suficiencia de contexto (paso 1 de la restricción crítica).

NO interpreta el significado de una variable; solo mide si existe EVIDENCIA suficiente
para poder interpretarla más adelante. Marca candidatas a INSUFFICIENT_CONTEXT y redacta
el diagnóstico (qué falta, por qué, qué se requiere).

El LLM (S7, Tarea 10) respeta este veredicto: donde no hay evidencia, no inventa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from survey_intelligence.contracts.canonical import CanonicalVariable
from survey_intelligence.contracts.enums import ColumnClass, DataType

# Palabras que indican que un encabezado es una pregunta real (aporta contexto).
_QUESTION_SIGNALS = ("?", "¿", "indica", "evalúa", "evalua", "selecciona",
                     "ordena", "cómo", "como", "qué", "que", "cuál", "cual",
                     "cuánto", "cuanto", "cuándo", "cuando")

# Longitud mínima de encabezado para considerar que "dice algo" interpretable.
_MIN_HEADER_WORDS = 3


@dataclass(frozen=True)
class SufficiencyVerdict:
    """Veredicto de suficiencia para una variable."""
    variable_id: str
    is_interpretable: bool
    missing_information: list[str] = field(default_factory=list)
    why_not_interpretable: str | None = None
    required_to_interpret: list[str] = field(default_factory=list)


def _header_is_descriptive(header: str) -> bool:
    """El encabezado parece una pregunta o descripción real, no un nombre técnico."""
    low = header.lower()
    if any(sig in low for sig in _QUESTION_SIGNALS):
        return True
    # Suficientes palabras -> probablemente una afirmación/ítem interpretable.
    return len(header.split()) >= _MIN_HEADER_WORDS


def evaluate_variable(var: CanonicalVariable) -> SufficiencyVerdict:
    """
    Decide si una variable tiene evidencia suficiente para ser interpretable.

    Evidencia posible (cualquiera basta):
      - encabezado descriptivo (pregunta o ítem con texto),
      - pertenece a una matriz (tiene stem + item),
      - escala detectada con etiquetas,
      - es texto libre (el propio texto es la evidencia).

    Las columnas de plataforma se consideran INTERPRETABLE (su rol es conocido:
    metadato administrativo); no son candidatas a INSUFFICIENT_CONTEXT.
    """
    # Metadata de plataforma: interpretable por su rol conocido (no se enriquece
    # semánticamente, pero no es "sin contexto").
    if var.column_class == ColumnClass.PLATFORM_METADATA:
        return SufficiencyVerdict(var.variable_id, is_interpretable=True)

    has_descriptive_header = _header_is_descriptive(var.raw_header)
    has_matrix = var.matrix_group is not None
    has_scale = var.detected_scale is not None and bool(var.detected_scale.labels)
    is_free_text = var.inferred_data_type == DataType.FREE_TEXT

    if has_descriptive_header or has_matrix or has_scale or is_free_text:
        return SufficiencyVerdict(var.variable_id, is_interpretable=True)

    # Sin evidencia: construir el diagnóstico.
    missing: list[str] = []
    required: list[str] = []

    if not has_descriptive_header:
        missing.append("texto de la pregunta o descripción del ítem")
    if not has_scale:
        missing.append("etiquetas de valor que definan los códigos observados")
    missing.append("entrada de codebook que defina la variable")

    required.append("un codebook o diccionario de datos que defina esta variable")
    required.append("o el enunciado original del ítem en el instrumento")

    why = (
        f"La columna '{var.raw_header}' (nombre técnico '{var.normalized_name}') "
        f"no tiene pregunta, etiquetas de valor ni codebook que permitan interpretarla."
    )

    return SufficiencyVerdict(
        variable_id=var.variable_id,
        is_interpretable=False,
        missing_information=missing,
        why_not_interpretable=why,
        required_to_interpret=required,
    )
