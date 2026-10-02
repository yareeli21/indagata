from sqlalchemy.orm import Session
from app.models.documento_vectorizado import DocumentoVectorizado
from app.schemas.documento_vectorizado import DocumentoVectorizadoCreate

class DocumentoVectorizadoRepository:
    def create(self, db: Session, obj_in: DocumentoVectorizadoCreate) -> DocumentoVectorizado:
        """Registra un nuevo chunk generado y su ID de vector en ChromaDB."""
        db_obj = DocumentoVectorizado(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def deactivate_by_instrumento(self, db: Session, id_instrumento: int) -> None:
        """Desactiva lógicamente los chunks en PostgreSQL antes de eliminarlos en ChromaDB (DA-14)."""
        db.query(DocumentoVectorizado).filter(DocumentoVectorizado.id_instrumento == id_instrumento).update({"activo": False})
        db.commit()

documento_vectorizado_repo = DocumentoVectorizadoRepository()