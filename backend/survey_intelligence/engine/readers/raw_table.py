# survey_intelligence/engine/readers/raw_table.py
"""
RawTable: estructura tabular cruda producida por los readers.

Es el resultado neutral de leer un CSV o XLSX, antes de cualquier interpretación.
S1 (ingesta) produce un RawTable; S2 (canonical) lo consume. Así la construcción
del modelo canónico no depende del formato de origen.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawTable:
    """
    Tabla cruda: encabezados + filas de valores como texto.

    Attributes:
        headers:  nombres de columna tal cual vienen (ya normalizados de newlines).
        rows:     filas de datos; cada celda es str (o "" para vacío). Los valores
                  no textuales (p. ej. datetime de XLSX) se serializan a str aquí.
        encoding: codificación detectada al leer (solo informativo; None para XLSX).
        sheet:    hoja leída (solo XLSX).
        notes:    observaciones del reader (p. ej. codificación de respaldo usada).
    """
    headers: list[str]
    rows: list[list[str]]
    encoding: str | None = None
    sheet: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def n_columns(self) -> int:
        return len(self.headers)
