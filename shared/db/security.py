"""Utilidades de seguridad compartidas: hashing/verificación de contraseñas y JWT.

Reutilizable por el api-gateway (login) y por cualquier servicio que necesite
validar un token. El hashing usa bcrypt vía passlib.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from shared.db.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ALGORITHM = "HS256"


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra su hash almacenado."""
    return pwd_context.verify(password_plano, password_hash)


def hashear_password(password_plano: str) -> str:
    """Genera el hash de una contraseña nueva (registro de usuarios)."""
    return pwd_context.hash(password_plano)


def crear_access_token(sub: str, extra: dict | None = None) -> str:
    """Crea un JWT firmado con el usuario (`sub`) y claims extra opcionales."""
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decodificar_access_token(token: str) -> dict | None:
    """Decodifica y valida un JWT. Devuelve el payload o None si es inválido."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        return None
