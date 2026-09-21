# survey_intelligence/ports/__init__.py
"""
Puertos (contratos de dependencia) del SIS.

Los protocolos definen la forma; el host inyecta los adaptadores concretos.
Se incluyen implementaciones por defecto seguras para operar sin infraestructura:
  - SystemClock      : reloj UTC del sistema.
  - UuidGenerator    : IDs UUID4.
  - NullTelemetry    : telemetría no-op.

Nota: la resolución de codebooks es determinística (etapa S5), sin RAG ni
embeddings. El RAG principal del sistema se trabaja fuera del SIS.
"""
from __future__ import annotations

from survey_intelligence.ports.clock_port import ClockPort, SystemClock
from survey_intelligence.ports.ids_port import IdGeneratorPort, UuidGenerator
from survey_intelligence.ports.llm_port import LLMPort
from survey_intelligence.ports.telemetry_port import NullTelemetry, TelemetryPort

__all__ = [
    # Protocolos
    "LLMPort",
    "ClockPort",
    "IdGeneratorPort",
    "TelemetryPort",
    # Implementaciones por defecto
    "SystemClock",
    "UuidGenerator",
    "NullTelemetry",
]
