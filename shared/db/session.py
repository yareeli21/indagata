"""Motor y sesión de SQLAlchemy, compartidos por todos los microservicios.

Expone:
  - engine        : el motor conectado a PostgreSQL (DATABASE_URL de settings).
  - SessionLocal  : fábrica de sesiones.
  - get_db()      : dependency de FastAPI (abre/cierra sesión por request).
  - init_db()     : crea las tablas que falten (útil en desarrollo / tests).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.db.base import Base
from shared.db.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,   # descarta conexiones muertas antes de usarlas
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea todas las tablas declaradas en los modelos (si no existen).

    El esquema oficial es el SQL de infrastructure/postgres/init; esta función
    es una comodidad para desarrollo y pruebas. Importa los modelos para que
    queden registrados en la metadata antes de crear.
    """
    import shared.models  # noqa: F401  (registra todos los modelos en Base.metadata)

    Base.metadata.create_all(bind=engine)
