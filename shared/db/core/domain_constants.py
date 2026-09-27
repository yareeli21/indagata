# api/core/domain_constants.py
"""
Fuente única de las constantes de dominio (vocabularios cerrados).

Antes estas tuplas vivían duplicadas: en `models_instrumentos.py` (para los
CheckConstraint de la BD) y, en forma de `Literal[...]`, en `schemas_carga.py`
(para la validación Pydantic). Este módulo las centraliza para evitar que se
desincronicen.

Reglas:
  - Los MODELOS importan estas tuplas y las usan tal cual en sus CheckConstraint;
    el SQL generado es idéntico (mismo orden y valores).
  - Los SCHEMAS mantienen sus `Literal[...]` (necesarios para el tipado estático y
    Pydantic) y verifican en import-time, con `assert_literal_matches`, que sus
    valores coinciden con estas tuplas. Si alguien cambia una sin la otra, el
    arranque falla de inmediato con un mensaje claro.

Cualquier cambio de valores aquí es un cambio de contrato de dominio: revisar
migraciones de BD y `SCHEMA_VERSION` del SIS si aplica.
"""
from __future__ import annotations

# Tipos de instrumento soportados.
TIPOS_INSTRUMENTO: tuple[str, ...] = ("encuesta", "entrevista", "prueba_estandarizada")

# Estados del pipeline (campo `estado` de instrumento_procesado).
ESTADOS_PIPELINE: tuple[str, ...] = (
    "pendiente",
    "metadata_registrado",
    "etl_pendiente_limpieza",
    "etl_pendiente_enriquecimiento",
    "etl_aprobado",
    "en_ingesta",
    "vectorizado",
    "error",
)

# Resultados del log interno del pipeline.
RESULTADOS_LOG: tuple[str, ...] = ("en_proceso", "exitoso", "error")

# Tipos de propuesta del SIS/ETL.
TIPOS_PROPUESTA: tuple[str, ...] = ("transformacion", "metadato_enriquecido", "kpi_sugerido")

# Estados de decisión de una propuesta.
DECISIONES_PROPUESTA: tuple[str, ...] = ("pendiente", "aceptada", "rechazada")

# Scopes de oportunidades de mejora continua.
IMPROVEMENT_SCOPES: tuple[str, ...] = (
    "survey", "pipeline", "future_analysis",
    "validation_rule", "quality_heuristic", "pattern",
)

# Ciclo de vida de una oportunidad de mejora.
IMPROVEMENT_ESTADOS: tuple[str, ...] = (
    "proposed", "under_review", "accepted", "promoted", "rejected",
)


def assert_literal_matches(nombre: str, valores_literal: tuple[str, ...], canonicos: tuple[str, ...]) -> None:
    """
    Verifica en import-time que un conjunto de valores (p.ej. los de un Literal de
    Pydantic) coincide con la tupla canónica. Lanza AssertionError si divergen,
    para que la desincronización se detecte al arrancar y no en producción.
    """
    if set(valores_literal) != set(canonicos):
        faltan = set(canonicos) - set(valores_literal)
        sobran = set(valores_literal) - set(canonicos)
        raise AssertionError(
            f"Desincronización en '{nombre}': faltan={sorted(faltan)} sobran={sorted(sobran)}. "
            f"Alinea el Literal con api/core/domain_constants.py."
        )
