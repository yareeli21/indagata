# survey_intelligence/engine/transforms/drop_columns.py
"""
Transformación drop_columns (reversible).

Elimina columnas del RawTable identificadas por su normalized_name. Guarda en
undo_data los encabezados y valores eliminados para poder revertir.

Las columnas se identifican por normalized_name (estable) mapeado a la posición
real vía la lista de nombres normalizados que acompaña al RawTable.
"""
from __future__ import annotations

from survey_intelligence.engine.readers.raw_table import RawTable
from survey_intelligence.engine.transforms.models import AppliedTransform


def apply_drop_columns(
    raw: RawTable,
    normalized_names: list[str],
    columns_to_drop: list[str],
) -> tuple[RawTable, AppliedTransform]:
    """
    Elimina las columnas cuyo normalized_name esté en columns_to_drop.

    Args:
        raw:              tabla actual.
        normalized_names: nombre normalizado por posición (paralelo a raw.headers).
        columns_to_drop:  normalized_names a eliminar.

    Returns:
        (nueva_tabla, registro_reversible).
    """
    drop_set = set(columns_to_drop)
    keep_positions = [i for i, name in enumerate(normalized_names) if name not in drop_set]
    drop_positions = [i for i, name in enumerate(normalized_names) if name in drop_set]

    # Guardar datos para deshacer: por cada columna eliminada, su header, name y valores.
    removed: list[dict] = []
    for pos in drop_positions:
        removed.append({
            "position": pos,
            "header": raw.headers[pos],
            "normalized_name": normalized_names[pos],
            "values": [row[pos] if pos < len(row) else "" for row in raw.rows],
        })

    new_headers = [raw.headers[i] for i in keep_positions]
    new_rows = [[row[i] for i in keep_positions if i < len(row)] for row in raw.rows]

    new_table = RawTable(
        headers=new_headers,
        rows=new_rows,
        encoding=raw.encoding,
        sheet=raw.sheet,
        notes=list(raw.notes),
    )

    applied = AppliedTransform(
        transform_id="drop_columns",
        params={"columnas": list(columns_to_drop)},
        undo_data={"removed_columns": removed, "kept_positions": keep_positions},
        summary=f"Eliminadas {len(drop_positions)} columnas: {', '.join(columns_to_drop)}",
    )
    return new_table, applied


def undo_drop_columns(raw: RawTable, applied: AppliedTransform) -> RawTable:
    """Revierte un drop_columns, reinsertando las columnas en su posición original."""
    removed = applied.undo_data.get("removed_columns", [])
    if not removed:
        return raw

    # Reconstruir headers y filas insertando cada columna eliminada en su posición.
    headers = list(raw.headers)
    rows = [list(r) for r in raw.rows]

    # Insertar en orden de posición ascendente para que los índices sean válidos.
    for col in sorted(removed, key=lambda c: c["position"]):
        pos = col["position"]
        headers.insert(pos, col["header"])
        for i, row in enumerate(rows):
            value = col["values"][i] if i < len(col["values"]) else ""
            row.insert(pos, value)

    return RawTable(
        headers=headers,
        rows=rows,
        encoding=raw.encoding,
        sheet=raw.sheet,
        notes=list(raw.notes),
    )
