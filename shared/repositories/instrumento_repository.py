#verificar hashes para evitar duplicados y eliminar registros

from sqlalchemy.orm import Session
from app.models.instrumento import InstrumentoProcesado
from app.schemas.instrumento import InstrumentoCreate, InstrumentoUpdate

class InstrumentoRepository:
    
    def get_by_id(self, db: Session, id_instrumento: int) -> InstrumentoProcesado | None:
        """Obtiene un instrumento por su ID."""
        return db.query(InstrumentoProcesado).filter(InstrumentoProcesado.id_instrumento == id_instrumento).first()

    def get_by_hash(self, db: Session, hash_md5: str) -> InstrumentoProcesado | None:
        """Busca si el archivo ya fue subido para evitar duplicados (Regla RN_05)."""
        return db.query(InstrumentoProcesado).filter(InstrumentoProcesado.hash_md5 == hash_md5).first()

    def create(self, db: Session, obj_in: InstrumentoCreate) -> InstrumentoProcesado:
        """Crea un nuevo registro en instrumento_procesado."""
        db_obj = InstrumentoProcesado(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: InstrumentoProcesado, obj_in: InstrumentoUpdate) -> InstrumentoProcesado:
        """Actualiza campos específicos, como cambiar el estado a 'estandarizado'."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id_instrumento: int) -> bool:
        """Elimina el registro de la BD (Parte del flujo de eliminación en cascada CU-09)."""
        db_obj = self.get_by_id(db, id_instrumento)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

# Instancia global para ser usada en los endpoints de FastAPI
instrumento_repo = InstrumentoRepository()