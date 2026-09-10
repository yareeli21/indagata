# app/services/instrumento_service.py
from sqlalchemy.orm import Session

from app.models.instrumento import InstrumentoProcesado

PREFIJOS_CODIGO = {
    "encuesta": "ENC",
    "entrevista": "ENT",
    "prueba estandarizada": "PRB",
}


def _preparar_instrumentos(filas: list[InstrumentoProcesado]) -> list[dict]:
    """Agrega campos derivados: tipo legible, slug para CSS y código de catálogo."""
    resultado = []
    for i, fila in enumerate(filas, start=1):
        tipo = fila.plataforma or "Instrumento"
        tipo_normalizado = tipo.lower()
        prefijo = next(
            (v for k, v in PREFIJOS_CODIGO.items() if k in tipo_normalizado), "INS"
        )
        resultado.append({
            "nombre": fila.nombre,
            "plataforma": fila.plataforma,
            "estado": fila.estado,
            "fecha_procesamiento": fila.fecha_procesamiento,
            "tipo": tipo,
            "tipo_slug": tipo_normalizado.replace(" ", "-"),
            "codigo": f"{prefijo}·{i:03d}",
        })
    return resultado


def obtener_instrumentos(db: Session, tipo: str = "todos") -> list[dict]:
    query = db.query(InstrumentoProcesado)

    if tipo and tipo != "todos":
        query = query.filter(InstrumentoProcesado.plataforma.ilike(f"%{tipo}%"))

    filas = query.order_by(InstrumentoProcesado.fecha_procesamiento.desc()).all()
    return _preparar_instrumentos(filas)