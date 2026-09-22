# survey_intelligence/engine/transforms/apply_engine.py
"""
Motor de aplicación de transformaciones (patrón propose -> decide -> apply).

Cierra la brecha detectada en el host: EtlService.approve hoy REGISTRA la decisión
pero NO ejecuta el cambio. El apply_engine ejecuta SOLO las decisiones aprobadas y
de forma reversible, devolviendo la tabla transformada, los registros de deshacer
y el Canonical regenerado.

REGLA: nunca muta datos sin una decisión explícita. Recibe solo decisiones ya
aprobadas por el usuario.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from survey_intelligence.contracts.canonical import CanonicalSurveyModel
from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.transforms.models import (
    AppliedTransform,
    TransformDecision,
)
from survey_intelligence.engine.transforms.transform_registry import get_transform


@dataclass(frozen=True)
class ApplyResult:
    """Resultado de aplicar un lote de transformaciones aprobadas."""
    raw_table: RawTable
    applied: list[AppliedTransform] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # transform_ids no reconocidos


def apply_decisions(
    raw: RawTable,
    normalized_names: list[str],
    decisions: list[TransformDecision],
) -> ApplyResult:
    """
    Aplica en orden las transformaciones aprobadas.

    Las columnas se identifican por normalized_name; tras un drop_columns, la lista
    de nombres se recalcula para que las transformaciones siguientes sigan alineadas.

    Args:
        raw:              tabla inicial.
        normalized_names: nombre normalizado por posición (paralelo a raw.headers).
        decisions:        transformaciones aprobadas por el usuario.

    Returns:
        ApplyResult con la tabla final, los registros reversibles y los omitidos.
    """
    current = raw
    names = list(normalized_names)
    applied: list[AppliedTransform] = []
    skipped: list[str] = []

    for decision in decisions:
        fn = get_transform(decision.transform_id)
        if fn is None:
            skipped.append(decision.transform_id)
            continue

        current, record = fn(current, names, decision.params)
        applied.append(record)

        # Si se eliminaron columnas, recalcular la lista de nombres para mantener
        # la alineación posicional con la nueva tabla.
        if decision.transform_id == "drop_columns":
            drop_set = set(decision.params.get("columnas", []))
            names = [n for n in names if n not in drop_set]

    return ApplyResult(raw_table=current, applied=applied, skipped=skipped)


def rebuild_canonical_after_apply(
    original_canonical: CanonicalSurveyModel,
    result: ApplyResult,
) -> CanonicalSurveyModel:
    """
    Regenera el Canonical tras aplicar transformaciones, reejecutando el pipeline
    determinístico (S2 + S3) sobre la tabla transformada.

    Importado localmente para evitar ciclos (stages -> engine -> stages).
    """
    from survey_intelligence.pipeline.stages.s1_ingestion import IngestionResult
    from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
    from survey_intelligence.pipeline.stages.s3_data_profiler import profile
    from survey_intelligence.engine.heuristics.platform_columns import detect_platform

    raw = result.raw_table
    # Recalcular la detección de plataforma sobre los encabezados restantes.
    platform = detect_platform(raw.headers)
    ingestion = IngestionResult(raw_table=raw, platform=platform)

    canonical = build_canonical(
        ingestion,
        file_name=original_canonical.source.file_name,
        sheet=original_canonical.source.sheet,
    )
    return profile(canonical, raw)
