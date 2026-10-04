"""
Documents Router - CRUD Endpoints

Endpoints para crear, leer, actualizar y eliminar documentos raw
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Annotated, List
import logging

# Local imports
from shared.db import get_db
from models import RawDocument, AgregarDocumento, ActualizarNombreDocumento
from services.document_service import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documentos")

# Dependency
db_dependency = Annotated[Session, Depends(get_db)]

# ═══════════════════════════════════════════════════════════════
# CREATE (POST)
# ═══════════════════════════════════════════════════════════════

@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_documento(documento: AgregarDocumento, db: db_dependency):
    """
    Crear y almacenar un nuevo documento raw
    
    - **nombre_documento**: Nombre único del documento
    - **tipo_de_instrumento**: encuesta | entrevista | prueba_estandarizada
    - **id_propietario**: ID del usuario propietario
    - **ruta**: Ruta de almacenamiento del archivo
    
    Returns: Documento creado con su ID
    """
    try:
        return DocumentService.create(db, documento)
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document"
        )

# ═══════════════════════════════════════════════════════════════
# READ (GET)
# ═══════════════════════════════════════════════════════════════

@router.get("/")
async def listar_documentos(
    skip: int = Query(0, ge=0, description="Saltar N registros (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Máximo de resultados"),
    db: db_dependency = None
):
    """
    Listar todos los documentos (con paginación)
    
    - **skip**: Número de registros a saltar (para paginación)
    - **limit**: Máximo de registros a devolver (máximo 100)
    
    Returns: Lista de documentos con total count
    """
    try:
        return DocumentService.list_all(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )

@router.get("/{id_documento}")
async def obtener_documento(id_documento: int, db: db_dependency):
    """
    Obtener un documento específico por ID
    
    - **id_documento**: ID del documento
    
    Returns: Documento con todos sus detalles
    """
    try:
        documento = DocumentService.get_by_id(db, id_documento)
        if not documento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {id_documento} no encontrado"
            )
        return documento
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )

@router.get("/owner/{id_propietario}")
async def listar_documentos_usuario(
    id_propietario: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: db_dependency = None
):
    """
    Obtener todos los documentos de un usuario específico
    
    - **id_propietario**: ID del propietario/usuario
    - **skip**: Para paginación
    - **limit**: Para paginación
    
    Returns: Lista de documentos del usuario
    """
    try:
        return DocumentService.get_by_owner(db, id_propietario, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error getting user documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user documents"
        )

@router.get("/type/{tipo}")
async def listar_documentos_por_tipo(
    tipo: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: db_dependency = None
):
    """
    Obtener documentos por tipo
    
    - **tipo**: encuesta | entrevista | prueba_estandarizada
    
    Returns: Lista de documentos del tipo especificado
    """
    try:
        return DocumentService.get_by_type(db, tipo, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error getting documents by type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get documents by type"
        )

# ═══════════════════════════════════════════════════════════════
# UPDATE (PUT)
# ═══════════════════════════════════════════════════════════════

@router.put("/{id_documento}")
async def actualizar_documento(
    id_documento: int,
    documento: ActualizarNombreDocumento,
    db: db_dependency
):
    """
    Actualizar nombre de un documento
    
    - **id_documento**: ID del documento a actualizar
    - **nombre_documento**: Nuevo nombre
    
    Returns: Documento actualizado
    """
    try:
        documento_actualizado = DocumentService.update(db, id_documento, documento)
        if not documento_actualizado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {id_documento} no encontrado"
            )
        return documento_actualizado
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )

# ═══════════════════════════════════════════════════════════════
# DELETE (DELETE)
# ═══════════════════════════════════════════════════════════════

@router.delete("/{id_documento}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_documento(id_documento: int, db: db_dependency):
    """
    Eliminar un documento
    
    - **id_documento**: ID del documento a eliminar
    
    Returns: 204 No Content si fue exitoso
    """
    try:
        success = DocumentService.delete(db, id_documento)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {id_documento} no encontrado"
            )
        return None
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

# ═══════════════════════════════════════════════════════════════
# STATS (GET)
# ═══════════════════════════════════════════════════════════════

@router.get("/stats/total")
async def obtener_estadisticas(db: db_dependency):
    """
    Obtener estadísticas de documentos almacenados
    
    Returns: Conteos por tipo de instrumento
    """
    try:
        return DocumentService.get_stats(db)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
