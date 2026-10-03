"""Emisión y validación de JSON Web Tokens (JWT).

El token es una credencial firmada con `settings.SECRET_KEY` (HS256 por defecto).
Lleva el id del usuario (`sub`), su rol y la expiración (`exp`). El gateway lo
emite al hacer login; cualquier servicio lo valida con la misma SECRET_KEY sin
consultar la base de datos ni llamar al gateway.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from shared.db.core.config import settings


class TokenError(Exception):
    """El token es inválido, está expirado o le faltan claims."""


@dataclass(frozen=True)
class TokenData:
    """Datos extraídos de un JWT válido."""

    usuario_id: int
    rol: str | None


def crear_access_token(
    usuario_id: int,
    rol: str | None,
    expires_minutes: int | None = None,
) -> str:
    """Crea un JWT firmado para un usuario.

    Args:
        usuario_id:      Se guarda en el claim `sub`.
        rol:             Se guarda en el claim `rol`.
        expires_minutes: Minutos de validez (default: settings.ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        El token codificado (string).
    """
    minutos = (
        expires_minutes
        if expires_minutes is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expira = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": expira,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token: str) -> TokenData:
    """Valida y decodifica un JWT.

    Returns:
        TokenData con usuario_id y rol.

    Raises:
        TokenError: si la firma es inválida, el token expiró o falta `sub`.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise TokenError(f"Token inválido o expirado: {exc}") from exc

    sub = payload.get("sub")
    if sub is None:
        raise TokenError("El token no contiene 'sub' (usuario_id).")

    try:
        usuario_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise TokenError("El claim 'sub' no es un usuario_id válido.") from exc

    return TokenData(usuario_id=usuario_id, rol=payload.get("rol"))
