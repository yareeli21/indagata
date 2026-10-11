"""
Metadatos específicos por tipo (Bug 2) — Endpoint.

Expone el UPSERT de metadatos específicos del tipo de instrumento (paso 4 del
wizard). Ruta final (tras montarse con prefix='/api' en main.py):

    POST /api/metadata/{instrumento_id}/especificos

El router usa prefix='/metadata' (igual que routers/metadata.py), SIN segundo
'/metadata' en la ruta, para distinguirse de los endpoints DC
(`/api/metadata/metadata/{id}`). Ver design.md §6.1.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metadata", tags=["metadata-especificos"])

# Import shared dependencies
from shared.db.database import get_db

# Import business logic
from services.specific_manager import SpecificMetadataManager


@router.post("/{instrumento_id}/especificos")
async def registrar_metadatos_especificos(
    instrumento_id: int,
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Registra (UPSERT) los metadatos específicos por tipo de un instrumento.

    Body: { "tipo": "encuesta|entrevista|prueba_estandarizada", "campos": {...} }

    - `tipo` se valida contra `raw_data.tipo_instrumento` (409 si no coincide).
    - `campos` contiene las claves de la tabla del tipo; solo se persisten las
      presentes/no vacías (las ausentes quedan NULL).
    - A diferencia de Dublin Core, es EDITABLE: segunda llamada actualiza la fila.

    Returns: { instrumento_id, tipo, campos (persistidos), mensaje }
    """
    tipo = request.get("tipo")
    campos = request.get("campos", {})

    if not tipo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falta el campo 'tipo'.",
        )

    try:
        response = SpecificMetadataManager.upsert(db, instrumento_id, tipo, campos)
        logger.info(
            "✅ Metadatos específicos registrados para instrumento %s",
            instrumento_id,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Error registrando metadatos específicos: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudieron registrar los metadatos específicos.",
        )
