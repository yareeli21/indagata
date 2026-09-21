# app/dependencies/__init__.py
from api.dependencies.dependencies_instrumentos import (
    get_current_user,
    get_instrumento_o_404,
    puede_acceder_o_403,
    verificar_propietario,
    UsuarioActual,
    InstrumentoAcceso,
    InstrumentoProp,
    DBSession,
)

__all__ = [
    "get_current_user",
    "get_instrumento_o_404",
    "puede_acceder_o_403",
    "verificar_propietario",
    "UsuarioActual",
    "InstrumentoAcceso",
    "InstrumentoProp",
    "DBSession",
]
