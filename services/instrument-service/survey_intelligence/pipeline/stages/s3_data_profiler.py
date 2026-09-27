# survey_intelligence/pipeline/stages/s3_data_profiler.py
"""
Etapa S3 — Data Profiling (determinístico, sin LLM).

Enriquece el Canonical de S2 con:
  - detected_scale (Likert/binaria) + anomalías de escala (typos con canonical_guess).
  - value_distribution (nulos, cardinalidad, top valores, nulos estructurales).
  - inferred_data_type refinado (ordinal, multi_select, datetime, numeric, ...).

Como CanonicalSurveyModel es inmutable, S3 devuelve un modelo nuevo con las
variables reconstruidas. Todas las métricas viven aquí (nunca en el Enriched).
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import (
    CanonicalQuestion,
    CanonicalSurveyModel,
    CanonicalVariable,
    QuestionDistributionBin,
)
from survey_intelligence.contracts.enums import CanonicalQuestionType, ColumnClass, DataType
from survey_intelligence.engine.profiling.scale_detector import detect_scale
from survey_intelligence.engine.profiling.stats import (
    infer_data_type,
    value_distribution,
)
from survey_intelligence.engine.readers.raw_table import RawTable


def _column_values(raw: RawTable, position: int) -> list[str]:
    col = position - 1  # position es 1-based
    return [row[col] for row in raw.rows if col < len(row)]


def profile(canonical: CanonicalSurveyModel, raw: RawTable) -> CanonicalSurveyModel:
    """Devuelve un Canonical nuevo con profiling completo por variable."""
    profiled_vars: list[CanonicalVariable] = []

    for var in canonical.variables:
        values = _column_values(raw, var.position)

        # Metadatos de plataforma: solo distribución básica, sin escala ni tipo fino.
        if var.column_class == ColumnClass.PLATFORM_METADATA:
            profiled_vars.append(
                var.model_copy(update={
                    "value_distribution": value_distribution(values),
                })
            )
            continue

        scale = detect_scale(values)
        is_free_text = var.column_class == ColumnClass.FREE_TEXT
        scale_kind = scale.kind.value if scale is not None else None
        data_type = infer_data_type(
            values, has_scale=scale is not None, is_free_text=is_free_text, scale_kind=scale_kind
        )

        # Si el profiler reclasifica una 'free_text' como multi_select, corrige la clase.
        column_class = var.column_class
        if data_type == DataType.MULTI_SELECT and column_class == ColumnClass.FREE_TEXT:
            column_class = ColumnClass.QUESTION

        profiled_vars.append(
            var.model_copy(update={
                "column_class": column_class,
                "inferred_data_type": data_type,
                "detected_scale": scale,
                "value_distribution": value_distribution(values),
            })
        )

    profiled = canonical.model_copy(update={"variables": profiled_vars})

    # ── Rediseño v2: profiling POR PREGUNTA (solo si el canónico trae questions v2) ──
    # variables[] ya quedaron con su value_distribution (compatibilidad intacta).
    # Aquí solo se añaden metrics/distribution a cada CanonicalQuestion v2.
    if any(q.type is not None for q in profiled.questions):
        profiled = _profile_v2_questions(profiled, raw)

    return profiled


def _profile_v2_questions(canonical: CanonicalSurveyModel, raw: RawTable) -> CanonicalSurveyModel:
    """
    Calcula metrics/distribution por pregunta (v2), determinístico. Reutiliza los
    valores por columna; NO toca variables[]. Cubre los tipos en alcance:
    opcion_multiple (por opción, columnas yes/no), likert/opcion_unica/numerica y matriz
    (por columna), y texto (solo conteos).
    """
    QT = CanonicalQuestionType
    new_questions: list[CanonicalQuestion] = []

    for q in canonical.questions:
        if q.type is None:
            new_questions.append(q)
            continue

        # Valores por columna de origen (posición 1-based en SourceColumn).
        cols = {sc.position: _column_values(raw, sc.position + 1) for sc in q.source_columns}
        # Nota: SourceColumn.position es 0-based (posición del header); _column_values
        # espera 1-based, por eso +1.

        distribution: list[QuestionDistributionBin] = []
        n_resp = 0
        n_null = 0

        if q.type == QT.OPCION_MULTIPLE and q.options:
            # Una columna yes/no por opción: frecuencia = nº de "yes" en esa columna.
            total_filas = raw.n_rows or 1
            for opt, sc in zip(q.options, q.source_columns):
                vals = cols.get(sc.position, [])
                yes = sum(1 for v in vals if str(v).strip().lower() in {"yes", "sí", "si", "true", "1", "x"})
                distribution.append(QuestionDistributionBin(
                    label=opt.label, option_id=opt.option_id,
                    frequency=yes, percentage=round(100 * yes / total_filas, 1),
                ))
            # Respondentes: filas con al menos un 'yes' en cualquier columna de la pregunta.
            n_resp = 0
            for i in range(raw.n_rows):
                marcado = any(
                    i < len(cols.get(sc.position, [])) and
                    str(cols[sc.position][i]).strip().lower() in {"yes", "sí", "si", "true", "1", "x"}
                    for sc in q.source_columns
                )
                if marcado:
                    n_resp += 1
            n_null = raw.n_rows - n_resp

        else:
            # Preguntas de 1 columna (o matriz/likert): distribución por valores de la
            # primera columna de origen (para matriz/likert multi-col, el detalle por ítem
            # se refina en fases posteriores; aquí damos la agregada de la 1ª columna).
            first = q.source_columns[0] if q.source_columns else None
            vals = cols.get(first.position, []) if first else []
            vd = value_distribution(vals)
            n_resp = vd.n_non_null
            n_null = vd.n_null
            total = n_resp or 1
            for tv in vd.top_values:
                distribution.append(QuestionDistributionBin(
                    label=str(tv.get("value", "")),
                    frequency=int(tv.get("count", 0)),
                    percentage=round(100 * int(tv.get("count", 0)) / total, 1),
                ))

        metrics = {"n_respuestas": n_resp, "n_nulos": n_null}
        new_questions.append(q.model_copy(update={"metrics": metrics, "distribution": distribution}))

    return canonical.model_copy(update={"questions": new_questions})
