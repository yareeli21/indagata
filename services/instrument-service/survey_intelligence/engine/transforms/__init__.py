# survey_intelligence/engine/transforms/__init__.py
"""Motor de transformaciones ejecutables (propose -> decide -> apply)."""
from __future__ import annotations

from survey_intelligence.engine.transforms.apply_engine import (
    ApplyResult,
    apply_decisions,
    rebuild_canonical_after_apply,
)
from survey_intelligence.engine.transforms.drop_columns import (
    apply_drop_columns,
    undo_drop_columns,
)
from survey_intelligence.engine.transforms.models import (
    AppliedTransform,
    TransformDecision,
)
from survey_intelligence.engine.transforms.normalize_scale import (
    apply_normalize_scale,
    undo_normalize_scale,
)
from survey_intelligence.engine.transforms.transform_registry import (
    get_transform,
    registered_transforms,
)

__all__ = [
    "TransformDecision",
    "AppliedTransform",
    "ApplyResult",
    "apply_decisions",
    "rebuild_canonical_after_apply",
    "apply_drop_columns",
    "undo_drop_columns",
    "apply_normalize_scale",
    "undo_normalize_scale",
    "get_transform",
    "registered_transforms",
]
