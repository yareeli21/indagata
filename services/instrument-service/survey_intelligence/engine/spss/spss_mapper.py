# survey_intelligence/engine/spss/spss_mapper.py
"""
SPSS mapper determinístico (Tarea 9).

Deriva un BORRADOR del diccionario SPSS desde el Canonical, sin LLM. Rellena lo que
se puede afirmar con certeza y lo marca como enrichment_provenance=auto_deterministic.
Lo que no se puede decidir determinísticamente queda como needs_user_input (lo
completará el LLM en S7 o el usuario).

Puntos clave:
  - value_labels: código -> etiqueta (a partir del orden canónico de la escala).
  - value_encoding: texto observado -> código; las variantes mal escritas (typos)
    detectadas se mapean al MISMO código que su forma canónica, limpiando el dato.
  - measure: ordinal (Likert), nominal (binaria/nominal/multi_select), scale (numérica).
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import CanonicalSurveyModel, CanonicalVariable
from survey_intelligence.contracts.enums import (
    ColumnClass,
    DataType,
    EnrichmentProvenance,
    Measure,
    ScaleKind,
    SpssFieldStatus,
    SpssType,
)
from survey_intelligence.contracts.spss import SpssVariableMetadata
from survey_intelligence.engine.profiling.scale_detector import canonical_scale_order
from survey_intelligence.engine.spss.spss_validator import sanitize_spss_name

# Mapa tipo de dato -> nivel de medición SPSS.
_MEASURE_BY_TYPE = {
    DataType.ORDINAL: Measure.ORDINAL,
    DataType.NUMERIC: Measure.SCALE,
    DataType.NOMINAL: Measure.NOMINAL,
    DataType.BOOLEAN: Measure.NOMINAL,
    DataType.MULTI_SELECT: Measure.NOMINAL,
    DataType.FREE_TEXT: Measure.NOMINAL,
    DataType.DATETIME: Measure.SCALE,
}


def _variable_label(var: CanonicalVariable) -> str:
    """El label SPSS es el ítem de la matriz si existe, si no el encabezado."""
    if var.matrix_group is not None:
        return var.matrix_group.item
    return var.raw_header


def _build_value_labels_and_encoding(
    var: CanonicalVariable,
) -> tuple[dict[str, str], dict[str, int]]:
    """
    Construye value_labels (código->etiqueta) y value_encoding (texto->código).

    Usa el orden canónico de la escala para asignar códigos 1..N. Las anomalías de
    typo se añaden al encoding apuntando al código de su canonical_guess.
    """
    scale = var.detected_scale
    if scale is None or not scale.labels:
        return {}, {}

    # Determinar el orden canónico de la escala (para códigos consistentes).
    if scale.kind == ScaleKind.LIKERT:
        order = canonical_scale_order(scale.labels) or list(scale.labels)
    else:
        # Binaria/otra: orden observado estable.
        order = list(scale.labels)

    value_labels: dict[str, str] = {}
    value_encoding: dict[str, int] = {}
    for idx, label in enumerate(order, start=1):
        value_labels[str(idx)] = label
        value_encoding[label] = idx

    # Mapear typos al código de su etiqueta canónica.
    for anomaly in scale.anomalies:
        canonical = anomaly.canonical_guess
        if canonical in value_encoding:
            value_encoding[anomaly.value] = value_encoding[canonical]

    return value_labels, value_encoding


def map_variable(var: CanonicalVariable) -> SpssVariableMetadata:
    """Deriva el borrador SPSS de una variable."""
    # Columnas de plataforma: se dejan mínimas (el host puede excluirlas del .SAV).
    if var.column_class == ColumnClass.PLATFORM_METADATA:
        return SpssVariableMetadata(
            variable_id=var.variable_id,
            name=sanitize_spss_name(var.normalized_name),
            variable_label=var.raw_header,
            measure=Measure.NOMINAL,
            type=SpssType.STRING,
            enrichment_provenance=EnrichmentProvenance.AUTO_DETERMINISTIC,
            confidence=1.0,
            status=SpssFieldStatus.CONFIRMED,
        )

    value_labels, value_encoding = _build_value_labels_and_encoding(var)
    dtype = var.inferred_data_type
    measure = _MEASURE_BY_TYPE.get(dtype, Measure.NOMINAL)

    # Una escala binaria (Sí/No, Yes/No) es NOMINAL: no tiene orden intrínseco,
    # aunque el tipo de dato se haya inferido como ordinal.
    if var.detected_scale is not None and var.detected_scale.kind == ScaleKind.BINARY:
        measure = Measure.NOMINAL

    # Tipo SPSS: numérico si hay codificación de valores o es numérico/ordinal;
    # string para texto libre y multi_select (se expande después).
    if value_encoding or dtype in (DataType.NUMERIC, DataType.ORDINAL):
        spss_type = SpssType.NUMERIC
    else:
        spss_type = SpssType.STRING

    # Provenance: determinístico si tenemos una base sólida (escala o tipo claro);
    # si el tipo es desconocido, se deja para el LLM/usuario.
    if dtype == DataType.UNKNOWN:
        provenance = EnrichmentProvenance.NEEDS_USER_INPUT
        status = SpssFieldStatus.PENDING
        confidence = None
    else:
        provenance = EnrichmentProvenance.AUTO_DETERMINISTIC
        status = SpssFieldStatus.CONFIRMED
        confidence = 1.0

    return SpssVariableMetadata(
        variable_id=var.variable_id,
        name=sanitize_spss_name(var.normalized_name),
        variable_label=_variable_label(var),
        measure=measure,
        type=spss_type,
        value_labels=value_labels,
        value_encoding=value_encoding,
        missing_values=[],
        enrichment_provenance=provenance,
        confidence=confidence,
        status=status,
    )


def build_spss_dictionary(canonical: CanonicalSurveyModel) -> list[SpssVariableMetadata]:
    """Deriva el borrador del diccionario SPSS para todas las variables."""
    return [map_variable(v) for v in canonical.variables]
