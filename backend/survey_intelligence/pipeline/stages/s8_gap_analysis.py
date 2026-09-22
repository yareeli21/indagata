# survey_intelligence/pipeline/stages/s8_gap_analysis.py
"""
Etapa S8 — Gap Analysis + Improvement Opportunities (determinística).

Compara lo que el pipeline ESPERABA poder determinar contra lo que realmente pudo, y
convierte cada laguna en una ImprovementOpportunity accionable (status=proposed).
Cubre los 6 scopes: survey, pipeline, future_analysis, validation_rule,
quality_heuristic, pattern.

El SIS solo EMITE oportunidades; no persiste ni promueve reglas (gobernanza del host).
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enriched import EnrichedSurveyModel
from survey_intelligence.contracts.enums import (
    ImprovementScope,
    InterpretabilityStatus,
    SufficiencyLevel,
)
from survey_intelligence.contracts.improvement import (
    ImprovementOpportunity,
    ProposedRule,
)
from survey_intelligence.ports.clock_port import ClockPort
from survey_intelligence.ports.ids_port import IdGeneratorPort


def run_gap_analysis(
    canonical: CanonicalSurveyModel,
    enriched: EnrichedSurveyModel,
    ids: IdGeneratorPort,
    clock: ClockPort,
) -> list[ImprovementOpportunity]:
    """Genera las oportunidades de mejora a partir del Canonical + Enriched."""
    now = clock.now().isoformat()
    opportunities: list[ImprovementOpportunity] = []

    def _new(scope: ImprovementScope, title: str, description: str,
             evidence: list[str], rule: ProposedRule | None = None,
             confidence: float | None = None) -> ImprovementOpportunity:
        return ImprovementOpportunity(
            opportunity_id=ids.new_id("imp-"),
            scope=scope, title=title, description=description,
            evidence=evidence, proposed_rule=rule, confidence=confidence,
            generated_by="gap_analysis_stage", created_at=now,
        )

    # ── validation_rule: typos de escala -> regla candidata de normalización ────
    typo_evidence: list[str] = []
    for v in canonical.variables:
        if v.detected_scale and v.detected_scale.anomalies:
            for a in v.detected_scale.anomalies:
                typo_evidence.append(f"{v.variable_id}:{a.value}~{a.canonical_guess}")
    if typo_evidence:
        opportunities.append(_new(
            ImprovementScope.VALIDATION_RULE,
            title="Regla candidata: normalizar variantes mal escritas de la escala",
            description="Se detectaron valores de escala con distancia de edición 1 respecto a una etiqueta canónica.",
            evidence=typo_evidence[:10],
            rule=ProposedRule(
                rule_id_candidate="scale_typo_normalization",
                when="valor de escala con distancia de edición 1 respecto a una etiqueta canónica",
                then="proponer normalize_scale con el valor canónico",
            ),
            confidence=0.8,
        ))

    # ── survey / future_analysis: preguntas de suficiencia limitada/pobre ───────
    weak = []
    for ev in enriched.variables_enriched:
        se = ev.semantic_enrichment
        if se and se.analytical_sufficiency and se.analytical_sufficiency.level in (
            SufficiencyLevel.LIMITADA, SufficiencyLevel.POBRE
        ):
            weak.append(ev.variable_id)
    if weak:
        opportunities.append(_new(
            ImprovementScope.FUTURE_ANALYSIS,
            title="Preguntas con suficiencia analítica limitada",
            description="Algunas preguntas rinden poco analíticamente; considera enriquecerlas en la próxima versión del instrumento.",
            evidence=weak[:10],
            confidence=0.6,
        ))

    # ── pattern: variables sin contexto que se repiten ──────────────────────────
    insufficient = [
        ev.variable_id for ev in enriched.variables_enriched
        if ev.interpretability_status == InterpretabilityStatus.INSUFFICIENT_CONTEXT
    ]
    if insufficient:
        opportunities.append(_new(
            ImprovementScope.PATTERN,
            title="Variables no interpretables sin codebook",
            description="Hay variables que no pueden interpretarse sin documentación; un codebook (RAG) las resolvería.",
            evidence=insufficient[:10],
            confidence=0.7,
        ))

    # ── quality_heuristic: doble pregunta detectada ─────────────────────────────
    if enriched.survey_level_findings.double_barreled:
        opportunities.append(_new(
            ImprovementScope.QUALITY_HEURISTIC,
            title="Heurística candidata: detección de preguntas dobles",
            description="Se detectaron posibles preguntas de doble cañón; formalizar una heurística de detección.",
            evidence=list(enriched.survey_level_findings.double_barreled)[:10],
            confidence=0.55,
        ))

    # ── pipeline: siempre una nota de mejora del propio proceso ─────────────────
    opportunities.append(_new(
        ImprovementScope.PIPELINE,
        title="Registro de ejecución para mejora del pipeline",
        description="Registrar métricas de esta ejecución (tipos detectados, insuficientes, degradaciones) para robustecer futuros análisis.",
        evidence=[f"n_variables={len(canonical.variables)}", f"n_insuficientes={len(insufficient)}"],
        confidence=0.5,
    ))

    return opportunities
