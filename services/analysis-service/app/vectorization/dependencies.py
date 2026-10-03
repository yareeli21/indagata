"""Dependencias FastAPI del módulo de vectorización.

Reutiliza la sesión de BD y el usuario de desarrollo de shared, igual que el
instrument-service. En producción, la autenticación se integrará con el JWT del
api-gateway desactivando AUTH_DEV_MODE.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

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


DBSession = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[Usuario, Depends(get_current_user)]
