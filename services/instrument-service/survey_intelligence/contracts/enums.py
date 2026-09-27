# survey_intelligence/contracts/enums.py
"""
Enumeraciones de dominio del SIS.

Vocabularios cerrados que gobiernan los contratos. Son parte del schema público,
por lo que cambiar un valor implica subir SCHEMA_VERSION.
"""
from __future__ import annotations

from enum import Enum


class InterpretabilityStatus(str, Enum):
    """Estado interpretativo de una variable (ver design.md §11)."""
    INTERPRETABLE = "INTERPRETABLE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class ColumnClass(str, Enum):
    """Clasificación estructural de una columna del instrumento."""
    QUESTION = "question"
    PLATFORM_METADATA = "platform_metadata"
    FREE_TEXT = "free_text"
    UNKNOWN = "unknown"


class DataType(str, Enum):
    """Tipo de dato inferido de forma determinística (sin LLM)."""
    ORDINAL = "ordinal"
    NOMINAL = "nominal"
    NUMERIC = "numeric"
    FREE_TEXT = "free_text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    # Celda con múltiples opciones elegidas separadas por delimitador (Microsoft
    # Forms colapsa la opción múltiple en una sola celda, p. ej. "A;B;C").
    MULTI_SELECT = "multi_select"
    UNKNOWN = "unknown"


class ScaleKind(str, Enum):
    """Tipo de escala detectada."""
    LIKERT = "likert"
    BINARY = "binary"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


class Measure(str, Enum):
    """Nivel de medición SPSS."""
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    SCALE = "scale"


class SpssType(str, Enum):
    """Tipo de variable SPSS."""
    NUMERIC = "numeric"
    STRING = "string"


class EnrichmentProvenance(str, Enum):
    """Origen de un metadato SPSS (ver design.md §4.4)."""
    AUTO_DETERMINISTIC = "auto_deterministic"
    AUTO_LLM = "auto_llm"
    NEEDS_USER_INPUT = "needs_user_input"
    USER_PROVIDED = "user_provided"


class SpssFieldStatus(str, Enum):
    """Estado de confirmación de un bloque de metadatos SPSS."""
    CONFIRMED = "confirmed"
    PENDING = "pending"


class SufficiencyLevel(str, Enum):
    """Nivel de suficiencia analítica de una pregunta interpretable (ver design.md §8.2)."""
    RICA = "rica"
    ADECUADA = "adecuada"
    LIMITADA = "limitada"
    POBRE = "pobre"


class EnrichmentSuggestionType(str, Enum):
    """Catálogo cerrado de sugerencias de enriquecimiento (ver design.md §8.3)."""
    ADD_FOLLOWUP_OPEN_ENDED = "add_followup_open_ended"
    ADD_REASON_FIELD = "add_reason_field"
    SPLIT_DOUBLE_BARRELED = "split_double_barreled"
    CLARIFY_SCOPE = "clarify_scope"
    ADD_MISSING_DIMENSION = "add_missing_dimension"


class TransformId(str, Enum):
    """Transformaciones ejecutables (patrón propose -> decide -> apply, design.md §7)."""
    DROP_COLUMNS = "drop_columns"
    NORMALIZE_SCALE = "normalize_scale"


class ProposalType(str, Enum):
    """Tipo de propuesta. Compatible con TIPOS_PROPUESTA del host."""
    TRANSFORMACION = "transformacion"
    METADATO_ENRIQUECIDO = "metadato_enriquecido"
    KPI_SUGERIDO = "kpi_sugerido"


class ImprovementScope(str, Enum):
    """Scopes de oportunidades de mejora continua (ver design.md §14)."""
    SURVEY = "survey"
    PIPELINE = "pipeline"
    FUTURE_ANALYSIS = "future_analysis"
    VALIDATION_RULE = "validation_rule"
    QUALITY_HEURISTIC = "quality_heuristic"
    PATTERN = "pattern"


class ImprovementStatus(str, Enum):
    """Ciclo de vida de una oportunidad de mejora. El SIS solo emite 'proposed'."""
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class Severity(str, Enum):
    """Severidad de un hallazgo metodológico."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StageStatus(str, Enum):
    """Estado de ejecución de una etapa del pipeline."""
    OK = "ok"
    SKIPPED = "skipped"
    DEGRADED = "degraded"
    FAILED = "failed"


class ResultStatus(str, Enum):
    """Estado global del resultado del pipeline (ver design.md §5.2)."""
    COMPLETED = "completed"
    COMPLETED_DEGRADED = "completed_degraded"
    FAILED = "failed"


class CanonicalQuestionType(str, Enum):
    """
    Tipos canónicos de pregunta (rediseño v2 — encuestas basadas en preguntas, no columnas).

    Conjunto reducido que unifica los 40+ tipos nativos de Google Forms, Microsoft Forms y
    LimeSurvey. Ver backend/survey_intelligence/docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md.
    """
    TEXTO_CORTO = "texto_corto"
    TEXTO_LARGO = "texto_largo"
    OPCION_UNICA = "opcion_unica"
    OPCION_MULTIPLE = "opcion_multiple"
    LIKERT = "likert"
    RANKING = "ranking"
    NUMERICA = "numerica"
    FECHA = "fecha"
    MATRIZ = "matriz"
    ARCHIVO = "archivo"
    # Elementos sin respuesta (text display / equation): metadato, no pregunta con datos.
    NO_DATO = "no_dato"


class SourceEncoding(str, Enum):
    """
    Cómo estaba codificada una columna de origen respecto a su pregunta lógica (rediseño v2).

    Permite reconstruir la respuesta sin ambigüedad y auditar la interpretación.
    """
    SINGLE_CELL = "single_cell"              # 1 celda = 1 respuesta directa
    COMMA_SEPARATED = "comma_separated"      # opción múltiple colapsada por comas (Google)
    SEMICOLON_ORDERED = "semicolon_ordered"  # ranking en 1 celda separado por ';' (Microsoft)
    YES_NO = "yes_no"                        # 1 columna por opción, celda yes/no (LimeSurvey MC)
    RANK_BRACKET = "rank_bracket"            # columna '[Rank k]' (LimeSurvey ranking advanced)
    SCALE_BRACKET = "scale_bracket"          # columna 'stem [ítem]' con valor de escala
    DUAL_BRACKET = "dual_bracket"            # doble corchete 'stem [a][b]' (array dual scale/texts)
    JSON_FILE = "json_file"                  # celda con JSON de archivo (LimeSurvey file upload)
