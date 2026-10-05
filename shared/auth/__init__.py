"""Utilidades de autenticación compartidas por los microservicios.

Centraliza el hashing de contraseñas (bcrypt) y la emisión/validación de JWT.
El gateway EMITE el token aquí; los servicios lo VALIDAN con la misma lógica y la
misma SECRET_KEY, de modo que no haya divergencias entre servicios.

    from shared.auth import crear_access_token, decodificar_token, TokenData
    from shared.auth import hashear_password, verificar_password
    from shared.auth import ROL_INVESTIGADOR, ROL_ADMINISTRADOR
"""
from __future__ import annotations

from shared.auth.jwt_handler import (
    TokenData,
    TokenError,
    crear_access_token,
    decodificar_token,
)
from shared.auth.password import hashear_password, verificar_password
from shared.auth.roles import ROL_ADMINISTRADOR, ROL_INVESTIGADOR, ROLES_VALIDOS

__all__ = [
    "crear_access_token",
    "decodificar_token",
    "TokenData",
    "TokenError",
    "hashear_password",
    "verificar_password",
    "ROL_INVESTIGADOR",
    "ROL_ADMINISTRADOR",
    "ROLES_VALIDOS",
]
