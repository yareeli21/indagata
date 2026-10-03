"""
Dublin Core Manager - Core Business Logic

Handles all CRUD operations for Dublin Core metadata:
- Registration (6 auto-filled + 7 user-provided fields)
- Retrieval
- Validation
- Immutability enforcement
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from pathlib import Path
import logging
import json
import os

logger = logging.getLogger(__name__)


class DCManager:
    """Business logic for Dublin Core metadata management"""
    
    @staticmethod
    def get_initial_data(db: Session, instrumento_id: int) -> dict:
        """
        Get pre-populated data for metadata registration form.
        
        Returns auto-filled values (read-only on frontend):
        - dc_creator: from authenticated user
        - dc_publisher: from APP_NAME config
        - dc_type: from instrument type
        - dc_format: from file extension
        - dc_date: today
        - dc_language: "es"
        - dc_title: suggested from instrument name
        """
        from shared.models.instrumento_procesado import InstrumentoProcesado
        
        # Get instrument
        instrumento = db.query(InstrumentoProcesado).filter(
            InstrumentoProcesado.instrumento_id == instrumento_id
        ).first()
        
        if not instrumento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {instrumento_id} not found"
            )
        
        # Get user (TODO: from authentication context)
        # For now, use a placeholder
        usuario_nombre = "Sistema"  # Would come from auth context
        
        # Get config
        app_name = os.getenv("APP_NAME", "Indagata")
        
        # Get file extension
        file_format = "unknown"
        if instrumento.ruta_archivo:
            try:
                file_format = Path(instrumento.ruta_archivo).suffix.lstrip(".")
            except:
                pass
        
        return {
            "instrumento_id": instrumento_id,
            "dc_creator": usuario_nombre,
            "dc_publisher": app_name,
            "dc_type": instrumento.tipo_instrumento,
            "dc_format": file_format,
            "dc_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "dc_language": "es",
            "dc_title_sugerido": instrumento.nombre or instrumento.archivo_nombre or "Sin título",
        }
    
    @staticmethod
    def register_dc(db: Session, instrumento_id: int, request: dict) -> dict:
        """
        Register Dublin Core metadata for an instrument.
        
        IMMUTABLE: Second registration returns 409 Conflict.
        
        Auto-filled fields (6):
        - dc_creator, dc_publisher, dc_type, dc_format, dc_date, dc_language
        
        User input (7):
        - dc_title, dc_subject, dc_description, dc_coverage, dc_rights, dc_source, dc_relation
        """
        from shared.models.instrumento_procesado import InstrumentoProcesado
        from shared.models.metadatos_dc import MetadatosDC
        
        # 1. Get instrument
        instrumento = db.query(InstrumentoProcesado).filter(
            InstrumentoProcesado.instrumento_id == instrumento_id
        ).first()
        
        if not instrumento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {instrumento_id} not found"
            )
        
        # 2. Check if metadata already exists (immutability)
        existing = db.query(MetadatosDC).filter(
            MetadatosDC.instrumento_id == instrumento_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Metadata already registered for this instrument. Registration is immutable."
            )
        
        # 3. Get auto-filled values
        app_name = os.getenv("APP_NAME", "Indagata")
        usuario_nombre = request.get("dc_creator", "Sistema")
        
        file_format = "unknown"
        if instrumento.ruta_archivo:
            try:
                file_format = Path(instrumento.ruta_archivo).suffix.lstrip(".")
            except:
                pass
        
        # 4. Create metadata record
        metadatos = MetadatosDC(
            instrumento_id=instrumento_id,
            dc_title=request.get("dc_title"),
            dc_creator=usuario_nombre,
            dc_subject=json.dumps(request.get("dc_subject", []), ensure_ascii=False),
            dc_description=request.get("dc_description"),
            dc_publisher=app_name,
            dc_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            dc_type=instrumento.tipo_instrumento,
            dc_format=file_format,
            dc_language="es",
            dc_coverage=request.get("dc_coverage"),
            dc_rights=request.get("dc_rights"),
            dc_source=request.get("dc_source"),
            dc_relation=request.get("dc_relation"),
        )
        
        db.add(metadatos)
        
        # 5. Update instrument state
        instrumento.estado = "metadata_registrado"
        instrumento.nombre = request.get("dc_title", instrumento.nombre)
        instrumento.fecha_procesamiento = datetime.now(timezone.utc)
        
        db.add(instrumento)
        db.commit()
        db.refresh(metadatos)
        
        logger.info(f"✅ Metadata registered for instrument {instrumento_id}")
        
        # 6. Return complete response
        return {
            "instrumento_id": instrumento_id,
            "estado": "metadata_registrado",
            "dc_title": metadatos.dc_title,
            "dc_creator": metadatos.dc_creator,
            "dc_subject": json.loads(metadatos.dc_subject),
            "dc_description": metadatos.dc_description,
            "dc_publisher": metadatos.dc_publisher,
            "dc_date": metadatos.dc_date,
            "dc_type": metadatos.dc_type,
            "dc_format": metadatos.dc_format,
            "dc_language": metadatos.dc_language,
            "dc_coverage": metadatos.dc_coverage,
            "dc_rights": metadatos.dc_rights,
            "dc_source": metadatos.dc_source,
            "dc_relation": metadatos.dc_relation,
            "mensaje": "✅ Metadata registered successfully. Ready for analysis."
        }
    
    @staticmethod
    def get_dc(db: Session, instrumento_id: int) -> dict:
        """Retrieve Dublin Core metadata"""
        from shared.models.metadatos_dc import MetadatosDC
        
        metadatos = db.query(MetadatosDC).filter(
            MetadatosDC.instrumento_id == instrumento_id
        ).first()
        
        if not metadatos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata not found for instrument {instrumento_id}"
            )
        
        return {
            "instrumento_id": instrumento_id,
            "dc_title": metadatos.dc_title,
            "dc_creator": metadatos.dc_creator,
            "dc_subject": json.loads(metadatos.dc_subject) if metadatos.dc_subject else [],
            "dc_description": metadatos.dc_description,
            "dc_publisher": metadatos.dc_publisher,
            "dc_date": metadatos.dc_date,
            "dc_type": metadatos.dc_type,
            "dc_format": metadatos.dc_format,
            "dc_language": metadatos.dc_language,
            "dc_coverage": metadatos.dc_coverage,
            "dc_rights": metadatos.dc_rights,
            "dc_source": metadatos.dc_source,
            "dc_relation": metadatos.dc_relation,
        }
    
    @staticmethod
    def list_dc(db: Session, skip: int = 0, limit: int = 20) -> dict:
        """List all metadata with pagination"""
        from shared.models.metadatos_dc import MetadatosDC
        
        total = db.query(MetadatosDC).count()
        metadatos_list = db.query(MetadatosDC).offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "metadatos": [
                {
                    "instrumento_id": m.instrumento_id,
                    "dc_title": m.dc_title,
                    "dc_creator": m.dc_creator,
                    "dc_type": m.dc_type,
                    "dc_date": m.dc_date,
                }
                for m in metadatos_list
            ]
        }
    
    @staticmethod
    def delete_dc(db: Session, instrumento_id: int) -> None:
        """Delete metadata (for cleanup/re-registration)"""
        from shared.models.metadatos_dc import MetadatosDC
        
        metadatos = db.query(MetadatosDC).filter(
            MetadatosDC.instrumento_id == instrumento_id
        ).first()
        
        if not metadatos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata not found for instrument {instrumento_id}"
            )
        
        db.delete(metadatos)
        db.commit()
        
        logger.info(f"✅ Metadata deleted for instrument {instrumento_id}")
