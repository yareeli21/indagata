# survey_intelligence/engine/heuristics/column_proposals.py
"""
Generación de propuestas de eliminación de columnas (patrón propose -> decide -> apply).

Determinístico. Produce TransformProposal(s) que el usuario decide y que, solo si se
aprueban, el apply_engine (Tarea 8) ejecuta de forma reversible.

Dos tipos de propuesta:
  1. drop_columns AGRUPADA: todas las columnas de plataforma en UNA sola propuesta
     (no una por columna).
  2. Propuesta SEPARADA para timestamps, con la salvedad de que su diferencia puede
     derivar el tiempo de respuesta (posible indicador de calidad).

El LLM nunca afirma "esto es basura"; el texto dice "parece no aportar al análisis
semántico, ¿lo elimino?" con justificación visible. El usuario decide.
"""
from __future__ import annotations

import json
import re

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enums import ColumnClass, ProposalType, TransformId
from survey_intelligence.contracts.result import TransformProposal
from survey_intelligence.ports.ids_port import IdGeneratorPort

# Patrón para reconocer columnas de marca de tiempo por su nombre.
# Nota: 'start'/'end' solos NO cuentan (evita 'Start language'); deben ir con
# date/time o ser palabras inequívocamente temporales.
_TIMESTAMP = re.compile(
    r"\b(date|fecha|hora|timestamp|marca temporal|"
    r"started|submitted|finaliza|last action|"
    r"start time|end time|completion time)\b",
    re.IGNORECASE,
)


def _is_timestamp(variable) -> bool:
    """
    Una columna es de marca de tiempo si su nombre lo sugiere O el profiler detectó
    tipo datetime. Usar ambas señales es más robusto que solo el nombre.
    """
    from survey_intelligence.contracts.enums import DataType

    if variable.inferred_data_type == DataType.DATETIME:
        return True
    return bool(_TIMESTAMP.search(variable.raw_header))


def build_column_proposals(
    canonical: CanonicalSurveyModel,
    ids: IdGeneratorPort,
) -> list[TransformProposal]:
    """
    Construye las propuestas de eliminación de columnas a partir del Canonical.

    Returns:
        Lista de TransformProposal (0, 1 o 2 propuestas).
    """
    platform_vars = [
        v for v in canonical.variables
        if v.column_class == ColumnClass.PLATFORM_METADATA
    ]
    if not platform_vars:
        return []

    # Separar timestamps del resto de columnas administrativas.
    timestamp_vars = [v for v in platform_vars if _is_timestamp(v)]
    other_vars = [v for v in platform_vars if not _is_timestamp(v)]

    proposals: list[TransformProposal] = []

    # ── Propuesta 1: columnas administrativas no-temporales (agrupada) ──────────
    if other_vars:
        headers = [v.raw_header for v in other_vars]
        names = [v.normalized_name for v in other_vars]
        proposals.append(
            TransformProposal(
                proposal_id=ids.new_id("prop-"),
                tipo=ProposalType.TRANSFORMACION,
                descripcion=(
                    f"{len(headers)} columnas parecen metadatos de la plataforma "
                    f"(no respuestas a preguntas): {', '.join(headers)}."
                ),
                accion_sugerida=(
                    "ACEPTAR = eliminar estas columnas del dataset. "
                    "RECHAZAR = conservarlas."
                ),
                justificacion=(
                    "No corresponden a ningún ítem del instrumento; son control interno "
                    "de la herramienta y no aportan valor semántico ni analítico."
                ),
                impacto_esperado=(
                    "Dataset más limpio; embeddings y chunking enfocados solo en "
                    "preguntas reales."
                ),
                valor_original=json.dumps(headers, ensure_ascii=False),
                valor_propuesto=json.dumps(
                    {"transform_id": TransformId.DROP_COLUMNS.value, "columnas": names},
                    ensure_ascii=False,
                ),
            )
        )

    # ── Propuesta 2: timestamps (separada, con salvedad de tiempo de respuesta) ──
    if timestamp_vars:
        headers = [v.raw_header for v in timestamp_vars]
        names = [v.normalized_name for v in timestamp_vars]
        proposals.append(
            TransformProposal(
                proposal_id=ids.new_id("prop-"),
                tipo=ProposalType.TRANSFORMACION,
                descripcion=(
                    f"{len(headers)} columnas de marca de tiempo: {', '.join(headers)}."
                ),
                accion_sugerida=(
                    "ACEPTAR = eliminar estas columnas del dataset. "
                    "RECHAZAR = conservarlas (por ejemplo, para derivar el tiempo de "
                    "respuesta a partir de ellas)."
                ),
                justificacion=(
                    "Normalmente no aportan al análisis semántico, pero su diferencia "
                    "(fin menos inicio) puede derivar el tiempo de respuesta, un posible "
                    "indicador de calidad (respuestas apresuradas)."
                ),
                impacto_esperado=(
                    "Dataset más limpio si se eliminan; o una nueva variable derivada "
                    "'tiempo_respuesta' si decides conservarlas."
                ),
                valor_original=json.dumps(headers, ensure_ascii=False),
                valor_propuesto=json.dumps(
                    {"transform_id": TransformId.DROP_COLUMNS.value, "columnas": names},
                    ensure_ascii=False,
                ),
            )
        )

    return proposals
