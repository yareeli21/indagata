"""Schemas Pydantic: prompts.

Refleja 1:1 la tabla `tt_rag.prompts` de 01_schema.sql.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptBase(BaseModel):
    tipo: str
    version: str
    contenido: str
    coleccion_id: int | None = None
    activo: bool = True


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    tipo: str | None = None
    version: str | None = None
    contenido: str | None = None
    coleccion_id: int | None = None
    activo: bool | None = None


class PromptRead(PromptBase):
    model_config = ConfigDict(from_attributes=True)

    prompt_id: int
    creado_en: datetime | None = None
