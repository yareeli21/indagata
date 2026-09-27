# survey_intelligence/contracts/interview.py
"""
Contratos del pipeline de ENTREVISTAS.

Las entrevistas NO se analizan como encuestas: en vez de variables/escalas, el
conocimiento se organiza en participantes, turnos de diálogo (quién pregunta, quién
responde, a qué pregunta), temas, hallazgos, patrones, citas y resúmenes.

Dos capas, igual que el resto del SIS:
  - Determinística (sin LLM): participantes + turnos (diarización textual).
  - LLM (sobre lo observado, sin inventar): temas, hallazgos, patrones, citas,
    resúmenes por participante y general.

`InterviewAnalysis` es el agregado que se adjunta a SurveyIntelligenceResult en el
campo opcional `interview_analysis` (solo para instrumentos de tipo 'entrevista').
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


# ── Capa determinística: participantes y turnos ────────────────────────────

class Participant(BaseModel):
    """Un participante de la entrevista, con rol e identificador estable."""
    model_config = _FROZEN

    participant_id: str          # p.ej. "entrevistador_01", "entrevistado_02"
    role: str                    # "entrevistador" | "entrevistado"
    display_label: str | None = None   # etiqueta original detectada en el texto


class DialogueTurn(BaseModel):
    """Un turno del diálogo: quién habla, qué dice y a qué pregunta responde."""
    model_config = _FROZEN

    turn_id: int
    speaker_id: str              # -> Participant.participant_id
    turn_type: str               # "pregunta" | "respuesta" | "intervencion"
    text: str
    answers_to: int | None = None   # turn_id de la pregunta respondida (si aplica)
    char_len: int = 0
    word_len: int = 0


# ── Capa semántica (LLM sobre lo observado) ────────────────────────────────

class Theme(BaseModel):
    """Tema/tópico emergente, con la evidencia (turnos) que lo respalda."""
    model_config = _FROZEN

    theme_id: str
    titulo: str
    descripcion: str | None = None
    turn_ids: list[int] = Field(default_factory=list)
    participant_ids: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    """Hallazgo analítico con evidencia trazable a los turnos."""
    model_config = _FROZEN

    finding_id: str
    enunciado: str
    evidence_turn_ids: list[int] = Field(default_factory=list)
    participant_ids: list[str] = Field(default_factory=list)
    confidence: float | None = None


class Pattern(BaseModel):
    """Patrón discursivo/temático observado en el diálogo."""
    model_config = _FROZEN

    pattern_id: str
    descripcion: str
    evidence_turn_ids: list[int] = Field(default_factory=list)


class Quote(BaseModel):
    """Cita textual relevante, trazable a su turno y hablante."""
    model_config = _FROZEN

    quote_id: str
    text: str
    speaker_id: str
    turn_id: int
    theme_id: str | None = None


class ParticipantSummary(BaseModel):
    """Resumen de las intervenciones de un participante."""
    model_config = _FROZEN

    participant_id: str
    resumen: str
    themes: list[str] = Field(default_factory=list)


# ── Agregado de salida ─────────────────────────────────────────────────────

class InterviewAnalysis(BaseModel):
    """
    Conocimiento consolidado de una entrevista. Se adjunta a
    SurveyIntelligenceResult.interview_analysis (solo instrumentos 'entrevista').

    La capa determinística (participants, turns, n_personas) siempre se completa.
    La capa semántica (themes, findings, patterns, quotes, resúmenes) puede quedar
    vacía si no hubo LLM (degradación controlada).
    """
    model_config = _FROZEN

    based_on_canonical_id: str
    participants: list[Participant] = Field(default_factory=list)
    n_personas: int = 0
    turns: list[DialogueTurn] = Field(default_factory=list)

    themes: list[Theme] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    participant_summaries: list[ParticipantSummary] = Field(default_factory=list)
    general_summary: str | None = None

    degraded: bool = False   # True si la capa semántica no se pudo generar (sin LLM)
