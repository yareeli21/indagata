"""Router — CARGA de instrumentos (Paso 1: subir archivo).

Único endpoint del instrument-service en esta fase:

  POST /instrumentos/upload  → sube el archivo respondido (+ opcional el original),
                               identifica su tipo, lo guarda en RAW DATA y registra
                               el instrumento (raw_data + instrumento_procesado).

Las etapas posteriores (metadatos, limpieza, enriquecimiento, KPIs) viven en
otros módulos/servicios y no forman parte del alcance de la carga.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from app.dependencies import DBSession, UsuarioActual
from app.schemas.upload import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter(prefix="/instrumentos", tags=["carga-instrumentos"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Paso 1 — Subir el instrumento y su archivo original",
    description=(
        "Recibe el archivo RESPONDIDO del instrumento y, opcionalmente, el archivo "
        "ORIGINAL (el instrumento sin respuestas). Identifica el tipo de cada archivo, "
        "lo enruta a su familia de parser y lo **parsea** para conocer con qué estructura "
        "se va a trabajar:\n\n"
        "- **encuesta** → tabular (`.csv`, `.xlsx`, `.xls`): columnas y nº de filas.\n"
        "- **entrevista** / **prueba_estandarizada** → documento (`.pdf`, `.txt`, `.docx`): "
        "texto extraído y métricas.\n\n"
        "Almacena ambos archivos en RAW DATA (`storage/raw`) y registra el instrumento "
        "en `raw_data` (padre) + `instrumento_procesado` (estado `recibido`). "
        "Devuelve `id_crudo`, `id_instrumento` y el resumen del parseo."
    ),
)
async def upload_instrumento(
    usuario_actual: UsuarioActual,
    db: DBSession,
    archivo: UploadFile = File(
        ..., description="Archivo RESPONDIDO del instrumento (con las respuestas)."
    ),
    tipo_instrumento: str = Form(
        ..., description="encuesta | entrevista | prueba_estandarizada"
    ),
    archivo_original: UploadFile | None = File(
        default=None,
        description="Instrumento ORIGINAL sin respuestas (opcional).",
    ),
) -> UploadResponse:
    return await UploadService.upload(
        db=db,
        usuario_id=usuario_actual.usuario_id,
        tipo_instrumento_raw=tipo_instrumento,
        archivo=archivo,
        archivo_original=archivo_original,
    )
