# survey_intelligence/engine/transforms/models.py
"""
Modelos del motor de transformaciones (patrón propose -> decide -> apply).

Una TransformDecision es lo que el usuario aprueba. Un AppliedTransform es el
registro reversible de un cambio ya ejecutado (guarda lo necesario para deshacer).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TransformDecision:
    """
    Decisión de aplicar una transformación aprobada por el usuario.

    Attributes:
        transform_id: identificador de la transformación ('drop_columns', ...).
        params:       parámetros (p. ej. {'columnas': [...]}).
        proposal_id:  propuesta de origen (trazabilidad; opcional).
    """
    transform_id: str
    params: dict[str, Any]
    proposal_id: str | None = None


@dataclass(frozen=True)
class AppliedTransform:
    """
    Registro reversible de una transformación ejecutada.

    Attributes:
        transform_id: qué se aplicó.
        params:       con qué parámetros.
        undo_data:    datos necesarios para revertir (p. ej. columnas eliminadas
                      con sus valores; mapa de valores originales por celda).
        summary:      descripción legible del cambio (para diagnósticos).
    """
    transform_id: str
    params: dict[str, Any]
    undo_data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
