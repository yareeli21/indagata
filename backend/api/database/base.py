# app/database/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Clase base de la que heredan todos los modelos (tablas) del proyecto.
    SQLAlchemy usa esto para saber qué clases representan tablas
    y poder generar el esquema, hacer queries, etc.
    """
    pass