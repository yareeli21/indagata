from sqlalchemy import Text
from sqlmodel import SQLModel, Field, Column 
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SAEnum


class MetadatosDublinCoreBase(SQLModel):

    __tablename__ = "metadatos_dc"    

    id_crudo: int = Field(default=None, primary_key=True,foreign_key="raw_data.id_documento", ondelete="CASCADE" )
    dc_title: str
    dc_creator: str
    dc_description: str
    dc_type: str
    dc_date: str
    dc_language: str
    dc_coverage: str
    dc_subject: str
    dc_publisher: str
    dc_rights: str
    dc_format: str
    dc_source: str
    dc_relation: str



class MetadatosEncuestas(SQLModel):
    __tablename__ = "metadatos_enriquecidos_encuestas"
    id_crudo:int = Field(default=None, primary_key=True,foreign_key="raw_data.id_documento" )
    numero_de_respondentes: int
    numero_de_poblacion: int 
    tipo_de_investigacion:Text
    notas_contextuales: Text
    notas_interpretacion: Text
    secciones: Text

    
class MetadatosEntrevistas(SQLModel):
    __tablename__= "metadatos_enriquecidos entrevistas"
    id_crudo:int = Field(default=None, primary_key=True,foreign_key="raw_data.id_documento" )
    identificador_propio: Mapped[str | None] = mapped_column(Text)
    objetivo: Mapped[str | None] = mapped_column(Text)
    metodologia: Mapped[str | None] = mapped_column(Text)
    institucion: Mapped[str | None] = mapped_column(Text)
    derechos: Mapped[str | None] = mapped_column(Text
