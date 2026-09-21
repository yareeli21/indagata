# survey_intelligence/pipeline/stages/s5_codebook_resolution.py
"""
Etapa S5 — Resolución Determinística de Codebook (sin RAG).

Sustituye la aproximación RAG vectorial por coincidencia exacta y normalizada
$O(1)$ sobre el CodebookModel estructurado.

Funcionalidad:
  1. Para cada variable del Canonical, busca coincidencia en el codebook por
     raw_header o normalized_name.
  2. Si coincide:
     - Convierte la variable en INTERPRETABLE (actualiza SufficiencyVerdict).
     - Actualiza el texto de la pregunta en CanonicalQuestion con la etiqueta del codebook.
     - Si el codebook aporta etiquetas de valor (categorías), enriquece DetectedScale
       para que el SPSS mapper y las etapas posteriores dispongan de las etiquetas.
  3. Si no hay codebook o ninguna variable coincide, opera limpiamente sin romper nada.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from survey_intelligence.contracts.canonical import (
    CanonicalQuestion,
    CanonicalSurveyModel,
    CanonicalVariable,
    DetectedScale,
)
from survey_intelligence.contracts.codebook import CodebookEntry, CodebookModel
from survey_intelligence.contracts.enums import ScaleKind
from survey_intelligence.engine.heuristics.context_sufficiency import SufficiencyVerdict


@dataclass(frozen=True)
class CodebookResolution:
    variable_id: str
    entry_name: str
    label: str
    value_labels: dict[str, str]
    resolved: bool = True


@dataclass(frozen=True)
class CodebookResolutionResult:
    canonical: CanonicalSurveyModel
    verdicts: dict[str, SufficiencyVerdict]
    resolutions: dict[str, CodebookResolution] = field(default_factory=dict)
    skipped: bool = False
    reason: str | None = None


def resolve_codebook(
    canonical: CanonicalSurveyModel,
    verdicts: dict[str, SufficiencyVerdict],
    codebook: CodebookModel | None,
) -> CodebookResolutionResult:
    """
    Ejecuta la resolución determinística de variables contra el codebook.

    Args:
        canonical: Modelo canónico actual.
        verdicts: Veredictos de suficiencia de S4.
        codebook: Diccionario estructurado opcional.
    """
    if codebook is None or not codebook.entries:
        return CodebookResolutionResult(
            canonical=canonical,
            verdicts=verdicts,
            resolutions={},
            skipped=True,
            reason="no_codebook",
        )

    updated_verdicts = dict(verdicts)
    resolutions: dict[str, CodebookResolution] = {}
    updated_variables: list[CanonicalVariable] = []
    
    # Mapa de variable_id a entry encontrada
    matched_entries: dict[str, CodebookEntry] = {}

    for var in canonical.variables:
        entry = codebook.lookup(var.raw_header)
        if entry is None:
            entry = codebook.lookup(var.normalized_name)

        if entry is not None:
            matched_entries[var.variable_id] = entry
            resolutions[var.variable_id] = CodebookResolution(
                variable_id=var.variable_id,
                entry_name=entry.name,
                label=entry.label,
                value_labels=entry.value_labels,
                resolved=True,
            )
            # Actualizar veredicto a interpretable con evidencia
            updated_verdicts[var.variable_id] = SufficiencyVerdict(
                variable_id=var.variable_id,
                is_interpretable=True,
                missing_information=[],
                why_not_interpretable=None,
                required_to_interpret=[],
            )

            # Enriquecer detected_scale si el codebook define categorías de valores
            detected_scale = var.detected_scale
            if entry.value_labels:
                points = len(entry.value_labels)
                kind = ScaleKind.CATEGORICAL
                if points == 2:
                    kind = ScaleKind.BINARY
                elif points in (5, 7):
                    kind = ScaleKind.LIKERT
                detected_scale = DetectedScale(
                    kind=kind,
                    points=points,
                    labels=list(entry.value_labels.values()),
                    consistent=True,
                )

            # Si el raw_header original era corto/técnico y el codebook trae una etiqueta descriptiva
            new_header = entry.label if (len(entry.label) > len(var.raw_header) or var.raw_header.lower() == var.normalized_name.lower()) else var.raw_header

            updated_variables.append(
                var.model_copy(update={
                    "raw_header": new_header,
                    "detected_scale": detected_scale,
                })
            )
        else:
            updated_variables.append(var)

    # Actualizar texto en CanonicalQuestions que coincidan
    updated_questions: list[CanonicalQuestion] = []
    for q in canonical.questions:
        # Si la pregunta tiene una sola variable asociada y fue resuelta
        if len(q.variable_ids) == 1 and q.variable_ids[0] in matched_entries:
            entry = matched_entries[q.variable_ids[0]]
            new_text = entry.label or q.text
            updated_questions.append(
                q.model_copy(update={
                    "text": new_text,
                    "length_chars": len(new_text),
                    "length_words": len(new_text.split()),
                })
            )
        else:
            updated_questions.append(q)

    resolved_canonical = canonical.model_copy(update={
        "variables": updated_variables,
        "questions": updated_questions,
    })

    return CodebookResolutionResult(
        canonical=resolved_canonical,
        verdicts=updated_verdicts,
        resolutions=resolutions,
        skipped=False,
        reason=None,
    )
