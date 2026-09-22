# survey_intelligence/ports/clock_port.py
"""
ClockPort: contrato de dependencia para la hora actual.

Inyectable para que los tests sean reproducibles (reloj fijo). El SIS nunca llama
a datetime.now() directamente en la lógica de negocio.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """Puerto para obtener el instante actual."""

    def now(self) -> datetime:
        """Devuelve el instante actual (se recomienda UTC, timezone-aware)."""
        ...


class SystemClock:
    """Implementación por defecto: reloj del sistema en UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
