# app/schemas/metadatos.py
"""
Esquema de metadatos Nivel 1 (globales, Dublin Core adaptado)
para instrumentos: encuestas, entrevistas, pruebas estandarizadas.
"""
from pydantic import BaseModel, Field


class MetadatosBase(BaseModel):
    # obligatorios
    titulo: str
    institucion_responsable: str
    objetivo: str
    tipo_instrumento: str  # reutilizado del formulario de carga
    periodo_inicio: str    # formato "YYYY-MM-DD"
    periodo_fin: str
    idioma: str = "es"
    poblacion_alcance: str

    # opcionales
    palabras_clave: list[str] = Field(default_factory=list)
    institucion_publica: str | None = None
    condiciones_uso: str | None = None
    formato_archivo: str | None = None       # automático, no editable
    plataforma_origen: str | None = None      # editorial por ahora
    instrumentos_relacionados: list[str] = Field(default_factory=list)


class MetadatosCompletos(BaseModel):
    """Estructura final que se guarda en la columna JSONB `metadatos`."""
    base: MetadatosBase
    enriquecidos: dict = Field(default_factory=dict)  # Nivel 2, se llena después