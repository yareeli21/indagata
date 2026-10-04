"""DTOs del RAG: indexado y chat (diseño §4.6, §4.7, §4.11).

Todos los literales de `tipo` espejan `TipoInstrumento` del frontend (§2.4). El
`top_k` del chat se NORMALIZA (clamp) al rango [1, 20] en vez de rechazarse.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

TipoInstrumento = Literal["Encuesta", "Entrevista", "Prueba estandarizada"]


# ── Indexado ──────────────────────────────────────────────────────────────────
class IndexRequest(BaseModel):
    investigacionId: str = Field(min_length=1)
    instrumentoIds: list[str] = Field(min_length=1)
    reindexar: bool = False

    @field_validator("investigacionId")
    @classmethod
    def _investigacion_no_vacia(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("investigacionId no puede estar vacío.")
        return v


class IndexInstrumentoResultado(BaseModel):
    instrumentoId: str
    chunks: int
    estado: Literal["indexado", "omitido"]
    motivo: str | None = None


class IndexResponse(BaseModel):
    coleccion: str
    total_chunks: int
    instrumentos: list[IndexInstrumentoResultado]
    mensaje: str


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    investigacionId: str = Field(min_length=1)
    pregunta: str = Field(min_length=1, max_length=4000)
    instrumentoIds: list[str] | None = None
    modelo: str | None = None
    stream: bool = True
    top_k: int = 5

    @field_validator("investigacionId")
    @classmethod
    def _investigacion_no_vacia(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("investigacionId no puede estar vacío.")
        return v

    @field_validator("top_k")
    @classmethod
    def _clamp_top_k(cls, v: int) -> int:
        """Normaliza (NO rechaza) al rango [1, 20] (§4.7)."""
        return max(1, min(20, v))


class FuenteChatOut(BaseModel):
    instrumentoId: str
    titulo: str
    tipo: TipoInstrumento
    investigador: str
    kpis: list[str]
    fragmento: str


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[FuenteChatOut]
    modelo: str
    degradado: bool = False
