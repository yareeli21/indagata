"""Dependencias de autenticación del gateway.

`get_current_user` valida el Bearer token y carga el Usuario desde la BD.
`require_rol(...)` construye una dependencia que exige uno de los roles dados.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.auth import TokenError, decodificar_token
from shared.db.session import get_db
from shared.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Decodifica el JWT, valida y devuelve el Usuario. 401 si algo falla."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = decodificar_token(token)
    except TokenError:
        raise cred_exc

    usuario = db.get(Usuario, data.usuario_id)
    if usuario is None:
        raise cred_exc
    return usuario


def require_rol(*roles: str):
    """Crea una dependencia que exige que el usuario tenga uno de `roles`."""

    def _checker(
        usuario: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta operación.",
            )
        return usuario

    return _checker


DBSession = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[Usuario, Depends(get_current_user)]
