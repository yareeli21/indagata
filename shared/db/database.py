"""Compatibilidad: re-exporta el motor/sesión/Base desde los módulos canónicos.

Mantener imports antiguos (`from shared.db.database import get_db, Base`)
funcionando. El código nuevo debe importar de `shared.db.session` y
`shared.db.base` directamente.
"""
from shared.db.base import Base
from shared.db.session import SessionLocal, engine, get_db, init_db

__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_db"]
