# survey_intelligence/ports/ids_port.py
"""
IdGeneratorPort: contrato de dependencia para generación de identificadores.

Usado para proposal_id, opportunity_id, etc. Inyectable para tests deterministas
(generador secuencial en vez de UUID aleatorio).
"""
from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class IdGeneratorPort(Protocol):
    """Puerto para generar identificadores únicos."""

    def new_id(self, prefix: str = "") -> str:
        """Genera un identificador único, opcionalmente con un prefijo."""
        ...


class UuidGenerator:
    """Implementación por defecto: UUID4."""

    def new_id(self, prefix: str = "") -> str:
        value = uuid.uuid4().hex
        return f"{prefix}{value}" if prefix else value
