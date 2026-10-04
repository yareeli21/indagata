"""
Routers module for Storage Service

Organiza todos los endpoints del servicio
"""

from . import health, documents

__all__ = ["health", "documents"]
