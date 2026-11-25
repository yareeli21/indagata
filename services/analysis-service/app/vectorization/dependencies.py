"""Dependencias FastAPI del módulo de vectorización.

Todas las rutas exigen el JWT del api-gateway (misma SECRET_KEY), igual que el resto
de los servicios. Antes existía un «modo desarrollo» (`AUTH_DEV_MODE`) que resolvía un
usuario fijo sin token; se retiró porque este servicio se publica directo al
navegador (`VITE_ANALYSIS_URL`) y dejaba rutas como el reindexado de KPIs abiertas a
cualquiera.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR, TokenError, decodificar_token
from shared.db.session import get_db
from shared.models.usuario import Usuario

_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_usuario_jwt(
    token: Annotated[str, Depends(_oauth2)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Usuario del JWT del api-gateway; 401 si no es válido o la cuenta está desactivada."""
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
    if usuario is None or not usuario.activo:
        raise cred_exc
    if usuario.rol not in (ROL_INVESTIGADOR, ROL_ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta operación.")
    return usuario


# Se conserva el nombre para no tocar los routers: ahora también exige el JWT.
get_current_user = get_usuario_jwt

DBSession = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[Usuario, Depends(get_usuario_jwt)]
InvestigadorJWT = Annotated[Usuario, Depends(get_usuario_jwt)]
