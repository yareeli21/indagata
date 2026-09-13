# app/services/login_service.py
"""
Lógica de negocio para autenticación de usuarios.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPExeptionn
from models.models_login import Usuario
from schemas.schemas_login import LoginCreate
from core.security import hashear_password, verificar_password

class UserService:
    @staticmethod
    def create_new_user(db:Session, user_in: LoginCreate):
        
        existing_user =db.query(Usuario).filter(Usuario.correo == user_in.correo).first()

        if existing_user: 
            raise HTTPExeptionn(
                status_code=status.HTT
            )






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