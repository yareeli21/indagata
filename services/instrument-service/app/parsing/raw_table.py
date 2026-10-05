"""RawTable: estructura tabular cruda producida por el parser tabular.

Resultado neutral de leer un CSV o XLSX, antes de cualquier interpretación.
Mantiene el servicio desacoplado del formato de origen: quien consuma el
contenido trabaja siempre con esta misma forma.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawTable:
    """Tabla cruda: encabezados + filas de valores como texto.

    Attributes:
        headers:  Nombres de columna (ya normalizados de saltos de línea).
        rows:     Filas de datos; cada celda es str ("" si está vacía). Los
                  valores no textuales (p. ej. datetime de XLSX) se serializan a
                  str durante la lectura.
        encoding: Codificación detectada al leer (informativa; None para XLSX).
        sheet:    Hoja leída (solo XLSX).
        notes:    Observaciones del parser (p. ej. codificación de respaldo).
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
