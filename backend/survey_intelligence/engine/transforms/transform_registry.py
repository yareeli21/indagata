# survey_intelligence/engine/transforms/transform_registry.py
"""
Registro de transformaciones (patrón Registry).

Mapea transform_id -> función de aplicación. Añadir una transformación nueva es
registrar una entrada aquí, sin tocar el apply_engine.
"""
from __future__ import annotations

from typing import Any, Callable

from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.transforms.drop_columns import apply_drop_columns
from survey_intelligence.engine.transforms.models import AppliedTransform
from survey_intelligence.engine.transforms.normalize_scale import apply_normalize_scale

# Firma común: (raw, normalized_names, params) -> (nueva_tabla, registro).
TransformFn = Callable[
    [RawTable, list[str], dict[str, Any]],
    "tuple[RawTable, AppliedTransform]",
]


def _drop_columns_adapter(
    raw: RawTable, names: list[str], params: dict[str, Any]
) -> tuple[RawTable, AppliedTransform]:
    return apply_drop_columns(raw, names, params.get("columnas", []))


def _normalize_scale_adapter(
    raw: RawTable, names: list[str], params: dict[str, Any]
) -> tuple[RawTable, AppliedTransform]:
    return apply_normalize_scale(
        raw, names, params.get("column", ""), params.get("mapping", {})
    )


_REGISTRY: dict[str, TransformFn] = {
    "drop_columns": _drop_columns_adapter,
    "normalize_scale": _normalize_scale_adapter,
}


def get_transform(transform_id: str) -> TransformFn | None:
    """Devuelve la función de la transformación, o None si no está registrada."""
    return _REGISTRY.get(transform_id)


def registered_transforms() -> list[str]:
    return list(_REGISTRY.keys())
