# survey_intelligence/engine/transforms/normalize_scale.py
"""
Transformación normalize_scale (reversible).

Reemplaza variantes mal escritas de una etiqueta de escala por su valor canónico
(p. ej. "En deesacuerdo" -> "En desacuerdo"). Guarda en undo_data las celdas
modificadas (posición fila/columna y valor original) para revertir.
"""
from __future__ import annotations

from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.transforms.models import AppliedTransform


def apply_normalize_scale(
    raw: RawTable,
    normalized_names: list[str],
    column: str,
    mapping: dict[str, str],
) -> tuple[RawTable, AppliedTransform]:
    """
    Aplica un mapeo valor_erroneo -> valor_canonico sobre una columna.

    Args:
        raw:              tabla actual.
        normalized_names: nombre normalizado por posición.
        column:           normalized_name de la columna a corregir.
        mapping:          {valor_observado: valor_canonico}.

    Returns:
        (nueva_tabla, registro_reversible).
    """
    try:
        col = normalized_names.index(column)
    except ValueError:
        # La columna no existe (quizá ya se eliminó): no-op.
        return raw, AppliedTransform(
            transform_id="normalize_scale",
            params={"column": column, "mapping": mapping},
            summary=f"normalize_scale omitido: columna '{column}' no encontrada",
        )

    changed_cells: list[dict] = []
    new_rows = [list(r) for r in raw.rows]
    for i, row in enumerate(new_rows):
        if col >= len(row):
            continue
        original = row[col]
        if original in mapping:
            row[col] = mapping[original]
            changed_cells.append({"row": i, "col": col, "original": original})

    new_table = RawTable(
        headers=list(raw.headers),
        rows=new_rows,
        encoding=raw.encoding,
        sheet=raw.sheet,
        notes=list(raw.notes),
    )

    applied = AppliedTransform(
        transform_id="normalize_scale",
        params={"column": column, "mapping": mapping},
        undo_data={"changed_cells": changed_cells},
        summary=f"Normalizados {len(changed_cells)} valores en '{column}'",
    )
    return new_table, applied


def undo_normalize_scale(raw: RawTable, applied: AppliedTransform) -> RawTable:
    """Revierte un normalize_scale restaurando los valores originales por celda."""
    changed = applied.undo_data.get("changed_cells", [])
    if not changed:
        return raw
    new_rows = [list(r) for r in raw.rows]
    for cell in changed:
        i, col = cell["row"], cell["col"]
        if i < len(new_rows) and col < len(new_rows[i]):
            new_rows[i][col] = cell["original"]
    return RawTable(
        headers=list(raw.headers),
        rows=new_rows,
        encoding=raw.encoding,
        sheet=raw.sheet,
        notes=list(raw.notes),
    )
