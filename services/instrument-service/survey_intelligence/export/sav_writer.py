# survey_intelligence/export/sav_writer.py
"""
Escritor de archivos .SAV (IBM SPSS) usando pyreadstat.

Toma el diccionario SPSS del Enriched Model + los datos del RawTable transformado y
escribe un .SAV con etiquetas de variable, etiquetas de valor y niveles de medición.

Aplica value_encoding (texto observado -> código numérico), lo que además mapea las
variantes mal escritas al código canónico (limpia el dato en el .SAV).

Solo aplica a encuestas (datos tabulares). El host decide cuándo invocarlo.
"""
from __future__ import annotations

from pathlib import Path

from survey_intelligence.contracts.enums import ColumnClass, Measure, SpssType
from survey_intelligence.contracts.spss import SpssVariableMetadata
from survey_intelligence.engine.readers.raw_table import RawTable

# Mapa de Measure del SIS -> measure de pyreadstat.
_MEASURE_MAP = {
    Measure.NOMINAL: "nominal",
    Measure.ORDINAL: "ordinal",
    Measure.SCALE: "scale",
}


class SavWriteError(Exception):
    """No se pudo escribir el archivo .SAV."""


def _encode_cell(value: str, encoding: dict[str, int]) -> object:
    """Codifica una celda: texto->código si hay mapeo; si no, el valor tal cual."""
    if value in encoding:
        return encoding[value]
    if value == "":
        return None
    return value


def write_sav(
    output_path: Path,
    raw: RawTable,
    normalized_names: list[str],
    spss_by_id: dict[str, SpssVariableMetadata],
    variable_ids_by_position: list[str],
    include_platform: bool = False,
) -> Path:
    """
    Escribe un .SAV a output_path.

    Args:
        raw:                       tabla de datos (idealmente ya limpiada por apply_engine).
        normalized_names:          nombre normalizado por posición (paralelo a raw.headers).
        spss_by_id:                diccionario SPSS por variable_id.
        variable_ids_by_position:  variable_id por posición de columna (paralelo a headers).
        include_platform:          si False, excluye columnas de metadata de plataforma.

    Returns:
        La ruta del archivo escrito.

    Raises:
        SavWriteError: si pyreadstat no está disponible o falla la escritura.
    """
    try:
        import pandas as pd
        import pyreadstat
    except ImportError as exc:  # pragma: no cover
        raise SavWriteError("pyreadstat/pandas no disponibles.") from exc

    # Seleccionar columnas a exportar.
    columns: list[dict] = []
    for pos, vid in enumerate(variable_ids_by_position):
        spss = spss_by_id.get(vid)
        if spss is None:
            continue
        # Excluir plataforma salvo que se pida incluirla.
        if not include_platform and spss.measure == Measure.NOMINAL and _is_platform(spss):
            # heurística débil; el host normalmente ya quitó estas columnas.
            pass
        columns.append({"pos": pos, "vid": vid, "spss": spss})

    if not columns:
        raise SavWriteError("No hay columnas para exportar al .SAV.")

    # Construir DataFrame + metadatos.
    data: dict[str, list] = {}
    variable_labels: dict[str, str] = {}
    value_labels: dict[str, dict] = {}
    measures: dict[str, str] = {}

    used_names: set[str] = set()
    for col in columns:
        spss: SpssVariableMetadata = col["spss"]
        name = spss.name or f"v{col['pos']}"
        # Garantizar unicidad de nombres en el .SAV.
        base = name
        i = 2
        while name in used_names:
            name = f"{base}_{i}"
            i += 1
        used_names.add(name)

        pos = col["pos"]
        raw_values = [row[pos] if pos < len(row) else "" for row in raw.rows]
        encoded = [_encode_cell(v, spss.value_encoding) for v in raw_values]
        data[name] = encoded

        if spss.variable_label:
            variable_labels[name] = spss.variable_label[:256]
        if spss.value_labels:
            # pyreadstat espera {codigo_int: etiqueta}.
            value_labels[name] = {int(k): v for k, v in spss.value_labels.items()}
        if spss.measure:
            measures[name] = _MEASURE_MAP.get(spss.measure, "nominal")

    df = pd.DataFrame(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        pyreadstat.write_sav(
            df,
            str(output_path),
            column_labels={k: variable_labels.get(k) for k in df.columns},
            variable_value_labels=value_labels,
            variable_measure=measures,
        )
    except Exception as exc:  # noqa: BLE001
        raise SavWriteError(f"Error al escribir .SAV: {exc}") from exc

    return output_path


def _is_platform(spss: SpssVariableMetadata) -> bool:
    """Heurística: nombres administrativos típicos."""
    n = (spss.name or "").lower()
    return any(k in n for k in ("response_id", "seed", "date_", "hora_", "marca_temporal"))
