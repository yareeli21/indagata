"""Dependencias FastAPI del cleaning-service (JWT emitido por el api-gateway)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR, TokenError, decodificar_token
from shared.db.session import get_db
from shared.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Usuario del token; 401 si el token es inválido, expiró o el usuario no existe."""
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
    return usuario


def requiere_investigador(usuario: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
    """Solo investigadores y administradores limpian instrumentos."""
    if usuario.rol not in (ROL_INVESTIGADOR, ROL_ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta operación.")
    return usuario


def es_admin(usuario: Usuario) -> bool:
    return usuario.rol == ROL_ADMINISTRADOR


DBSession = Annotated[Session, Depends(get_db)]
Investigador = Annotated[Usuario, Depends(requiere_investigador)]
