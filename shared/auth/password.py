"""Hashing y verificación de contraseñas con bcrypt (passlib)."""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashear_password(password_plano: str) -> str:
    """Genera el hash bcrypt de una contraseña nueva (alta de usuario)."""
    return _pwd_context.hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara una contraseña en claro contra su hash almacenado."""
    return _pwd_context.verify(password_plano, password_hash)
