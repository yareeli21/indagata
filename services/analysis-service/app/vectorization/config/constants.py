"""Constantes del módulo de vectorización e inferencia de KPIs.

Define el tipo de instrumento, los nombres de las colecciones Chroma, los
parámetros de búsqueda y —lo más importante— el mapeo de QUÉ metadatos clave se
extraen del JSON por tipo de instrumento para construir el vector del summary.

Solo lo CLAVE entra al vector (instrumento original + metadatos selectos). Las
respuestas de los respondentes NO se vectorizan: meterían ruido en la búsqueda
semántica de KPIs.
"""
from __future__ import annotations

from enum import Enum


class TipoInstrumento(str, Enum):
    """Tipos de instrumento soportados (alineado con raw_data.tipo_instrumento)."""

    ENCUESTA = "encuesta"
    ENTREVISTA = "entrevista"
    PRUEBA_ESTANDARIZADA = "prueba_estandarizada"


# ── Metadatos Dublin Core base (siempre, cualquier tipo) ─────────────────────
# Claves tal como aparecen en metadata.dublin_core del JSON (prefijo "dc:").
DUBLIN_CORE_KEYS: tuple[str, ...] = (
    "dc:title",
    "dc:subject",
    "dc:description",
    "dc:coverage",
)

# ── Metadatos específicos por tipo (dentro de metadata.survey_specific) ──────
# Nombres de campo esperados en el JSON. La extracción es tolerante: si un campo
# falta, se omite sin romper.
CAMPOS_ESPECIFICOS_POR_TIPO: dict[TipoInstrumento, tuple[str, ...]] = {
    TipoInstrumento.ENCUESTA: (
        "carrera",
        "notas_contextuales",
        "notas_interpretacion",
        "constructo_principal",
        "dimensiones",
        "palabras_clave",
    ),
    TipoInstrumento.ENTREVISTA: (
        "objetivo",
        "metodologia",
    ),
    TipoInstrumento.PRUEBA_ESTANDARIZADA: (
        "unidad_de_aprendizaje",
        "taxonomia_bloom",
        "objetivo_de_evaluacion",
        "competencias",
    ),
}

# Etiquetas legibles para construir el texto del summary (campo → encabezado).
ETIQUETAS_CAMPOS: dict[str, str] = {
    "dc:title": "Título",
    "dc:subject": "Materia",
    "dc:description": "Descripción",
    "dc:coverage": "Cobertura",
    "carrera": "Carrera",
    "notas_contextuales": "Notas contextuales",
    "notas_interpretacion": "Notas de interpretación",
    "constructo_principal": "Constructo principal",
    "dimensiones": "Dimensiones",
    "palabras_clave": "Palabras clave",
    "objetivo": "Objetivo",
    "metodologia": "Metodología",
    "unidad_de_aprendizaje": "Unidad de aprendizaje",
    "taxonomia_bloom": "Taxonomía de Bloom",
    "objetivo_de_evaluacion": "Objetivo de la evaluación",
    "competencias": "Competencias",
}

# ── Placeholders de prueba para campos de notas que llegan vacíos ────────────
# El JSON de ejemplo trae notas_contextuales / notas_interpretacion vacías; para
# que el vector no quede hueco se rellenan con un texto de prueba derivado.
PLACEHOLDERS_NOTAS: dict[str, str] = {
    "notas_contextuales": (
        "Instrumento aplicado en contexto universitario mexicano; respuestas de "
        "percepción estudiantil con fines demostrativos."
    ),
    "notas_interpretacion": (
        "Interpretar los resultados como percepción autorreportada; no sustituyen "
        "registros administrativos ni medidas objetivas."
    ),
}

# Clave donde se insertan los KPIs aceptados en el JSON enriquecido.
INFERRED_KPIS_KEY = "inferred_kpis"

# Nombre lógico del "chunk" único del summary (una fila en documento_vectorizado).
SUMMARY_SECCION = "summary_instrument"
