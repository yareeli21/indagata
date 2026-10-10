"""Dependencias FastAPI del storage-service.

El storage-service es INTERNO: lo llaman los demás microservicios con un token de
servicio (`shared.auth.servicio`). Un administrador también puede usarlo a través
del api-gateway (`/almacenamiento/*`). Los investigadores NO acceden directo:
descargan por el visualization-service, que aplica la regla de propiedad.

El rol se toma del claim firmado del JWT (sin consultar la BD), para que las
operaciones de archivo sigan funcionando aunque Postgres no esté disponible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR, ROL_SERVICIO, TokenError, decodificar_token
from shared.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class Principal:
    """Quién hace la petición: un servicio interno o un usuario."""

    usuario_id: int
    rol: str | None


def get_principal(token: Annotated[str, Depends(oauth2_scheme)]) -> Principal:
    """Valida el Bearer token (de servicio o de usuario). 401 si es inválido."""
    try:
        datos = decodificar_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(usuario_id=datos.usuario_id, rol=datos.rol)


def requiere_servicio_o_admin(
    principal: Annotated[Principal, Depends(get_principal)],
) -> Principal:
    """Solo servicios internos o administradores."""
    if principal.rol not in (ROL_SERVICIO, ROL_ADMINISTRADOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El almacenamiento es interno: usa el servicio correspondiente.",
        )
    return principal


DBSession = Annotated[Session, Depends(get_db)]
Autenticado = Annotated[Principal, Depends(get_principal)]
Interno = Annotated[Principal, Depends(requiere_servicio_o_admin)]
