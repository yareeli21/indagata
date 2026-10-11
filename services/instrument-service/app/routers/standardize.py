"""Router — ESTANDARIZACIÓN de instrumentos (diseño §1.6).

  POST /instrumentos/{id}/estandarizar/preview  -> PreviewResponse (no persiste)
  POST /instrumentos/{id}/estandarizar          -> EstandarizarResponse

Ambos exigen `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` (igual que
upload/list). `{id}` = id_crudo (id canónico del frontend). Se exponen por el
passthrough del gateway (`/instrumentos/*`).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import DBSession, require_rol
from app.schemas.estandarizacion import (
    EstandarizarRequest,
    EstandarizarResponse,
    PreviewResponse,
)
from app.services import standardization_service
from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR
from shared.models.usuario import Usuario

router = APIRouter(prefix="/instrumentos", tags=["estandarizacion-instrumentos"])

UsuarioQuePuedeEstandarizar = Annotated[
    Usuario, Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))
]


@router.post(
    "/{id}/estandarizar/preview",
    response_model=PreviewResponse,
    summary="Previsualizar los tipos de pregunta detectados (no persiste)",
)
def previsualizar_estandarizacion(
    usuario_actual: UsuarioQuePuedeEstandarizar,
    db: DBSession,
    id: int,
) -> PreviewResponse:
    return standardization_service.preview(db, id)


@router.post(
    "/{id}/estandarizar",
    response_model=EstandarizarResponse,
    summary="Estandarizar con los tipos confirmados (persiste el JSON de dominio)",
)
def estandarizar_instrumento(
    usuario_actual: UsuarioQuePuedeEstandarizar,
    db: DBSession,
    id: int,
    payload: EstandarizarRequest,
) -> EstandarizarResponse:
    return standardization_service.estandarizar(db, id, payload.preguntas)
