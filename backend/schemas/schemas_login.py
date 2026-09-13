from datetime import datetime
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional 
from datetime import date, time

#validaciones de entrada y salida

class LoginBase(BaseModel):
    usuario: str= Field(..., alias="Usuario")
    correo: EmailStr= Field(..., alias="Correo")


class LoginCreate(LoginBase):

   password:str = Field(...,alias="Contraseña")

class LoginUpdate(LoginBase):
    usuario:Optional[str] = Field(None, alias="Usuario")
    correo: Optional[EmailStr] = Field(None, alias="Correo")
    password: Optional[str] = Field(None, alias="Contraseña")



class LoginResponse(LoginBase):

    id: str = Field(...,alias="ID")
    fecha:datetime = Field(..., alias="Fecha de Creación")


    class Config:
        orm_mode = True
        from_atributes = True
        allow_population_by_field_name = True
        populate_by_name = True