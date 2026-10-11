"""Construcción del JSON de dominio con el esquema del seed (diseño §1.4).

Único punto que serializa a la forma de `storage/raw/inst_01.v1.json`. Produce
un **superconjunto compatible de lectura** del esquema del seed:

  - OMITE `synthetic_profiles` y `respondents[].profile_id` (artefactos de datos
    sintéticos sembrados; ningún consumidor real los lee).
  - `metadata.dublin_core` y `metadata.survey_specific` quedan vacíos al
    estandarizar (se pueblan en pasos posteriores del wizard).
  - `type` usa el vocabulario estandarizado (binaria|opcion_multiple|likert|
    numerica_continua|abierta), no los literales específicos del seed.

Entradas:
  - Tabular: `RawTable` + preguntas confirmadas (con su mapa a columnas) ->
    `instrument.sections[].questions[]` + `respondents[]` (una fila -> uno).
  - Documento: texto completo extraído -> una sola pregunta `abierta`,
    `respondents = []`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.parsing.raw_table import RawTable

_SECTION_ID = "s1"
_SECTION_NAME = "Reactivos del módulo"
_SCHEMA_VERSION = "1.0"

# Tipos que llevan `options` en el JSON de dominio.
_TIPOS_CON_OPCIONES = frozenset({"opcion_multiple", "binaria", "likert"})


@dataclass(frozen=True)
class PreguntaDominio:
    """Pregunta ya resuelta (confirmada + columna de origen) para el builder."""

    question_id: str
    text: str
    type: str
    es_demografica: bool
    columna: int | None  # índice de columna en RawTable (None para documento)
    options: list[str] | None = None
    scale_min: int | None = None
    scale_max: int | None = None


def _coaccionar_valor(valor: str, tipo: str) -> Any:
    """Coacciona una celda al tipo confirmado; vacío -> None."""
    cell = valor.strip()
    if not cell:
        return None
    if tipo == "likert":
        try:
            return int(float(cell))
        except (TypeError, ValueError):
            return cell
    if tipo == "numerica_continua":
        try:
            f = float(cell)
        except (TypeError, ValueError):
            return cell
        return int(f) if f.is_integer() else f
    if tipo == "binaria":
        try:
            f = float(cell)
            return int(f) if f.is_integer() else cell
        except (TypeError, ValueError):
            return cell
    return cell


def _pregunta_json(p: PreguntaDominio) -> dict[str, Any]:
    """Serializa una PreguntaDominio al esquema del seed."""
    out: dict[str, Any] = {"question_id": p.question_id, "text": p.text, "type": p.type}
    if p.type in _TIPOS_CON_OPCIONES and p.options:
        out["options"] = list(p.options)
    if p.type == "likert":
        if p.scale_min is not None:
            out["scale_min"] = p.scale_min
        if p.scale_max is not None:
            out["scale_max"] = p.scale_max
    return out


def _respondents_tabular(
    tabla: RawTable,
    preguntas: list[PreguntaDominio],
) -> list[dict[str, Any]]:
    """Una fila de datos -> un respondente (demographics + answers)."""
    demograficas = [p for p in preguntas if p.es_demografica and p.columna is not None]
    de_pregunta = [p for p in preguntas if not p.es_demografica and p.columna is not None]

    respondents: list[dict[str, Any]] = []
    for i, row in enumerate(tabla.rows, start=1):
        demographics: dict[str, Any] = {}
        for p in demograficas:
            valor = row[p.columna] if p.columna < len(row) else ""
            demographics[p.text] = _coaccionar_valor(valor, p.type)

        answers: dict[str, Any] = {}
        for p in de_pregunta:
            valor = row[p.columna] if p.columna < len(row) else ""
            answers[p.question_id] = _coaccionar_valor(valor, p.type)

        respondents.append(
            {
                "respondent_id": f"r_{i:04d}",
                "demographics": demographics,
                "answers": answers,
            }
        )
    return respondents


def construir_tabular(
    *,
    id_crudo: int,
    titulo: str,
    tabla: RawTable,
    preguntas: list[PreguntaDominio],
    note: str = "",
) -> dict[str, Any]:
    """Construye el JSON de dominio para un instrumento tabular (encuesta)."""
    questions = [_pregunta_json(p) for p in preguntas if not p.es_demografica]
    return {
        "instrument_id": f"upload_{id_crudo}",
        "schema_version": _SCHEMA_VERSION,
        "instrument": {
            "title": titulo,
            "objective": "",
            "dimensions_explored": [],
            "sections": [
                {
                    "section_id": _SECTION_ID,
                    "name": _SECTION_NAME,
                    "questions": questions,
                }
            ],
        },
        "metadata": {"dublin_core": {}, "survey_specific": {}},
        "design_reference": {"kpi_hints": [], "note": note},
        "respondents": _respondents_tabular(tabla, preguntas),
    }


def construir_documento(
    *,
    id_crudo: int,
    titulo: str,
    texto: str,
    note: str = "",
) -> dict[str, Any]:
    """Construye el JSON de dominio para un documento (entrevista/prueba).

    Una sola pregunta `abierta` con el texto COMPLETO del documento;
    `respondents = []`.
    """
    return {
        "instrument_id": f"upload_{id_crudo}",
        "schema_version": _SCHEMA_VERSION,
        "instrument": {
            "title": titulo,
            "objective": "",
            "dimensions_explored": [],
            "sections": [
                {
                    "section_id": _SECTION_ID,
                    "name": _SECTION_NAME,
                    "questions": [
                        {"question_id": "q1", "text": texto, "type": "abierta"}
                    ],
                }
            ],
        },
        "metadata": {"dublin_core": {}, "survey_specific": {}},
        "design_reference": {"kpi_hints": [], "note": note},
        "respondents": [],
    }
