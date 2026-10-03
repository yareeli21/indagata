"""Router — VECTORIZACIÓN e inferencia de KPIs.

Flujo de dos pasos (requiere decisión humana entre ambos):

  POST /vectorizacion/propuestas   → Paso 1: recibe el JSON + instrumento original
                                     (.md adjunto), vectoriza lo clave y propone
                                     los KPIs más cercanos con su score.
  POST /vectorizacion/confirmar    → Paso 2: recibe las decisiones + el JSON, persiste
                                     los KPIs aceptados y devuelve el JSON enriquecido.

Mantenimiento:
  POST /vectorizacion/kpis/reindex → (re)vectoriza la colección `kpis` desde la BD.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from app.vectorization.core.kpi_indexer import reindex_kpis
from app.vectorization.dependencies import DBSession, UsuarioActual
from app.vectorization.schemas.vectorizacion import (
    ConfirmarRequest,
    ConfirmarResponse,
    PropuestasResponse,
    ReindexResponse,
    SummaryEmbeddingResponse,
)
from app.vectorization.services.enrichment_service import EnrichmentService
from app.vectorization.services.inspection_service import InspectionService
from app.vectorization.services.proposal_service import ProposalService

router = APIRouter(prefix="/vectorizacion", tags=["vectorizacion-kpis"])

# Codificaciones a intentar al leer el instrumento original (.md/.txt).
_MD_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _decode_md(data: bytes) -> str:
    for enc in _MD_ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


@router.post(
    "/propuestas",
    response_model=PropuestasResponse,
    status_code=status.HTTP_200_OK,
    summary="Paso 1 — Proponer KPIs por similitud semántica",
    description=(
        "Recibe el **JSON** del instrumento (metadatos + respuestas) y el **instrumento "
        "original** (archivo `.md`/`.txt` adjunto, solo preguntas). Extrae los metadatos "
        "clave según el tipo, construye un *summary* (metadatos + instrumento original, "
        "sin respuestas), lo vectoriza en la colección `summary_instrument` y busca en la "
        "colección `kpis` los más cercanos. Devuelve las propuestas con su score para que "
        "el usuario las acepte o rechace. No modifica el JSON."
    ),
)
async def proponer_kpis(
    usuario_actual: UsuarioActual,
    archivo_json: UploadFile = File(..., description="JSON del instrumento (metadatos + respuestas)."),
    instrumento_original: UploadFile = File(..., description="Instrumento original (.md/.txt, solo preguntas)."),
    tipo_instrumento: str = Form(..., description="encuesta | entrevista | prueba_estandarizada"),
    id_instrumento: int = Form(..., description="PK de instrumento_procesado."),
) -> PropuestasResponse:
    json_bytes = await archivo_json.read()
    md_bytes = await instrumento_original.read()
    texto_original = _decode_md(md_bytes)

    respuesta, _ = ProposalService.propose(
        id_instrumento=id_instrumento,
        tipo_instrumento_raw=tipo_instrumento,
        json_bytes=json_bytes,
        instrumento_original=texto_original,
    )
    return respuesta


@router.post(
    "/confirmar",
    response_model=ConfirmarResponse,
    status_code=status.HTTP_200_OK,
    summary="Paso 2 — Confirmar KPIs y enriquecer el JSON",
    description=(
        "Recibe las **decisiones** del usuario (acepta/rechaza por KPI) y el **JSON** "
        "del instrumento. Persiste los KPIs aceptados en `kpi_inferido` (con evidencia "
        "en `kpi_inferido_chunk` y su score) y devuelve el **JSON enriquecido** con la "
        "clave `inferred_kpis`."
    ),
)
def confirmar_kpis(
    usuario_actual: UsuarioActual,
    db: DBSession,
    request: ConfirmarRequest,
) -> ConfirmarResponse:
    return EnrichmentService.confirm(db, request)


@router.post(
    "/kpis/reindex",
    response_model=ReindexResponse,
    status_code=status.HTTP_200_OK,
    summary="Mantenimiento — Reindexar la colección de KPIs",
    description=(
        "(Re)vectoriza TODOS los KPIs de la tabla `tt_rag.kpi` en la colección Chroma "
        "`kpis`. Ejecutar al sembrar o actualizar el catálogo de KPIs."
    ),
)
def reindexar_kpis(
    usuario_actual: UsuarioActual,
    db: DBSession,
) -> ReindexResponse:
    resultado = reindex_kpis(db)
    return ReindexResponse(coleccion=resultado.coleccion, n_kpis=resultado.n_kpis)


@router.get(
    "/summary/{id_instrumento}",
    response_model=SummaryEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspección — Ver el embedding del summary de un instrumento",
    description=(
        "Devuelve, de solo lectura, el vector del summary del instrumento guardado en "
        "la colección `summary_instrument`: el **modelo** con el que se generó, su "
        "**dimensión** (p. ej. 768), una muestra de valores, la metadata del punto y un "
        "preview del texto vectorizado. Útil para confirmar qué modelo de embeddings se usó."
    ),
)
def ver_summary_embedding(
    usuario_actual: UsuarioActual,
    db: DBSession,
    id_instrumento: int,
) -> SummaryEmbeddingResponse:
    return InspectionService.get_summary_embedding(db, id_instrumento)
