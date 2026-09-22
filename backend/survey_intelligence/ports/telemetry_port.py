# survey_intelligence/ports/telemetry_port.py
"""
TelemetryPort: contrato de dependencia para observabilidad.

El SIS emite eventos (spans por etapa, métricas) sin conocer el backend concreto
(logs, OpenTelemetry, pipeline_ingesta_log del host). Nunca se emite PII: solo
estructura y métricas, no contenidos de respuestas de encuestados (design.md §16).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TelemetryPort(Protocol):
    """Puerto para emitir eventos de telemetría."""

    def event(self, name: str, attrs: dict) -> None:
        """Emite un evento con un nombre y atributos (métricas/estructura, sin PII)."""
        ...


class NullTelemetry:
    """Implementación por defecto no-op: descarta todos los eventos."""

    def event(self, name: str, attrs: dict) -> None:  # noqa: ARG002
        return None
