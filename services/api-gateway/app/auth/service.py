"""Lógica de autenticación: verificar credenciales y dar de alta usuarios."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.schemas import RegisterRequest
from shared.auth import ROLES_VALIDOS, hashear_password, verificar_password
from shared.models.usuario import Usuario


def autenticar(db: Session, email: str, password: str) -> Usuario:
    """Verifica email + password. Devuelve el Usuario o lanza 401."""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    # Verificamos el hash aunque el usuario no exista para no filtrar por tiempo
    # si un email está registrado (defensa básica contra enumeración).
    hash_ref = usuario.password_hash if usuario else "$2b$12$" + "x" * 53
    ok = verificar_password(password, hash_ref)
    if usuario is None or not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def registrar_usuario(db: Session, datos: RegisterRequest) -> Usuario:
    """Crea un usuario nuevo. El rol debe ser válido y el email único."""
    if datos.rol not in ROLES_VALIDOS:
        validos = ", ".join(sorted(ROLES_VALIDOS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rol inválido. Valores aceptados: {validos}.",
        )

    existe = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email.",
        )

    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
