from sqlalchemy.orm import Session
from app.models.pregunta_kpi import PreguntaKPI
from app.schemas.pregunta_kpi import PreguntaKPICreate

class PreguntaKPIRepository:
    def create_bulk(self, db: Session, asignaciones: list[PreguntaKPICreate]) -> list[PreguntaKPI]:
        """Inserta por lote las relaciones validadas por el investigador (RN_07)."""
        db_objs = [PreguntaKPI(**obj.model_dump()) for obj in asignaciones]
        db.add_all(db_objs)
        db.commit()
        return db_objs

    def delete_by_instrumento(self, db: Session, id_instrumento: int) -> None:
        """Elimina relaciones en cascada al retirar un instrumento (DA-14)."""
        db.query(PreguntaKPI).filter(PreguntaKPI.id_instrumento == id_instrumento).delete()
        db.commit()

pregunta_kpi_repo = PreguntaKPIRepository()