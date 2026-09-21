# survey_intelligence/host_toolkit.py
"""
Superficie pública ADICIONAL del SIS para el host (generación de artefactos offline).

Además del flujo principal (SurveyIntelligenceService.process, expuesto en __init__),
el host necesita reutilizar algunos bloques determinísticos del motor para generar
artefactos fuera del pipeline completo:

  - dataset limpio (.csv) aplicando las transformaciones aprobadas;
  - archivo .SAV (IBM SPSS) con su diccionario.

Este módulo reúne esos bloques en un único punto público, para que el host NO tenga
que importar módulos internos del SIS (engine.*, pipeline.stages.*, export.*).
Es la frontera aprobada: si el SIS reorganiza sus internos, solo cambia este archivo.

Uso desde el host (vía services/sis_adapter.py):
    from survey_intelligence.host_toolkit import (
        read_csv, read_xlsx, normalize_name, unique_names,
        TransformDecision, apply_decisions,
        detect_platform, IngestionResult, build_canonical, profile,
        build_spss_dictionary, write_sav, SavWriteError,
    )
"""
from __future__ import annotations

# Lectura de tablas crudas.
from survey_intelligence.engine.readers import RawTable, read_csv, read_xlsx

# Normalización de nombres (mismo criterio que el Canonical builder).
from survey_intelligence.engine.profiling.name_normalizer import (
    normalize_name,
    unique_names,
)

# Motor de transformaciones (propose -> decide -> apply).
from survey_intelligence.engine.transforms import TransformDecision, apply_decisions

# Detección de plataforma y reconstrucción de Canonical determinístico.
from survey_intelligence.engine.heuristics.platform_columns import detect_platform
from survey_intelligence.pipeline.stages.s1_ingestion import IngestionResult
from survey_intelligence.pipeline.stages.s2_canonical_builder import build_canonical
from survey_intelligence.pipeline.stages.s3_data_profiler import profile

# Diccionario SPSS + escritura del .SAV.
from survey_intelligence.engine.spss.spss_mapper import build_spss_dictionary
from survey_intelligence.export.sav_writer import SavWriteError, write_sav

__all__ = [
    "RawTable",
    "read_csv",
    "read_xlsx",
    "normalize_name",
    "unique_names",
    "TransformDecision",
    "apply_decisions",
    "detect_platform",
    "IngestionResult",
    "build_canonical",
    "profile",
    "build_spss_dictionary",
    "write_sav",
    "SavWriteError",
]
