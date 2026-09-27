# survey_intelligence/pipeline/stages/s7_semantic_enrichment.py
"""
Etapa S7 — Enriquecimiento semántico (LLM) + validador anti-invención.

Produce, por variable interpretable: constructo, rol, tags, chunking_hint y
analytical_sufficiency. Fusiona el SPSS determinístico (S9-mapper) con la cara
semántica en el EnrichedVariable.

VALIDADOR ANTI-INVENCIÓN (restricción crítica, paso 2):
  - Las variables marcadas INSUFFICIENT_CONTEXT por S4 se mantienen así, con su
    diagnóstico; el LLM NO puede convertirlas en interpretables (salvo evidencia,
    que en Nivel 1 no existe sin RAG).
  - Si el LLM propone significado para una variable sin evidencia, se DEGRADA a
    INSUFFICIENT_CONTEXT. La IA no tiene la última palabra; la tiene la evidencia.

Degradable: si el LLM falla, las variables interpretables quedan con su SPSS
determinístico y sin cara semántica; degraded=True.
"""
from __future__ import annotations

from dataclasses import dataclass

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enriched import (
    AnalyticalSufficiency,
    ChunkingHint,
    EnrichedVariable,
    EnrichmentSuggestion,
    SemanticEnrichment,
    SurveySummary,
)
from survey_intelligence.contracts.enums import (
    ColumnClass,
    EnrichmentSuggestionType,
    InterpretabilityStatus,
    SufficiencyLevel,
)
from survey_intelligence.contracts.spss import SpssVariableMetadata
from survey_intelligence.engine.heuristics.context_sufficiency import SufficiencyVerdict
from survey_intelligence.engine.parsing.robust_json import JsonParseError, parse_json_object
from survey_intelligence.engine.prompts.enrichment_prompt import build_enrichment_prompt
from survey_intelligence.ports.llm_port import LLMPort

_VALID_SUFFICIENCY = {e.value for e in SufficiencyLevel}
_VALID_SUGGESTION = {e.value for e in EnrichmentSuggestionType}


@dataclass
class EnrichmentResult:
    variables: list[EnrichedVariable]
    survey_summary: SurveySummary | None
    degraded: bool
    llm_calls: int


def _has_evidence(canonical: CanonicalSurveyModel, variable_id: str) -> bool:
    """
    Determina si una variable tiene evidencia para ser interpretable.
    Es el guardián del validador anti-invención.
    """
    var = next((v for v in canonical.variables if v.variable_id == variable_id), None)
    if var is None:
        return False
    if var.column_class == ColumnClass.PLATFORM_METADATA:
        return True
    has_header = len(var.raw_header.split()) >= 3 or "?" in var.raw_header or "¿" in var.raw_header
    has_matrix = var.matrix_group is not None
    has_scale = var.detected_scale is not None and bool(var.detected_scale.labels)
    is_free_text = var.column_class == ColumnClass.FREE_TEXT
    return has_header or has_matrix or has_scale or is_free_text


def _insufficient_variable(
    variable_id: str, spss: SpssVariableMetadata | None, verdict: SufficiencyVerdict | None
) -> EnrichedVariable:
    """Construye un EnrichedVariable INSUFFICIENT_CONTEXT con su diagnóstico."""
    missing = verdict.missing_information if verdict else ["información suficiente para interpretar"]
    why = verdict.why_not_interpretable if verdict else "No hay evidencia para interpretar la variable."
    required = verdict.required_to_interpret if verdict else ["codebook o enunciado del ítem"]
    return EnrichedVariable(
        variable_id=variable_id,
        interpretability_status=InterpretabilityStatus.INSUFFICIENT_CONTEXT,
        spss_metadata=spss,
        semantic_enrichment=None,
        missing_information=missing,
        why_not_interpretable=why,
        required_to_interpret=required,
    )


def _build_sufficiency(node: dict) -> AnalyticalSufficiency | None:
    if not isinstance(node, dict):
        return None
    level = node.get("level")
    if level not in _VALID_SUFFICIENCY:
        return None
    suggestion = None
    sug = node.get("enrichment_suggestion")
    if isinstance(sug, dict) and sug.get("type") in _VALID_SUGGESTION:
        suggestion = EnrichmentSuggestion(
            type=EnrichmentSuggestionType(sug["type"]),
            proposed_item=str(sug.get("proposed_item", "")),
            rationale=str(sug.get("rationale", "")),
        )
    return AnalyticalSufficiency(
        level=SufficiencyLevel(level),
        reason=str(node.get("reason", "")),
        what_it_could_reveal=node.get("what_it_could_reveal"),
        enrichment_suggestion=suggestion,
    )


def run_enrichment(
    canonical: CanonicalSurveyModel,
    verdicts: dict[str, SufficiencyVerdict],
    spss_by_id: dict[str, SpssVariableMetadata],
    llm: LLMPort,
    temperature: float = 0.1,
    language_hint: str = "es",
) -> EnrichmentResult:
    """Ejecuta S7 con validador anti-invención."""
    # Variables a enriquecer (interpretables según S4) vs insuficientes.
    insufficient_ids = [vid for vid, v in verdicts.items() if not v.is_interpretable]

    # Vista de variables para el LLM (solo las que no son plataforma).
    variables_view = []
    for v in canonical.variables:
        if v.column_class == ColumnClass.PLATFORM_METADATA:
            continue
        text = v.matrix_group.item if v.matrix_group else v.raw_header
        variables_view.append({
            "variable_id": v.variable_id,
            "text": text,
            "scale_labels": v.detected_scale.labels if v.detected_scale else [],
            "data_type": v.inferred_data_type.value,
        })

    llm_calls = 0
    degraded = False
    data = None
    if variables_view:
        system, user = build_enrichment_prompt(variables_view, insufficient_ids, language_hint)
        for _attempt in range(2):
            try:
                llm_calls += 1
                raw = llm.complete_json(system_prompt=system, user_prompt=user, temperature=temperature)
                data = parse_json_object(raw)
                break
            except (RuntimeError, JsonParseError):
                data = None
                continue
        if data is None:
            degraded = True

    llm_by_id: dict[str, dict] = {}
    survey_summary = None
    if data is not None:
        for item in data.get("variables", []):
            if isinstance(item, dict) and item.get("variable_id"):
                llm_by_id[item["variable_id"]] = item
        summ = data.get("survey_summary")
        if isinstance(summ, dict):
            survey_summary = SurveySummary(
                purpose_inferred=summ.get("purpose_inferred"),
                confidence=summ.get("confidence"),
                provenance="llm+metadata",
            )

    enriched: list[EnrichedVariable] = []
    for var in canonical.variables:
        vid = var.variable_id
        spss = spss_by_id.get(vid)
        verdict = verdicts.get(vid)

        # Columnas de plataforma: interpretable por rol, sin enriquecimiento semántico.
        if var.column_class == ColumnClass.PLATFORM_METADATA:
            enriched.append(EnrichedVariable(
                variable_id=vid,
                interpretability_status=InterpretabilityStatus.INTERPRETABLE,
                spss_metadata=spss,
                semantic_enrichment=None,
            ))
            continue

        # Paso 1 del validador: si S4 la marcó insuficiente, se mantiene así.
        if verdict is not None and not verdict.is_interpretable:
            enriched.append(_insufficient_variable(vid, spss, verdict))
            continue

        llm_item = llm_by_id.get(vid)

        # Paso 2 del validador: si el LLM la declaró insuficiente O propone
        # significado SIN evidencia, se degrada a INSUFFICIENT_CONTEXT.
        llm_says_insufficient = (
            llm_item is not None
            and llm_item.get("interpretability_status") == "INSUFFICIENT_CONTEXT"
        )
        if llm_says_insufficient or not _has_evidence(canonical, vid):
            enriched.append(_insufficient_variable(vid, spss, verdict))
            continue

        # Interpretable con evidencia: construir cara semántica.
        construct = None
        semantic_role = None
        tags: list[str] = []
        sufficiency = None
        if llm_item is not None:
            construct = llm_item.get("construct")
            semantic_role = llm_item.get("semantic_role")
            tags = [str(t) for t in llm_item.get("semantic_tags", []) if t]
            sufficiency = _build_sufficiency(llm_item.get("analytical_sufficiency", {}))

        text = var.matrix_group.item if var.matrix_group else var.raw_header
        chunk_group = construct or var.normalized_name
        embeddable = f"{text}" + (f" — constructo: {construct}" if construct else "")

        semantic = SemanticEnrichment(
            construct=construct,
            semantic_role=semantic_role,
            semantic_tags=tags,
            chunking_hint=ChunkingHint(chunk_group=chunk_group, embeddable_text=embeddable),
            evidence=["encabezado explícito" if not var.matrix_group else "ítem de matriz"],
            analytical_sufficiency=sufficiency,
        )
        enriched.append(EnrichedVariable(
            variable_id=vid,
            interpretability_status=InterpretabilityStatus.INTERPRETABLE,
            spss_metadata=spss,
            semantic_enrichment=semantic,
        ))

    return EnrichmentResult(
        variables=enriched,
        survey_summary=survey_summary,
        degraded=degraded,
        llm_calls=llm_calls,
    )
