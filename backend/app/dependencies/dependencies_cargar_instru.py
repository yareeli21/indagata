# cargar_instru/dependencies.py
"""
Dependencias FastAPI para el módulo de gestión de instrumentos.

Estas funciones se inyectan en los endpoints mediante Depends().
Centralizan la autenticación, la verificación de acceso y la
obtención de entidades comunes, evitando repetición en los handlers.

Jerarquía de dependencias:

  get_current_user
      └── puede_acceder_o_403     (lectura: público O propietario)
              └── verificar_propietario  (escritura: solo propietario)

  get_instrumento_o_404           (base interna, sin verificación de permisos)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from cargar_instru.models import InstrumentoProcesado, PermisoInstrumento, Usuario

# ---------------------------------------------------------------------------
# Esquema OAuth2
# Apunta al endpoint de login del módulo de autenticación.
# Este módulo solo consume el token — no lo emite.
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ---------------------------------------------------------------------------
# get_current_user
# Decodifica el JWT y devuelve el usuario autenticado.
# ---------------------------------------------------------------------------

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """
    Extrae y valida el JWT Bearer token.
    Consulta la BD para verificar que el usuario existe.

    Lanza 401 si:
      - El token es inválido o está expirado.
      - El payload no contiene 'sub' con el usuario_id.
      - El usuario_id no existe en la tabla usuarios.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        usuario_id_str: str | None = payload.get("sub")
        if usuario_id_str is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    try:
        usuario_id = int(usuario_id_str)
    except (ValueError, TypeError):
        raise credenciales_invalidas

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise credenciales_invalidas

    return usuario


# ---------------------------------------------------------------------------
# get_instrumento_o_404
# Obtiene un instrumento por ID. No verifica permisos.
# Base para las dependencias de acceso más específicas.
# ---------------------------------------------------------------------------

def get_instrumento_o_404(
    instrumento_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """
    Busca el instrumento en la BD.
    Lanza 404 si no existe.
    No verifica permisos — eso lo hacen las dependencias que la usan.
    """
    instrumento = db.get(InstrumentoProcesado, instrumento_id)
    if instrumento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrumento {instrumento_id} no encontrado.",
        )
    return instrumento


# ---------------------------------------------------------------------------
# puede_acceder_o_403
# Verifica que el usuario puede LEER el instrumento.
# Regla: público OR propietario.
# ---------------------------------------------------------------------------

def puede_acceder_o_403(
    instrumento: Annotated[InstrumentoProcesado, Depends(get_instrumento_o_404)],
    usuario_actual: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """
    Verifica que el usuario tiene acceso de lectura al instrumento.

    Permite el acceso si:
      - El instrumento es público (visibilidad = 'publico'), O
      - El usuario es el propietario (tiene registro en permiso_instrumento).

    Lanza 403 si el instrumento es privado y el usuario no es el propietario.
    Devuelve el instrumento para que el handler pueda usarlo directamente.
    """
    if instrumento.visibilidad == "publico":
        return instrumento

    permiso = (
        db.query(PermisoInstrumento)
        .filter(
            PermisoInstrumento.instrumento_id == instrumento.instrumento_id,
            PermisoInstrumento.usuario_id == usuario_actual.usuario_id,
        )
        .first()
    )

    if permiso is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este instrumento.",
        )

    return instrumento


# ---------------------------------------------------------------------------
# verificar_propietario
# Verifica que el usuario puede MODIFICAR el instrumento.
# Regla: solo el propietario (registro en permiso_instrumento).
# ---------------------------------------------------------------------------

def verificar_propietario(
    instrumento: Annotated[InstrumentoProcesado, Depends(get_instrumento_o_404)],
    usuario_actual: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InstrumentoProcesado:
    """
    Verifica que el usuario es el propietario del instrumento.

    Úsala en endpoints de escritura:
      - PATCH /metadatos
      - PATCH /visibilidad
      - POST /versiones
      - DELETE /{id}

    Lanza 403 si el usuario no tiene registro en permiso_instrumento
    para este instrumento.
    Devuelve el instrumento para que el handler pueda usarlo directamente.
    """
    permiso = (
        db.query(PermisoInstrumento)
        .filter(
            PermisoInstrumento.instrumento_id == instrumento.instrumento_id,
            PermisoInstrumento.usuario_id == usuario_actual.usuario_id,
        )
        .first()
    )

    if permiso is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede realizar esta operación.",
        )

    return instrumento


# ---------------------------------------------------------------------------
# Tipos anotados — Para usar con Depends() en las firmas de los routers
# ---------------------------------------------------------------------------

UsuarioActual       = Annotated[Usuario, Depends(get_current_user)]
InstrumentoAcceso   = Annotated[InstrumentoProcesado, Depends(puede_acceder_o_403)]
InstrumentoProp     = Annotated[InstrumentoProcesado, Depends(verificar_propietario)]
DBSession           = Annotated[Session, Depends(get_db)]
