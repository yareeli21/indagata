"""Extracción de los metadatos CLAVE del JSON del instrumento.

Lee `metadata.dublin_core` (claves con prefijo `dc:`) y `metadata.survey_specific`
y arma un diccionario ordenado {etiqueta_legible: valor} con solo los campos que
alimentan el vector del summary, según el tipo de instrumento.

Reglas de negocio:
  - Tolerante a faltantes: si un campo no está, se omite (no rompe).
  - `carrera` (encuestas) no vive en survey_specific sino por respondente
    (respondents[].demographics.carrera): se resuelve como el conjunto de carreras
    presentes, o se cae a la población objetivo.
  - `notas_contextuales` / `notas_interpretacion` que llegan vacías se rellenan
    con un placeholder de prueba para que el vector no quede hueco.
"""
from __future__ import annotations

from typing import Any

from app.vectorization.config.constants import (
    CAMPOS_ESPECIFICOS_POR_TIPO,
    DUBLIN_CORE_KEYS,
    ETIQUETAS_CAMPOS,
    PLACEHOLDERS_NOTAS,
    TipoInstrumento,
)


def _coerce_text(value: Any) -> str:
    """Convierte un valor (str, lista, número) a texto legible, o '' si vacío."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        partes = [_coerce_text(v) for v in value]
        return ", ".join(p for p in partes if p)
    return str(value)


def _resolver_carrera(data: dict[str, Any], survey_specific: dict[str, Any]) -> str:
    """Resuelve 'carrera' para encuestas.

    Prioridad: survey_specific.carrera → conjunto de carreras de los respondentes
    → poblacion_objetivo. Devuelve '' si no hay nada.
    """
    directa = _coerce_text(survey_specific.get("carrera"))
    if directa:
        return directa

    carreras: list[str] = []
    for r in data.get("respondents", []) or []:
        if not isinstance(r, dict):
            continue
        carrera = (r.get("demographics") or {}).get("carrera")
        c = _coerce_text(carrera)
        if c and c not in carreras:
            carreras.append(c)
    if carreras:
        return ", ".join(carreras)

    return _coerce_text(survey_specific.get("poblacion_objetivo"))


def extract_key_metadata(
    data: dict[str, Any], tipo: TipoInstrumento
) -> dict[str, str]:
    """Extrae los metadatos clave del JSON para el tipo dado.

    Returns:
        dict ordenado {etiqueta_legible: valor_texto}, solo con campos no vacíos.
    """
    metadata = data.get("metadata", {}) or {}
    dublin = metadata.get("dublin_core", {}) or {}
    survey = metadata.get("survey_specific", {}) or {}

    resultado: dict[str, str] = {}

    # ── Dublin Core base (siempre) ───────────────────────────────────────────
    for key in DUBLIN_CORE_KEYS:
        valor = _coerce_text(dublin.get(key))
        if valor:
            resultado[ETIQUETAS_CAMPOS.get(key, key)] = valor

    # ── Específicos por tipo ──────────────────────────────────────────────────
    for campo in CAMPOS_ESPECIFICOS_POR_TIPO[tipo]:
        if campo == "carrera":
            valor = _resolver_carrera(data, survey)
        else:
            valor = _coerce_text(survey.get(campo))

        # Rellenar notas vacías con placeholder de prueba.
        if not valor and campo in PLACEHOLDERS_NOTAS:
            valor = PLACEHOLDERS_NOTAS[campo]

        if valor:
            resultado[ETIQUETAS_CAMPOS.get(campo, campo)] = valor

    return resultado
