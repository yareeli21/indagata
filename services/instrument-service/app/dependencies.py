"""Dependencias FastAPI del instrument-service.

Enfocado en lo que necesita el upload:
  - DBSession:      sesión de SQLAlchemy (shared.db.session.get_db).
  - UsuarioActual:  usuario autenticado. En desarrollo (AUTH_DEV_MODE) devuelve
                    un usuario fijo (DEV_USER_ID) sin exigir token, igual que el
                    bypass histórico del monolito.

Cuando exista el login real (POST /auth/token en el api-gateway), basta con
desactivar AUTH_DEV_MODE y conectar la validación del JWT aquí.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.db.session import get_db
from shared.models.usuario import Usuario


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> Usuario:
    """Devuelve el usuario actual.

    En modo desarrollo (AUTH_DEV_MODE=True) resuelve el usuario fijo
    DEV_USER_ID sin pedir token. En producción debe reemplazarse por la
    validación real del JWT emitido por el api-gateway.
    """
    if settings.AUTH_DEV_MODE:
        usuario = db.get(Usuario, settings.DEV_USER_ID)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"MODO DESARROLLO: el usuario de prueba "
                    f"(usuario_id={settings.DEV_USER_ID}) no existe en "
                    f"tt_rag.usuario. Créalo o ajusta DEV_USER_ID."
                ),
            )
        return usuario

    # Autenticación real pendiente de integrar con el api-gateway.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida (JWT aún no integrado en este servicio).",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Tipos anotados para usar directamente en las firmas de los routers.
DBSession = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[Usuario, Depends(get_current_user)]
