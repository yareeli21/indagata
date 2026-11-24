"""Lógica de autenticación y de gestión de usuarios.

Login con bloqueo: 5 contraseñas incorrectas seguidas bloquean la cuenta 15 minutos; una cuenta desactivada no
entra. Gestión (solo administrador): listar, editar nombre/rol/activo, restablecer contraseña y eliminar. Eliminar
solo se permite en cuentas sin instrumentos, porque raw_data.id_owner borra en cascada todo su trabajo; para quitar
el acceso a alguien con instrumentos se desactiva. Nadie puede desactivarse, quitarse el rol de administrador ni
eliminarse a sí mismo, y siempre queda al menos un administrador activo (24 nov 2026).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.schemas import ActualizarUsuarioRequest, RegisterRequest
from shared.auth import ROL_ADMINISTRADOR, ROLES_VALIDOS, hashear_password, verificar_password
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15
_HASH_FICTICIO = "$2b$12$" + "x" * 53


def _ahora() -> datetime:
    return datetime.now()


def _error(codigo: int, mensaje: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=mensaje)


def autenticar(db: Session, email: str, password: str) -> Usuario:
    """Verifica email + password con bloqueo por intentos. Devuelve el Usuario o lanza 401/403/429."""
    usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email.strip().lower()).first()
    if usuario is not None and usuario.bloqueado_hasta and usuario.bloqueado_hasta > _ahora():
        minutos = max(1, round((usuario.bloqueado_hasta - _ahora()).total_seconds() / 60))
        raise _error(status.HTTP_429_TOO_MANY_REQUESTS,
                     f"Demasiados intentos fallidos. Vuelve a intentarlo en {minutos} minuto(s).")
    # Se verifica el hash aunque el usuario no exista, para no revelar por el tiempo si un email está registrado.
    ok = verificar_password(password, usuario.password_hash if usuario else _HASH_FICTICIO)
    if usuario is None or not ok:
        if usuario is not None:
            usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
            if usuario.intentos_fallidos >= MAX_INTENTOS:
                usuario.bloqueado_hasta = _ahora() + timedelta(minutes=MINUTOS_BLOQUEO)
                usuario.intentos_fallidos = 0
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos.",
                            headers={"WWW-Authenticate": "Bearer"})
    if not usuario.activo:
        raise _error(status.HTTP_403_FORBIDDEN, "Tu cuenta está desactivada. Pide a un administrador que la reactive.")
    if usuario.intentos_fallidos or usuario.bloqueado_hasta:
        usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
        db.commit()
    return usuario


def registrar_usuario(db: Session, datos: RegisterRequest) -> Usuario:
    """Crea un usuario nuevo. El rol debe ser válido y el email único."""
    _validar_rol(datos.rol)
    email = datos.email.strip().lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first() is not None:
        raise _error(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese email.")
    usuario = Usuario(nombre=datos.nombre.strip(), email=email, password_hash=hashear_password(datos.password),
                      rol=datos.rol, activo=True, intentos_fallidos=0)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _validar_rol(rol: str) -> None:
    if rol not in ROLES_VALIDOS:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY,
                     f"Rol inválido. Valores aceptados: {', '.join(sorted(ROLES_VALIDOS))}.")


def instrumentos_por_usuario(db: Session) -> dict[int, int]:
    return dict(db.query(RawData.id_owner, func.count(RawData.id_crudo)).group_by(RawData.id_owner).all())


def listar(db: Session) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.usuario_id).all()


def _obtener(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise _error(status.HTTP_404_NOT_FOUND, "No existe ese usuario.")
    return usuario


def _otros_admins_activos(db: Session, usuario_id: int) -> int:
    return db.query(Usuario).filter(Usuario.rol == ROL_ADMINISTRADOR, Usuario.activo.is_(True),
                                    Usuario.usuario_id != usuario_id).count()


def actualizar(db: Session, usuario_id: int, datos: ActualizarUsuarioRequest, admin: Usuario) -> Usuario:
    """Edita nombre, rol o estado. Protege al propio administrador y al último administrador activo."""
    usuario = _obtener(db, usuario_id)
    deja_de_ser_admin = (usuario.rol == ROL_ADMINISTRADOR
                         and ((datos.rol is not None and datos.rol != ROL_ADMINISTRADOR) or datos.activo is False))
    if usuario.usuario_id == admin.usuario_id and (datos.activo is False or deja_de_ser_admin):
        raise _error(status.HTTP_409_CONFLICT, "No puedes desactivarte ni quitarte el rol de administrador a ti mismo.")
    if deja_de_ser_admin and _otros_admins_activos(db, usuario.usuario_id) == 0:
        raise _error(status.HTTP_409_CONFLICT, "Debe quedar al menos un administrador activo.")
    if datos.nombre is not None:
        if not datos.nombre.strip():
            raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede quedar vacío.")
        usuario.nombre = datos.nombre.strip()
    if datos.rol is not None:
        _validar_rol(datos.rol)
        usuario.rol = datos.rol
    if datos.activo is not None:
        usuario.activo = datos.activo
        if datos.activo:  # al reactivar, se quita también un bloqueo pendiente
            usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    db.commit()
    db.refresh(usuario)
    return usuario


def restablecer_password(db: Session, usuario_id: int, nueva: str) -> Usuario:
    """El administrador pone una contraseña nueva (y desbloquea la cuenta)."""
    usuario = _obtener(db, usuario_id)
    usuario.password_hash = hashear_password(nueva)
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_mi_password(db: Session, usuario: Usuario, actual: str, nueva: str) -> None:
    if not verificar_password(actual, usuario.password_hash):
        raise _error(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta.")
    if actual == nueva:
        raise _error(status.HTTP_400_BAD_REQUEST, "La contraseña nueva debe ser distinta de la actual.")
    usuario.password_hash = hashear_password(nueva)
    db.commit()


def eliminar(db: Session, usuario_id: int, admin: Usuario) -> None:
    """Borra una cuenta sin instrumentos. Con instrumentos se desactiva (borrarla borraría su trabajo)."""
    usuario = _obtener(db, usuario_id)
    if usuario.usuario_id == admin.usuario_id:
        raise _error(status.HTTP_409_CONFLICT, "No puedes eliminar tu propia cuenta.")
    if usuario.rol == ROL_ADMINISTRADOR and usuario.activo and _otros_admins_activos(db, usuario.usuario_id) == 0:
        raise _error(status.HTTP_409_CONFLICT, "Debe quedar al menos un administrador activo.")
    n = instrumentos_por_usuario(db).get(usuario.usuario_id, 0)
    if n:
        raise _error(status.HTTP_409_CONFLICT,
                     f"Esta cuenta tiene {n} instrumento(s); eliminarla los borraría. Desactívala en su lugar.")
    db.delete(usuario)
    db.commit()
