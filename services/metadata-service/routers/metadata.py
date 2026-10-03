"""
Dublin Core Metadata CRUD Endpoints

Manages registration and retrieval of 13 Dublin Core metadata fields:
- 6 auto-completed (creator, publisher, type, format, date, language)
- 7 user-provided (title, subject, description, coverage, rights, source, relation)

Immutable: Registration happens once, subsequent attempts return 409 Conflict.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metadata", tags=["metadata"])

# Import shared dependencies
from shared.db.database import get_db
from shared.schemas.responses import DublinCoreMetadata, InstrumentResponse

# Import business logic
from services.dc_manager import DCManager


@router.get("/metadata/{instrumento_id}/init")
async def get_metadata_init(
    instrumento_id: int,
    db: Session = Depends(get_db)
):
    """
    Get pre-populated metadata fields for form initialization.
    
    Returns auto-filled values (6 fields) with title suggestion:
    - dc_creator: authenticated user
    - dc_publisher: app name from config
    - dc_type: instrument type (encuesta/entrevista/prueba_estandarizada)
    - dc_format: file extension
    - dc_date: registration date (today)
    - dc_language: "es"
    - dc_title (editable): suggested from instrument name
    
    Used by frontend to initialize the metadata registration form.
    """
    try:
        initial_data = DCManager.get_initial_data(db, instrumento_id)
        logger.info(f"✅ Metadata init data retrieved for instrument {instrumento_id}")
        return initial_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting metadata init: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metadata initialization data"
        )


@router.post("/metadata/{instrumento_id}", response_model=dict)
async def register_metadata(
    instrumento_id: int,
    request: dict,  # Will be validated by DCManager
    db: Session = Depends(get_db)
):
    """
    Register Dublin Core metadata (Step 2 of upload workflow).
    
    Registers all 13 Dublin Core fields. Six fields are auto-completed,
    and seven fields come from user input.
    
    IMMUTABLE: Calling this endpoint twice returns 409 Conflict.
    You cannot update metadata after registration.
    
    Fields:
    - dc_title: str (required) - Instrument title
    - dc_subject: list[str] (required) - Keywords/topics
    - dc_description: str (optional) - Detailed description
    - dc_coverage: str (optional) - Geographic/temporal coverage
    - dc_rights: str (optional) - Usage rights
    - dc_source: str (optional) - Original source
    - dc_relation: str (optional) - Related instruments
    
    Returns: All 13 fields with instrument state updated to "metadata_registrado"
    """
    try:
        response = DCManager.register_dc(db, instrumento_id, request)
        logger.info(f"✅ Metadata registered for instrument {instrumento_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error registering metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register metadata"
        )


@router.get("/metadata/{instrumento_id}")
async def get_metadata(
    instrumento_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve Dublin Core metadata for an instrument.
    
    Returns all 13 registered Dublin Core fields including:
    - Auto-filled fields (creator, publisher, type, format, date, language)
    - User-provided fields (title, subject, description, coverage, rights, source, relation)
    - Timestamps (created_at, updated_at)
    
    Available in states: metadata_registrado, etl_*, etl_aprobado
    """
    try:
        metadata = DCManager.get_dc(db, instrumento_id)
        logger.info(f"✅ Metadata retrieved for instrument {instrumento_id}")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metadata"
        )


@router.get("/metadata")
async def list_metadata(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all metadata records (with pagination).
    
    Use for admin dashboards or bulk operations.
    """
    try:
        results = DCManager.list_dc(db, skip=skip, limit=limit)
        logger.info(f"✅ Listed metadata ({skip}-{skip+limit})")
        return results
    except Exception as e:
        logger.error(f"❌ Error listing metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list metadata"
        )


@router.delete("/metadata/{instrumento_id}")
async def delete_metadata(
    instrumento_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete metadata for an instrument (admin only, for cleanup).
    
    Allows starting the metadata registration process over if needed.
    Only works if instrument is in 'pendiente' state (not yet analyzed).
    """
    try:
        DCManager.delete_dc(db, instrumento_id)
        logger.info(f"✅ Metadata deleted for instrument {instrumento_id}")
        return {"message": "Metadata deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete metadata"
        )
