# survey_intelligence/pipeline/stages/s8b_results_analysis.py
"""
Etapa S8b — Análisis de resultados (hallazgos derivados de las RESPUESTAS).

Solo para encuestas. Para cada pregunta real:
  - Métricas determinísticas (n, nulos, moda, media codificada) desde value_distribution
    y value_encoding SPSS.
  - Distribución de frecuencias/porcentajes.
  - Interpretación, insights y texto semántico vía LLM EN LOTE (una llamada), sobre los
    datos observados (regla de no-invención).

Cada ResultsFinding es un chunk analítico para el RAG.
Degradable: si el LLM falla, se conservan las métricas/distribución determinísticas.
"""
from __future__ import annotations

from dataclasses import dataclass

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.contracts.enums import ColumnClass
from survey_intelligence.contracts.results import (
    DistributionBin,
    ResultMetrics,
    ResultsFinding,
)
from survey_intelligence.contracts.spss import SpssVariableMetadata
from survey_intelligence.engine.parsing.robust_json import JsonParseError, parse_json_object
from survey_intelligence.engine.prompts.results_prompt import build_results_prompt
from survey_intelligence.ports.llm_port import LLMPort


@dataclass
class ResultsAnalysisResult:
    findings: list[ResultsFinding]
    degraded: bool
    llm_calls: int


def _question_text(var) -> str:
    return var.matrix_group.item if var.matrix_group else var.raw_header


def _build_metrics_and_distribution(
    var, spss: SpssVariableMetadata | None
) -> tuple[ResultMetrics, list[DistributionBin]]:
    """Métricas y distribución determinísticas desde value_distribution + value_encoding."""
    vd = var.value_distribution
    n_resp = vd.n_non_null if vd else 0
    n_null = vd.n_null if vd else 0

    distribution: list[DistributionBin] = []
    moda: str | None = None
    media: float | None = None

    if vd and vd.top_values:
        # top_values ya viene ordenado por frecuencia (most_common).
        moda = str(vd.top_values[0].get("value")) if vd.top_values else None
        total = n_resp or 1
        for tv in vd.top_values:
            val = str(tv.get("value"))
            freq = int(tv.get("count", 0))
            distribution.append(DistributionBin(
                value=val, frequency=freq,
                percentage=round(100.0 * freq / total, 1),
            ))

    # Media codificada: solo si hay value_encoding (ordinales/Likert).
    if spss and spss.value_encoding and vd and vd.top_values:
        suma = 0.0
        cuenta = 0
        for tv in vd.top_values:
            code = spss.value_encoding.get(str(tv.get("value")))
            if code is not None:
                suma += code * int(tv.get("count", 0))
                cuenta += int(tv.get("count", 0))
        if cuenta:
            media = round(suma / cuenta, 2)

    return ResultMetrics(
        n_respuestas=n_resp, n_nulos=n_null, moda=moda, media_codificada=media
    ), distribution


def run_results_analysis(
    canonical: CanonicalSurveyModel,
    spss_by_id: dict[str, SpssVariableMetadata],
    llm: LLMPort,
    temperature: float = 0.1,
    language_hint: str = "es",
) -> ResultsAnalysisResult:
    """Ejecuta S8b. Métricas determinísticas + interpretación LLM en lote."""
    # Variables que son preguntas reales (excluye plataforma).
    preguntas = [
        v for v in canonical.variables
        if v.column_class != ColumnClass.PLATFORM_METADATA
    ]
    if not preguntas:
        return ResultsAnalysisResult(findings=[], degraded=False, llm_calls=0)

    # 1) Métricas y distribución determinísticas.
    base: dict[str, dict] = {}
    for var in preguntas:
        metrics, distribution = _build_metrics_and_distribution(var, spss_by_id.get(var.variable_id))
        base[var.variable_id] = {
            "var": var, "metrics": metrics, "distribution": distribution,
        }

    # 2) Interpretación por LLM en lote (una sola llamada).
    findings_input = [
        {
            "variable_id": vid,
            "pregunta": _question_text(b["var"]),
            "tipo": b["var"].inferred_data_type.value,
            "metrics": {
                "n_respuestas": b["metrics"].n_respuestas,
                "n_nulos": b["metrics"].n_nulos,
                "moda": b["metrics"].moda,
                "media_codificada": b["metrics"].media_codificada,
            },
            "distribution": [
                {"value": d.value, "frequency": d.frequency, "percentage": d.percentage}
                for d in b["distribution"]
            ],
        }
        for vid, b in base.items()
    ]

    llm_by_id: dict[str, dict] = {}
    degraded = False
    llm_calls = 0
    system, user = build_results_prompt(findings_input, language_hint)
    for _attempt in range(2):
        try:
            llm_calls += 1
            raw = llm.complete_json(system_prompt=system, user_prompt=user, temperature=temperature)
            data = parse_json_object(raw)
            for item in data.get("findings", []):
                if isinstance(item, dict) and item.get("variable_id"):
                    llm_by_id[item["variable_id"]] = item
            break
        except (RuntimeError, JsonParseError):
            continue
    else:
        degraded = True
    if not llm_by_id and llm_calls and not degraded:
        # respondió pero sin findings útiles
        pass

    # 3) Ensamblar los ResultsFinding.
    findings: list[ResultsFinding] = []
    for vid, b in base.items():
        var = b["var"]
        llm_item = llm_by_id.get(vid, {})
        # texto semántico de respaldo determinístico si el LLM no dio uno.
        fallback_text = (
            f"{_question_text(var)} — {b['metrics'].n_respuestas} respuestas; "
            f"moda: {b['metrics'].moda}"
        )
        findings.append(ResultsFinding(
            variable_id=vid,
            pregunta=_question_text(var),
            tipo=var.inferred_data_type.value,
            metrics=b["metrics"],
            distribution=b["distribution"],
            interpretation=llm_item.get("interpretation"),
            insights=[str(x) for x in llm_item.get("insights", [])],
            numeric_evidence=llm_item.get("numeric_evidence"),
            semantic_text=llm_item.get("semantic_text") or fallback_text,
        ))

    return ResultsAnalysisResult(findings=findings, degraded=degraded, llm_calls=llm_calls)


# ───────────────────────────────────────────────────────────────────────────
# Rediseño v2 — análisis POR PREGUNTA (sobre questions[] reagrupadas).
# Reutiliza el mismo patrón (LLM en lote + degradación + fallback determinístico)
# pero itera preguntas lógicas en vez de columnas. Devuelve ResultsFinding con
# question_id en el slot de id. La ruta v1 (por variable) queda intacta.
# ───────────────────────────────────────────────────────────────────────────

def run_results_analysis_v2(
    canonical: CanonicalSurveyModel,
    llm: LLMPort | None,
    temperature: float = 0.1,
    language_hint: str = "es",
) -> ResultsAnalysisResult:
    """
    S8b v2: hallazgos por PREGUNTA. Usa las metrics/distribution ya calculadas por S3 v2.

    Degradable: si `llm` es None o falla, se conservan métricas/distribución con un
    texto semántico determinístico de respaldo.
    """
    # Preguntas con datos (excluye no_dato y las sin tipo v2).
    preguntas = [
        q for q in canonical.questions
        if q.type is not None and q.type.value != "no_dato"
    ]
    if not preguntas:
        return ResultsAnalysisResult(findings=[], degraded=False, llm_calls=0)

    def _metrics_of(q) -> ResultMetrics:
        m = q.metrics or {}
        return ResultMetrics(
            n_respuestas=int(m.get("n_respuestas", 0)),
            n_nulos=int(m.get("n_nulos", 0)),
            moda=(q.distribution[0].label if q.distribution else None),
            media_codificada=None,
        )

    def _distribution_of(q) -> list[DistributionBin]:
        return [
            DistributionBin(value=b.label, frequency=b.frequency, percentage=b.percentage)
            for b in q.distribution
        ]

    base = {q.question_id: {"q": q, "metrics": _metrics_of(q), "distribution": _distribution_of(q)}
            for q in preguntas}

    # Interpretación LLM en lote (opcional).
    llm_by_id: dict[str, dict] = {}
    degraded = False
    llm_calls = 0
    if llm is not None:
        findings_input = [
            {
                "variable_id": qid,
                "pregunta": b["q"].text,
                "tipo": b["q"].type.value,
                "metrics": {
                    "n_respuestas": b["metrics"].n_respuestas,
                    "n_nulos": b["metrics"].n_nulos,
                    "moda": b["metrics"].moda,
                    "media_codificada": None,
                },
                "distribution": [
                    {"value": d.value, "frequency": d.frequency, "percentage": d.percentage}
                    for d in b["distribution"]
                ],
            }
            for qid, b in base.items()
        ]
        system, user = build_results_prompt(findings_input, language_hint)
        for _attempt in range(2):
            try:
                llm_calls += 1
                raw = llm.complete_json(system_prompt=system, user_prompt=user, temperature=temperature)
                data = parse_json_object(raw)
                for item in data.get("findings", []):
                    if isinstance(item, dict) and item.get("variable_id"):
                        llm_by_id[item["variable_id"]] = item
                break
            except (RuntimeError, JsonParseError):
                continue
        else:
            degraded = True
    else:
        degraded = True

    findings: list[ResultsFinding] = []
    for qid, b in base.items():
        q = b["q"]
        llm_item = llm_by_id.get(qid, {})
        fallback_text = f"{q.text} — {b['metrics'].n_respuestas} respuestas; moda: {b['metrics'].moda}"
        findings.append(ResultsFinding(
            variable_id=qid,               # aquí el id es el question_id
            pregunta=q.text,
            tipo=q.type.value,
            metrics=b["metrics"],
            distribution=b["distribution"],
            interpretation=llm_item.get("interpretation"),
            insights=[str(x) for x in llm_item.get("insights", [])],
            numeric_evidence=llm_item.get("numeric_evidence"),
            semantic_text=llm_item.get("semantic_text") or fallback_text,
        ))

    return ResultsAnalysisResult(findings=findings, degraded=degraded, llm_calls=llm_calls)
