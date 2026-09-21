# survey_intelligence/engine/question_typing.py
"""
Motor de TIPIFICACIÓN de preguntas (rediseño v2).

Determina el tipo canónico de una pregunta combinando señales (multi-señal), NO solo
el encabezado: plataforma + patrón de encabezado + forma de los valores observados.

Funciones PURAS y determinísticas: no tocan BD, disco, LLM ni el pipeline. Este módulo
NO se cablea aún; lo consumirán question_grouping y (más tarde) S2 v2.

Ver docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md (detección multi-señal).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from survey_intelligence.contracts.enums import CanonicalQuestionType as QT

# ── Señales de valores (forma de las celdas de una columna) ──────────────────

_YES_TOKENS = {"yes", "sí", "si", "true", "1", "x", "checked", "seleccionado"}
_NO_TOKENS = {"no", "false", "0", "", "unchecked"}
_DATE_RE = re.compile(
    r"^\s*\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}"           # 13/3/2026, 2026-03-13
    r"(?:[ T]\d{1,2}:\d{2}(:\d{2})?\s*([ap]\.?\s?m\.?)?)?\s*$",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"^\s*-?\d+([.,]\d+)?\s*$")
_JSON_FILE_RE = re.compile(r'"(filename|name|ext)"\s*:', re.IGNORECASE)


@dataclass(frozen=True)
class TypeVerdict:
    """Resultado de tipificar una pregunta."""
    type: QT
    confidence: float
    fallback: QT | None = None
    reason: str = ""


def _non_empty(values: list[str]) -> list[str]:
    return [v.strip() for v in values if v is not None and str(v).strip()]


def is_yes_no_column(values: list[str]) -> bool:
    """
    True si la columna es binaria yes/no (opción múltiple exportada en columnas).

    Nota: una opción no seleccionada por nadie tiene la columna llena de 'No'
    (sin ningún 'Yes'); sigue siendo una columna yes/no válida. Por eso basta con
    que el dominio no vacío sea subconjunto de los tokens binarios y contenga al
    menos un token reconocido (yes o no) que NO sea solo la cadena vacía/"0".
    """
    ne = _non_empty(values)
    if not ne:
        return False
    toks = {v.lower() for v in ne}
    if not (toks <= (_YES_TOKENS | _NO_TOKENS)):
        return False
    # Debe contener al menos un token binario explícito (yes/no/sí/true/false),
    # para no confundir con una columna de puros "1" (numérica) o vacíos.
    explicit = {"yes", "no", "sí", "si", "true", "false", "checked", "unchecked", "seleccionado"}
    return bool(toks & explicit)


def looks_numeric(values: list[str]) -> bool:
    ne = _non_empty(values)
    return bool(ne) and all(_NUMERIC_RE.match(v) for v in ne)


def looks_date(values: list[str]) -> bool:
    ne = _non_empty(values)
    return bool(ne) and all(_DATE_RE.match(v) for v in ne)


def looks_json_file(values: list[str]) -> bool:
    ne = _non_empty(values)
    return bool(ne) and any(_JSON_FILE_RE.search(v) for v in ne)


def has_comma_multi(values: list[str]) -> bool:
    """Heurística: varias celdas con comas → opción múltiple colapsada en 1 celda."""
    ne = _non_empty(values)
    if len(ne) < 3:
        return False
    with_comma = sum(1 for v in ne if "," in v)
    return with_comma / len(ne) >= 0.3


def has_semicolon_order(values: list[str]) -> bool:
    """Heurística: celdas con ';' separando opciones ordenadas → ranking (Microsoft)."""
    ne = _non_empty(values)
    if len(ne) < 3:
        return False
    with_semi = sum(1 for v in ne if ";" in v)
    return with_semi / len(ne) >= 0.3


def avg_len(values: list[str]) -> float:
    ne = _non_empty(values)
    return (sum(len(v) for v in ne) / len(ne)) if ne else 0.0


def unique_ratio(values: list[str]) -> float:
    ne = _non_empty(values)
    return (len(set(ne)) / len(ne)) if ne else 0.0


# ── Tipificación de una columna individual (señal base) ──────────────────────

_FREE_TEXT_MIN_AVG_CHARS = 40
_FREE_TEXT_MIN_UNIQUE_RATIO = 0.6
_LIKERT_MAX_CARDINALITY = 12  # pocas categorías → escala/opción; muchas → texto/numérica


def type_single_column(header: str, values: list[str]) -> TypeVerdict:
    """
    Tipifica una columna que representa una pregunta de UNA sola columna.

    (La reagrupación multi-columna la decide question_grouping; aquí se resuelve el
    caso 1-columna y se ofrecen las señales para el caso multi-columna.)
    """
    ne = _non_empty(values)

    # FUERA DE ALCANCE: archivo → se trata como texto (evidencia textual), sin tipo dedicado.
    if looks_json_file(values):
        return TypeVerdict(QT.TEXTO_CORTO, 0.4, reason="out_of_scope:archivo → texto")
    if looks_date(values):
        return TypeVerdict(QT.FECHA, 0.9, reason="celdas con formato de fecha/hora")
    # FUERA DE ALCANCE: ranking en 1 celda (';') → se trata como opción múltiple.
    if has_semicolon_order(values):
        return TypeVerdict(QT.OPCION_MULTIPLE, 0.5, reason="out_of_scope:ranking → opcion_multiple")
    if has_comma_multi(values):
        return TypeVerdict(QT.OPCION_MULTIPLE, 0.7, fallback=QT.OPCION_UNICA, reason="celdas con comas (multi)")
    if looks_numeric(values):
        card = len(set(ne))
        if 0 < card <= _LIKERT_MAX_CARDINALITY:
            return TypeVerdict(QT.LIKERT, 0.6, fallback=QT.NUMERICA, reason="numérica de baja cardinalidad")
        return TypeVerdict(QT.NUMERICA, 0.8, reason="valores numéricos variados")

    # Texto largo: la longitud promedio alta es la señal dominante (la variedad es
    # secundaria; respuestas abiertas repetidas siguen siendo texto largo).
    if avg_len(values) >= _FREE_TEXT_MIN_AVG_CHARS:
        conf = 0.8 if unique_ratio(values) >= _FREE_TEXT_MIN_UNIQUE_RATIO else 0.65
        return TypeVerdict(QT.TEXTO_LARGO, conf, reason="celdas largas")

    # Pocas categorías distintas → opción única; si no, texto corto.
    card = len(set(ne))
    if 0 < card <= _LIKERT_MAX_CARDINALITY and avg_len(values) < _FREE_TEXT_MIN_AVG_CHARS:
        return TypeVerdict(QT.OPCION_UNICA, 0.6, fallback=QT.TEXTO_CORTO, reason="baja cardinalidad categórica")
    return TypeVerdict(QT.TEXTO_CORTO, 0.5, fallback=QT.OPCION_UNICA, reason="texto breve")


# ── Tipificación de un grupo multi-columna (mismo stem) ──────────────────────

def type_multi_column(
    stem: str,
    sibling_values: list[list[str]],
    has_rank: bool = False,
    has_scale_axis: bool = False,
) -> TypeVerdict:
    """
    Tipifica una pregunta materializada en VARIAS columnas hermanas (mismo stem).

    sibling_values: lista de columnas (cada una es la lista de valores de esa columna).
    has_rank/has_scale_axis: si los encabezados traían [Rank k] / [Scale k].
    """
    # FUERA DE ALCANCE: ranking multi-columna ([Rank k]) → opción múltiple genérica.
    if has_rank:
        return TypeVerdict(QT.OPCION_MULTIPLE, 0.4, reason="out_of_scope:ranking [Rank k] → opcion_multiple")
    # FUERA DE ALCANCE: doble eje ([Scale k], array dual scale) → matriz genérica.
    if has_scale_axis:
        return TypeVerdict(QT.MATRIZ, 0.4, reason="out_of_scope:doble corchete [Scale k] → matriz")

    # Si todas las columnas hermanas son yes/no → opción múltiple (LimeSurvey MC).
    if sibling_values and all(is_yes_no_column(col) for col in sibling_values):
        return TypeVerdict(QT.OPCION_MULTIPLE, 0.9, reason="columnas hermanas binarias yes/no")

    # Si todas son numéricas de baja cardinalidad o categóricas cortas → likert (escala común).
    def _cat_or_scale(col: list[str]) -> bool:
        ne = _non_empty(col)
        return bool(ne) and (looks_numeric(col) or len(set(ne)) <= _LIKERT_MAX_CARDINALITY)

    if sibling_values and all(_cat_or_scale(col) for col in sibling_values):
        return TypeVerdict(QT.LIKERT, 0.75, fallback=QT.MATRIZ, reason="ítems con escala común")

    # En otro caso, es una matriz genérica (p.ej. array texts / array by column).
    return TypeVerdict(QT.MATRIZ, 0.6, reason="columnas hermanas heterogéneas")
