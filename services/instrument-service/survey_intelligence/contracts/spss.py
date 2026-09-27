# survey_intelligence/contracts/spss.py
"""
Contrato de metadatos SPSS (design.md §4.3, §9).

Diccionario de variables estándar que habilita la exportación a .SAV.
Cada campo lleva su origen (`enrichment_provenance`) y estado, formalizando la
distinción "automático vs. usuario". Donde no hay certeza -> needs_user_input,
NO se inventa el valor.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.enums import (
    EnrichmentProvenance,
    Measure,
    SpssFieldStatus,
    SpssType,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SpssVariableMetadata(BaseModel):
    """
    Diccionario SPSS de una variable.

    - value_labels:  código -> etiqueta (p. ej. {"1": "Totalmente desacuerdo"}).
    - value_encoding: texto observado -> código (p. ej. {"De acuerdo": 4}); permite
      escribir el .SAV numérico y mapea variantes mal escritas al código canónico.
    """
    model_config = _FROZEN

    variable_id: str
    name: str | None = None
    variable_label: str | None = None
    measure: Measure | None = None
    type: SpssType | None = None
    value_labels: dict[str, str] = Field(default_factory=dict)
    value_encoding: dict[str, int] = Field(default_factory=dict)
    missing_values: list[str] = Field(default_factory=list)

    enrichment_provenance: EnrichmentProvenance = EnrichmentProvenance.NEEDS_USER_INPUT
    confidence: float | None = None
    status: SpssFieldStatus = SpssFieldStatus.PENDING
