# app/services/metadatos_service.py
"""
Lógica de negocio para los metadatos Nivel 1 (globales, Dublin Core adaptado).
"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.instrumento import InstrumentoProcesado
from app.schemas.metadatos import MetadatosBase, MetadatosCompletos


def obtener_valores_iniciales(db: Session, instrumento_id: int) -> dict:
    """
    Regresa los valores que ya se pueden pre-llenar en el formulario:
    - tipo_instrumento: reutilizado del instrumento ya cargado
    - idioma: default fijo "es"
    - formato_archivo: inferido de la extensión del archivo guardado
    """
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()

    if not instrumento:
        return {}

    formato_archivo = None
    if instrumento.ruta_json:
        formato_archivo = Path(instrumento.ruta_json).suffix.lstrip(".").upper()

    return {
        "tipo_instrumento": instrumento.plataforma,
        "idioma": "es",
        "formato_archivo": formato_archivo,
    }


def guardar_metadatos_base(db: Session, instrumento_id: int, datos_formulario: dict) -> dict:
    """
    Valida los datos del formulario con Pydantic y los guarda en la columna
    `metadatos` (JSONB) del instrumento, dentro de la clave "base".
    Si ya existían metadatos "enriquecidos" (Nivel 2), se preservan.
    """
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()

    if not instrumento:
        return {"ok": False, "error": "Instrumento no encontrado."}

    try:
        metadatos_base = MetadatosBase(**datos_formulario)
    except Exception as e:
        return {"ok": False, "error": f"Datos inválidos: {e}"}

    enriquecidos_previos = {}
    if instrumento.metadatos and "enriquecidos" in instrumento.metadatos:
        enriquecidos_previos = instrumento.metadatos["enriquecidos"]

    metadatos_completos = MetadatosCompletos(
        base=metadatos_base,
        enriquecidos=enriquecidos_previos,
    )

    instrumento.metadatos = metadatos_completos.model_dump()
    instrumento.estado = "limpio"  # avanza el estado del pipeline, según tu convención
    db.commit()

    return {"ok": True, "instrumento_id": instrumento.instrumento_id}