# app/dependencies/dependencies_instrumentos.py
"""
Dependencias FastAPI compartidas por carga y visualización.

Todas las dependencias de autenticación y acceso viven aquí.
Se usan en los dos routers mediante Depends():
  - routers_carga.py       → UsuarioActual, InstrumentoProp, DBSession
  - routers_visualizacion.py → UsuarioActual, InstrumentoAcceso, DBSession

Jerarquía:
  get_current_user
      ├── puede_acceder_o_403   (lectura: TODOS - RAG colaborativo)
      └── verificar_propietario (escritura: solo propietario)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.core.config import settings
from api.database.database import get_db
from api.models.models_instrumentos import InstrumentoProcesado, PermisoInstrumento, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ MODO DESARROLLO — AUTENTICACIÓN DESACTIVADA TEMPORALMENTE
#
# Mientras no exista el endpoint POST /auth/token, esta función devuelve un
# usuario fijo (usuario_id=1) sin pedir token. Esto permite probar todos los
# endpoints de instrumentos en Postman sin autenticación.
#
# CÓMO REACTIVAR LA AUTENTICACIÓN REAL cuando el login esté implementado:
#   1. Borra el bloque marcado "BYPASS DE DESARROLLO" de esta función.
#   2. Descomenta el bloque marcado "AUTENTICACIÓN REAL" de más abajo.
#   3. No toques nada más: los tipos anotados, las demás dependencias y los
#      routers ya están listos para usar el token real.
# ═══════════════════════════════════════════════════════════════════════════

# ID del usuario de desarrollo. Debe existir en tt_rag.usuarios.
_DEV_USER_ID = 1


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """
    [MODO DESARROLLO] Devuelve un usuario fijo sin pedir token.
    Reemplazar por la versión real cuando el login esté implementado.
    """
    # ─── BYPASS DE DESARROLLO ────────────────────────────────────────────────
    usuario = db.get(Usuario, _DEV_USER_ID)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"MODO DESARROLLO: el usuario de prueba (usuario_id={_DEV_USER_ID}) "
                f"no existe en tt_rag.usuarios. Créalo o cambia _DEV_USER_ID."
            ),
        )
    return usuario


# ═══════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN REAL — descomentar cuando exista POST /auth/token
# y borrar la función get_current_user de arriba (el bypass de desarrollo).
# ═══════════════════════════════════════════════════════════════════════════
#
# def get_current_user(
#     token: Annotated[str, Depends(oauth2_scheme)],
#     db:    Annotated[Session, Depends(get_db)],
# ) -> Usuario:
#     """Decodifica el JWT y devuelve el usuario. Lanza 401 si es inválido."""
#     exc = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="No autenticado. Token inválido o expirado.",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#         uid_str: str | None = payload.get("sub")
#         if uid_str is None:
#             raise exc
#     except JWTError:
#         raise exc
#
#     try:
#         usuario_id = int(uid_str)
#     except (ValueError, TypeError):
#         raise exc
#
#     usuario = db.get(Usuario, usuario_id)
#     if usuario is None:
#         raise exc
#     return usuario


def get_instrumento_o_404(
    instrumento_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """Obtiene el instrumento o lanza 404."""
    instrumento = db.get(InstrumentoProcesado, instrumento_id)
    if instrumento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrumento {instrumento_id} no encontrado.",
        )
    return instrumento


def puede_acceder_o_403(
    instrumento:    Annotated[InstrumentoProcesado, Depends(get_instrumento_o_404)],
    usuario_actual: Annotated[Usuario, Depends(get_current_user)],
    db:             Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """
    Lectura: todos los instrumentos son públicos (RAG colaborativo).
    Solo verifica que el instrumento existe (ya validado por get_instrumento_o_404).
    """
    return instrumento


def verificar_propietario(
    instrumento:    Annotated[InstrumentoProcesado, Depends(get_instrumento_o_404)],
    usuario_actual: Annotated[Usuario, Depends(get_current_user)],
    db:             Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """Escritura: solo el propietario puede operar."""
    permiso = (
        db.query(PermisoInstrumento)
        .filter(
            PermisoInstrumento.instrumento_id == instrumento.instrumento_id,
            PermisoInstrumento.usuario_id == usuario_actual.usuario_id,
        )
        .first()
    )
    if permiso is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede realizar esta operación.")
    return instrumento


# Tipos anotados — usar directamente en las firmas de los routers
UsuarioActual     = Annotated[Usuario, Depends(get_current_user)]
InstrumentoAcceso = Annotated[InstrumentoProcesado, Depends(puede_acceder_o_403)]
InstrumentoProp   = Annotated[InstrumentoProcesado, Depends(verificar_propietario)]
DBSession         = Annotated[Session, Depends(get_db)]
