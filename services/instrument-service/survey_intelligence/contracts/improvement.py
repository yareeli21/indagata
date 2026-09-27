# survey_intelligence/contracts/improvement.py
"""
Improvement Opportunity (design.md §4.5, §14).

Recomendaciones de mejora continua. El SIS SOLO emite status='proposed'; nunca
persiste ni promueve reglas automáticamente (eso es gobernanza del host/humano).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from survey_intelligence.contracts.enums import ImprovementScope, ImprovementStatus

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ProposedRule(BaseModel):
    """Regla candidata con semántica when/then."""
    model_config = _FROZEN

    rule_id_candidate: str
    when: str
    then: str


class ImprovementOpportunity(BaseModel):
    model_config = _FROZEN

    opportunity_id: str
    scope: ImprovementScope
    title: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    proposed_rule: ProposedRule | None = None
    confidence: float | None = None
    status: ImprovementStatus = ImprovementStatus.PROPOSED
    generated_by: str
    created_at: str
