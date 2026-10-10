"""Router — metadatos enriquecidos según el tipo de instrumento.

Prefijo /api/enrichment (el api-gateway lo reenvía tal cual).

  GET /api/enrichment/campos/{tipo}       definición de campos del tipo
  GET /api/enrichment/{id}/propuesta      metadatos del tipo propuestos (o aprobados)
  GET /api/enrichment/{id}                metadatos del tipo aprobados

La aprobación es conjunta con el Dublin Core: POST /api/metadata/{id}/aprobar.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from dependencies import DBSession, Investigador
from models import CampoOut, PropuestaResponse
from services import aprobacion
from services.campos import NOMBRE_TABLA_POR_TIPO, campos_de, obligatorios
from services.enrichment_engine import EnrichmentEngine

router = APIRouter(prefix="/api/enrichment", tags=["metadatos-enriquecidos"])


@router.get("/campos/{tipo}", response_model=list[CampoOut], summary="Campos de metadatos de un tipo")
def campos(tipo: str, _: Investigador) -> list[CampoOut]:
    try:
        return [CampoOut(**c.a_dict()) for c in campos_de(tipo)]
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get(
    "/{id_crudo}/propuesta",
    response_model=PropuestaResponse,
    summary="Metadatos del tipo propuestos para el instrumento",
    description=(
        "Completa los metadatos faltantes según el tipo (encuesta, entrevista o prueba "
        "estandarizada) a partir del contenido del archivo y, opcionalmente, del LLM local."
    ),
)
def propuesta(
    id_crudo: int, usuario: Investigador, db: DBSession, usar_llm: bool | None = None
) -> PropuestaResponse:
    return PropuestaResponse(**aprobacion.propuesta(db, usuario, id_crudo, "enriquecidos", usar_llm))


@router.get("/{id_crudo}", response_model=PropuestaResponse, summary="Metadatos del tipo aprobados")
def obtener(id_crudo: int, usuario: Investigador, db: DBSession) -> PropuestaResponse:
    ctx = aprobacion.cargar_contexto(db, usuario, id_crudo, exigir_dueno=False)
    valores = EnrichmentEngine.obtener(db, ctx.tipo, id_crudo)
    if valores is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El instrumento no tiene metadatos del tipo registrados.")
    campos_tipo = campos_de(ctx.tipo)
    return PropuestaResponse(
        id_crudo=id_crudo,
        id_instrumento=ctx.procesado.id_instrumento,
        tipo_instrumento=ctx.tipo,
        tabla=NOMBRE_TABLA_POR_TIPO[ctx.tipo],
        aprobado=ctx.aprobado,
        fecha_aprobado=ctx.procesado.fecha_aprobado,
        valores=valores,
        origen={k: "aprobado" for k in valores},
        obligatorios=obligatorios(campos_tipo),
        campos=[CampoOut(**c.a_dict()) for c in campos_tipo],
    )
