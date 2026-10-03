"""Paquete compartido de Indagata.

Contiene la capa de datos común a todos los microservicios: la Base de
SQLAlchemy, la sesión de BD, la configuración (settings), utilidades de
seguridad, los modelos ORM, los esquemas Pydantic y los repositorios.

Cualquier servicio importa desde aquí para no duplicar tablas ni DTOs:

    from shared.db.session import get_db
    from shared.models import InstrumentoProcesado, Usuario
    from shared.schemas import InstrumentoRead
"""
