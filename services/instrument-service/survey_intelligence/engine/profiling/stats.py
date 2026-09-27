# survey_intelligence/engine/profiling/stats.py
"""
Estadística de distribución y detección de tipo (determinístico, sin LLM).

Calcula por columna: no nulos, nulos, ratio de nulos, cardinalidad, top valores;
detecta multi_select por delimitador (';' Microsoft, ', ' Google); infiere tipo
(numeric, datetime, multi_select, free_text, ...); y estima nulos estructurales
(los generados por lógica de salto condicional).
"""
from __future__ import annotations

import re
from collections import Counter

from survey_intelligence.contracts.canonical import ValueDistribution
from survey_intelligence.contracts.enums import DataType

_NUMERIC = re.compile(r"^-?\d+([.,]\d+)?$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2})|^\d{1,2}/\d{1,2}/\d{2,4}")

# Delimitadores de multi_select por plataforma.
_MULTI_DELIMITERS = (";", ", ")


def value_distribution(values: list[str], structural_null: int = 0) -> ValueDistribution:
    non_empty = [v for v in values if v and v.strip()]
    n_null = len(values) - len(non_empty)
    counter = Counter(non_empty)
    top = [{"value": v, "count": c} for v, c in counter.most_common(5)]
    return ValueDistribution(
        n_non_null=len(non_empty),
        n_null=n_null,
        null_ratio=round(n_null / len(values), 4) if values else 0.0,
        cardinality=len(counter),
        n_structural_null=structural_null,
        top_values=top,
    )


def _looks_multi_select(values: list[str]) -> bool:
    """Muchas celdas contienen un delimitador repetido -> opción múltiple colapsada."""
    non_empty = [v for v in values if v and v.strip()]
    if len(non_empty) < 2:
        return False
    for delim in _MULTI_DELIMITERS:
        hits = sum(1 for v in non_empty if delim in v and len(v.split(delim)) >= 2)
        if hits / len(non_empty) >= 0.6:
            return True
    return False


def split_multi_select(value: str) -> list[str]:
    """Divide una celda multi_select en sus opciones, probando delimitadores."""
    for delim in _MULTI_DELIMITERS:
        if delim in value:
            parts = [p.strip() for p in value.split(delim) if p.strip()]
            if len(parts) >= 2:
                return parts
    return [value.strip()] if value.strip() else []


def infer_data_type(
    values: list[str], has_scale: bool, is_free_text: bool, scale_kind: str | None = None
) -> DataType:
    """
    Infiere el tipo de dato de una columna.

    Orden de decisión:
      1. escala detectada -> ordinal (Likert) o nominal (binaria)
      2. multi_select por delimitador
      3. datetime
      4. numérico
      5. free_text (marcado por S2) o nominal
    """
    non_empty = [v for v in values if v and v.strip()]
    if not non_empty:
        return DataType.UNKNOWN

    if has_scale:
        # Una escala binaria (Sí/No) es nominal; una Likert es ordinal.
        if scale_kind == "binary":
            return DataType.NOMINAL
        return DataType.ORDINAL

    if _looks_multi_select(values):
        return DataType.MULTI_SELECT

    if all(_DATETIME.search(v) for v in non_empty):
        return DataType.DATETIME

    if all(_NUMERIC.match(v) for v in non_empty):
        return DataType.NUMERIC

    if is_free_text:
        return DataType.FREE_TEXT

    return DataType.NOMINAL


def estimate_structural_nulls(
    values: list[str], gate_values: list[str] | None
) -> int:
    """
    Estima nulos estructurales: celdas vacías cuya fila tiene un valor 'gate' que
    justifica el salto (p. ej. la pregunta anterior fue 'No').

    Sin una columna gate no se puede afirmar; devuelve 0 (se refina con el LLM/S4).
    Aquí se ofrece la utilidad para cuando el caller identifique la pregunta gate.
    """
    if gate_values is None:
        return 0
    structural = 0
    for val, gate in zip(values, gate_values):
        if (not val or not val.strip()) and gate.strip().lower() in {"no", "no estoy seguro(a)"}:
            structural += 1
    return structural
