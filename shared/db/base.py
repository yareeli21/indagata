"""Base declarativa única para TODOS los modelos del proyecto.

Todos los modelos de `shared/models` heredan de esta `Base`. Al compartir una
sola `Base`, SQLAlchemy conoce el mapa completo de tablas y relaciones sin
importar qué microservicio la cargue. El esquema físico vive en
`infrastructure/postgres/init/01_schema.sql`; aquí solo lo reflejamos.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

# Esquema PostgreSQL donde viven todas las tablas.
SCHEMA = "tt_rag"


class Base(DeclarativeBase):
    """Base común de todos los modelos ORM. No instanciar directamente."""

    pass
