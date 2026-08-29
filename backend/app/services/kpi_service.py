# app/services/kpi_service.py
from sqlalchemy.orm import Session

from app.models.kpi import Kpi


def obtener_todos_los_kpis(db: Session) -> list[Kpi]:
    """Regresa todos los KPIs activos, ordenados por nombre."""
    return (
        db.query(Kpi)
        .filter(Kpi.activo.is_(True))
        .order_by(Kpi.nombrekpi)
        .all()
    )