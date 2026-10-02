from sqlalchemy.orm import Session
from app.models.kpi import KPI
from app.schemas.kpi import KPICreate, KPIUpdate

class KPIRepository:
    def get_all_active(self, db: Session) -> list[KPI]:
        """Recupera el catálogo completo de KPIs activos para la inferencia del LLM."""
        return db.query(KPI).filter(KPI.activo == True).all()

    def create(self, db: Session, obj_in: KPICreate) -> KPI:
        db_obj = KPI(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, id_kpi: int, obj_in: KPIUpdate) -> KPI | None:
        """Permite editar o desactivar KPIs obsoletos (CU-06)."""
        db_obj = db.query(KPI).filter(KPI.id_kpi == id_kpi).first()
        if not db_obj:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

kpi_repo = KPIRepository()