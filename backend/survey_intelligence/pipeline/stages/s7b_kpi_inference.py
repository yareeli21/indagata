# survey_intelligence/pipeline/stages/s7b_kpi_inference.py
"""
Sub-etapa S7-KPI — Inferencia de KPIs contra el catálogo del host (LLM, degradable).

El SIS recibe el catálogo del host (solo nombres + descripciones; NO conoce tt_rag),
infiere qué KPIs son relevantes y puntúa su relevancia. Emite KpiInference; el host
hace el matching a kpi_id. Se filtran los KPIs cuyo nombre no esté en el catálogo
(no se inventan KPIs fuera de él).

Degradable: si el LLM falla o el catálogo está vacío, devuelve [].
"""
from __future__ import annotations

from dataclasses import dataclass

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enums import ColumnClass
from survey_intelligence.contracts.kpi import KpiInference
from survey_intelligence.engine.parsing.robust_json import JsonParseError, parse_json_object
from survey_intelligence.engine.prompts.kpi_prompt import build_kpi_prompt
from survey_intelligence.ports.llm_port import LLMPort


@dataclass
class KpiResult:
    kpis: list[KpiInference]
    degraded: bool
    llm_calls: int


def _clamp(value: object) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def run_kpi_inference(
    canonical: CanonicalSurveyModel,
    purpose: str | None,
    catalog: list[dict],
    llm: LLMPort,
    temperature: float = 0.1,
) -> KpiResult:
    """
    Ejecuta la inferencia de KPIs.

    Args:
        catalog: catálogo del host [{"nombre": str, "descripcion": str}]. Si está
                 vacío, no se puede hacer matching y se devuelve [].
    """
    if not catalog:
        return KpiResult(kpis=[], degraded=False, llm_calls=0)

    # Vista de preguntas (sin respuestas).
    questions_view = [
        {"question_id": q.question_id, "text": q.text}
        for q in canonical.questions
    ]

    system, user = build_kpi_prompt(purpose, questions_view, catalog)
    data = None
    llm_calls = 0
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
        return KpiResult(kpis=[], degraded=True, llm_calls=llm_calls)

    # Nombres válidos del catálogo (para no aceptar KPIs inventados).
    catalog_names = {str(c.get("nombre", "")).strip().lower() for c in catalog}
    valid_var_ids = {
        v.variable_id for v in canonical.variables
        if v.column_class != ColumnClass.PLATFORM_METADATA
    }

    kpis: list[KpiInference] = []
    for item in data.get("kpis", []):
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre_sugerido", "")).strip()
        if not nombre or nombre.lower() not in catalog_names:
            continue  # no se inventan KPIs fuera del catálogo
        fuentes = [v for v in item.get("variables_fuente", []) if v in valid_var_ids]
        kpis.append(KpiInference(
            nombre_sugerido=nombre,
            score_relevancia=_clamp(item.get("score_relevancia")),
            tipo_relacion=item.get("tipo_relacion"),
            evidencia_textual=item.get("evidencia_textual"),
            variables_fuente=fuentes,
        ))

    return KpiResult(kpis=kpis, degraded=False, llm_calls=llm_calls)
