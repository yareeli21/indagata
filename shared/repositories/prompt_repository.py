from sqlalchemy.orm import Session
from app.models.prompt import Prompt
from app.schemas.prompt import PromptCreate

class PromptRepository:
    def get_active_by_type(self, db: Session, tipo: str) -> Prompt | None:
        """Obtiene el prompt activo requerido para la vectorización (RN_11)."""
        return db.query(Prompt).filter(Prompt.tipo == tipo, Prompt.activo == True).first()

    def create_new_version(self, db: Session, obj_in: PromptCreate) -> Prompt:
        """Añade un prompt nuevo. Si es una actualización, el admin debe generar una versión nueva (CU-07)."""
        db_obj = Prompt(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

prompt_repo = PromptRepository()