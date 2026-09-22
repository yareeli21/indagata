# app/services/login_service.py
"""
Lógica de negocio para autenticación de usuarios.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models.models_login import Usuario
from schemas.schemas_login import LoginCreate
from core.security import hashear_password, verificar_password

class UserService:
    @staticmethod
    def create_new_user(db: Session, user_in: LoginCreate):
        existing_user = db.query(Usuario).filter(Usuario.correo == user_in.correo).first()
        
        if existing_user: 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario con este correo ya existe."
            )
        
        # Verificar si el nombre de usuario ya existe
        existing_username = db.query(Usuario).filter(Usuario.usuario == user_in.usuario).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso."
            )
        
        nuevo_usuario = Usuario(
            usuario=user_in.usuario,
            correo=user_in.correo,
            password_hash=hashear_password(user_in.password)
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario

    @staticmethod
    def reset_password(db: Session, correo: str, nueva_password: str):
        usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró un usuario con ese correo."
            )
        
        usuario.password_hash = hashear_password(nueva_password)
        db.commit()
        db.refresh(usuario)
        return usuario


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