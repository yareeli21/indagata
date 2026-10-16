"""Dependencias FastAPI del módulo de vectorización.

Reutiliza la sesión de BD y el usuario de desarrollo de shared, igual que el
instrument-service. En producción, la autenticación se integrará con el JWT del
api-gateway desactivando AUTH_DEV_MODE.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR, TokenError, decodificar_token
from shared.db.core.config import settings
from shared.db.session import get_db
from shared.models.usuario import Usuario


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> Usuario:
    """Usuario actual. En modo desarrollo resuelve DEV_USER_ID sin token."""
    if settings.AUTH_DEV_MODE:
        usuario = db.get(Usuario, settings.DEV_USER_ID)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"MODO DESARROLLO: el usuario de prueba "
                    f"(usuario_id={settings.DEV_USER_ID}) no existe en tt_rag.usuario."
                ),
            )
        return usuario

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida (JWT aún no integrado en este servicio).",
        headers={"WWW-Authenticate": "Bearer"},
    )


_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_usuario_jwt(
    token: Annotated[str, Depends(_oauth2)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Usuario del JWT del api-gateway (misma SECRET_KEY); 401 si no es válido.

    Lo usan los endpoints del perfil semántico, que registran quién aceptó cada KPI.
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        datos = decodificar_token(token)
    except TokenError:
        raise cred_exc
    usuario = db.get(Usuario, datos.usuario_id)
    if usuario is None:
        raise cred_exc
    if usuario.rol not in (ROL_INVESTIGADOR, ROL_ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta operación.")
    return usuario


DBSession = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[Usuario, Depends(get_current_user)]
InvestigadorJWT = Annotated[Usuario, Depends(get_usuario_jwt)]
