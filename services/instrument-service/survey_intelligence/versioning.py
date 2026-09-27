# survey_intelligence/versioning.py
"""
Versionamiento del Survey Intelligence Service (SIS).

Tres ejes de versión independientes (ver design.md §17):
  - SCHEMA_VERSION   : forma de los contratos JSON (SemVer).
  - PIPELINE_VERSION : comportamiento (reglas, prompts, heurísticas).
  - canonical_id     : identidad determinística del insumo (se calcula por request,
                       no vive aquí).
"""
from __future__ import annotations

# Forma de los contratos JSON. Major = ruptura; minor = campos nuevos opcionales;
# patch = correcciones no estructurales.
SCHEMA_VERSION: str = "sis-1.0.0"

# Comportamiento del pipeline. Sube al promover una regla o cambiar un prompt,
# aunque el schema no cambie.
PIPELINE_VERSION: str = "pipeline-1.0.0"
