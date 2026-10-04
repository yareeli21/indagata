from sqlmodel import SQLModel, Field, Column 
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SAEnum





#hay classes para la tabla y para lo que entra y sale de la API, los modelos con table = true son para la tabla,
#los que no son para los requests
#la validacion solo ocurre en los que no tienen table=True

""" TABLAS DE CON INFORMACION PUBLICA PARA NO EXPONER TODA LA INFO 
"""

class RawDocumentBase(SQLModel):

    nombre_documento: str = Field(index=True, unique=True)
    # Using timezone-aware datetimes is recommended for PostgreSQL
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TipoInstrumento(str, Enum):
    entrevista = "entrevista"
    prueba_estandarizada = "prueba_estandarizada"
    encuesta = "encuesta"



#. Setting __tablename__ allows your Python class to map exactly to that existing table name.


class RawDocument(RawDocumentBase, table=True):

    __tablename__="raw_data"
    
    # Optional and default=None allows PostgreSQL to auto-increment (SERIAL) unique true se elmimino por que era redundante pq postgres ya lo hace solito
    id_documento: Optional[int] = Field(default=None, primary_key=True)
    tipo_de_instrumento: TipoInstrumento = Field(
        sa_column=Column(
            SAEnum(
                TipoInstrumento,
                # native_enum=True leverages PostgreSQL's native ENUM type
                native_enum=True,
                values_callable=lambda e: [m.value for m in e],
                length=30,
            ),
            nullable=False,
            index=True,
        )
    )
    id_propietario: int = Field(foreign_key="Usuarios.id")
    ruta: str = Field(nullable=False, unique=True)

class InstrumentoProcesado(SQLModel):

    __tablename__ = "instrumento_procesado"
    id_crudo: int = Field(primary_key=True, foreign_key="raw_data.id_documento")

#Actions

class AgregarDocumento(RawDocumentBase):
    tipo_de_instrumento: TipoInstrumento
    id_propietario: int 

class ActualizarNombreDocumento(RawDocumentBase):
    nombre_documento: str


