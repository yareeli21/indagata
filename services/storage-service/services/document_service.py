"""
Document Service - Business Logic

Contiene toda la lógica para manejar documentos:
- Crear
- Leer
- Actualizar
- Eliminar
- Consultas especiales
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
from typing import Optional, List, Dict, Any

# Local imports
from models import RawDocument, AgregarDocumento, ActualizarNombreDocumento, TipoInstrumento

logger = logging.getLogger(__name__)

class DocumentService:
    """Servicio para operaciones CRUD de documentos"""
    
    # ═══════════════════════════════════════════════════════════
    # CREATE
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def create(db: Session, documento: AgregarDocumento) -> RawDocument:
        """
        Crear un nuevo documento
        
        Args:
            db: Sesión de base de datos
            documento: Datos del documento a crear
            
        Returns:
            Documento creado con su ID
        """
        db_documento = RawDocument(
            nombre_documento=documento.nombre_documento,
            tipo_de_instrumento=documento.tipo_de_instrumento,
            id_propietario=documento.id_propietario,
            ruta=documento.ruta
        )
        db.add(db_documento)
        db.commit()
        db.refresh(db_documento)
        
        logger.info(f"✅ Documento creado: {db_documento.id_documento}")
        return db_documento
    
    # ═══════════════════════════════════════════════════════════
    # READ
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def get_by_id(db: Session, id_documento: int) -> Optional[RawDocument]:
        """Obtener documento por ID"""
        return db.query(RawDocument).filter(
            RawDocument.id_documento == id_documento
        ).first()
    
    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Listar todos los documentos con paginación"""
        total = db.query(RawDocument).count()
        documentos = db.query(RawDocument).offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "documentos": documentos
        }
    
    @staticmethod
    def get_by_owner(db: Session, id_propietario: int, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Obtener documentos de un usuario específico"""
        total = db.query(RawDocument).filter(
            RawDocument.id_propietario == id_propietario
        ).count()
        
        documentos = db.query(RawDocument).filter(
            RawDocument.id_propietario == id_propietario
        ).offset(skip).limit(limit).all()
        
        return {
            "id_propietario": id_propietario,
            "total": total,
            "skip": skip,
            "limit": limit,
            "documentos": documentos
        }
    
    @staticmethod
    def get_by_type(db: Session, tipo: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Obtener documentos por tipo"""
        total = db.query(RawDocument).filter(
            RawDocument.tipo_de_instrumento == tipo
        ).count()
        
        documentos = db.query(RawDocument).filter(
            RawDocument.tipo_de_instrumento == tipo
        ).offset(skip).limit(limit).all()
        
        return {
            "tipo": tipo,
            "total": total,
            "skip": skip,
            "limit": limit,
            "documentos": documentos
        }
    
    # ═══════════════════════════════════════════════════════════
    # UPDATE
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def update(db: Session, id_documento: int, documento: ActualizarNombreDocumento) -> Optional[RawDocument]:
        """Actualizar nombre de un documento"""
        db_documento = db.query(RawDocument).filter(
            RawDocument.id_documento == id_documento
        ).first()
        
        if not db_documento:
            return None
        
        db_documento.nombre_documento = documento.nombre_documento
        db.add(db_documento)
        db.commit()
        db.refresh(db_documento)
        
        logger.info(f"✅ Documento actualizado: {id_documento}")
        return db_documento
    
    # ═══════════════════════════════════════════════════════════
    # DELETE
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def delete(db: Session, id_documento: int) -> bool:
        """Eliminar un documento"""
        db_documento = db.query(RawDocument).filter(
            RawDocument.id_documento == id_documento
        ).first()
        
        if not db_documento:
            return False
        
        db.delete(db_documento)
        db.commit()
        
        logger.info(f"✅ Documento eliminado: {id_documento}")
        return True
    
    # ═══════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        """Obtener estadísticas de documentos"""
        total = db.query(RawDocument).count()
        
        # Contar por tipo
        stats_por_tipo = db.query(
            RawDocument.tipo_de_instrumento,
            func.count(RawDocument.id_documento).label('count')
        ).group_by(RawDocument.tipo_de_instrumento).all()
        
        # Contar por propietario
        stats_por_propietario = db.query(
            RawDocument.id_propietario,
            func.count(RawDocument.id_documento).label('count')
        ).group_by(RawDocument.id_propietario).all()
        
        return {
            "total_documentos": total,
            "por_tipo": {str(tipo): count for tipo, count in stats_por_tipo},
            "por_propietario": {str(prop_id): count for prop_id, count in stats_por_propietario}
        }
