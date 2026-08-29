# app/core/security.py
"""
Utilidades de seguridad: hashing y verificación de contraseñas.
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra su hash almacenado."""
    return pwd_context.verify(password_plano, password_hash)


def hashear_password(password_plano: str) -> str:
    """Genera el hash de una contraseña nueva (para registro de usuarios)."""
    return pwd_context.hash(password_plano)