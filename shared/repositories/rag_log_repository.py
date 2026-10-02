from sqlalchemy.orm import Session
from app.models.rag_log import RagLog
from app.schemas.rag_log import RagLogCreate

class RagLogRepository:
    def create(self, db: Session, obj_in: RagLogCreate) -> RagLog:
        """Registra la consulta, los chunks recuperados, respuesta y latencia para auditoría y MLLMOps (CU-05)."""
        db_obj = RagLog(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_chat_history(self, db: Session, limit: int = 50, offset: int = 0) -> list[RagLog]:
        """Recupera el historial de consultas para la interfaz del usuario."""
        return db.query(RagLog).order_by(RagLog.fecha.desc()).offset(offset).limit(limit).all()

rag_log_repo = RagLogRepository()