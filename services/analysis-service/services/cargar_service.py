# app/services/cargar_service.py
from sqlalchemy import cast, Date
from sqlalchemy.orm import Session

from app.models.instrumento import InstrumentoProcesado
from app.core.config import settings


def obtener_instrumentos_cargados(db: Session, tipo: str = "todos", fecha: str = "") -> list[InstrumentoProcesado]:
    """Lista todos los instrumentos ya registrados en la BD (todavía no hay noción de 'usuario dueño')."""
    query = db.query(InstrumentoProcesado)

    if tipo and tipo != "todos":
        query = query.filter(InstrumentoProcesado.plataforma.ilike(f"%{tipo}%"))
    if fecha:
        query = query.filter(cast(InstrumentoProcesado.fecha_procesamiento, Date) == fecha)

    return query.order_by(InstrumentoProcesado.fecha_procesamiento.desc()).all()


def procesar_carga(db: Session, nombre: str, tipo: str, contenido: bytes, nombre_archivo: str) -> dict:
    """Guarda el archivo crudo en disco local y registra el instrumento en la BD."""
    carpeta_destino = settings.raw_path_abs
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    ruta_destino = carpeta_destino / nombre_archivo
    ruta_destino.write_bytes(contenido)

    nuevo = InstrumentoProcesado(
        nombre=nombre,
        plataforma=tipo,
        ruta_json=str(ruta_destino),  # por ahora guardamos aquí la ruta del crudo
        estado="ingresado",
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {"ok": True, "instrumento_id": nuevo.instrumento_id}


def eliminar_instrumento(db: Session, instrumento_id: int) -> bool:
    fila = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()
    if not fila:
        return False

    db.delete(fila)
    db.commit()
    return True