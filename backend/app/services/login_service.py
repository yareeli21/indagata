# app/services/login_service.py
"""
Lógica de negocio para autenticación de usuarios.
"""
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.core.security import verificar_password


def autenticar_usuario(db: Session, usuario: str, password: str) -> Usuario | None:
    """
    Busca al usuario por nombre y verifica su contraseña.
    Regresa el objeto Usuario si las credenciales son correctas, o None si no.
    """
    fila = db.query(Usuario).filter(Usuario.usuario == usuario).first()

    if not fila:
        return None

    if not verificar_password(password, fila.password_hash):
        return None

    return fila