# app/services/limpieza_service.py
"""
Servicio de limpieza y estandarización de instrumentos.
La limpieza automática (determinística) queda como TODO — ver clasificador.py.
La limpieza asistida usa el LLM para sugerir reglas y preguntar antes de aplicarlas.
"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.instrumento import InstrumentoProcesado

MARCADOR_FINAL = "[LIMPIEZA_LISTA]"


def aplicar_limpieza_automatica(db: Session, instrumento_id: int) -> dict:
    """
    TODO: implementar limpieza real usando clasificador.py:
    - clasificar_columnas_tabla() para detectar texto_libre / numerica / categorica
    - aplicar lowercase, puntuación, stopwords SOLO a columnas texto_libre
    - guardar el archivo limpio (probablemente en JSON_PATH)
    """
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()
    if not instrumento:
        return {"ok": False, "error": "Instrumento no encontrado."}

    instrumento.estado = "limpio"
    db.commit()
    return {"ok": True, "instrumento_id": instrumento.instrumento_id}


def construir_prompt_sistema_limpieza(db: Session, instrumento_id: int) -> str:
    """
    TODO: reemplazar con reglas específicas por tipo de instrumento
    (encuesta / entrevista / prueba estandarizada). Por ahora es un
    prompt genérico para dejar la conexión funcional.
    """
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()
    if not instrumento:
        raise ValueError("Instrumento no encontrado")

    muestra_archivo = ""
    if instrumento.ruta_json and Path(instrumento.ruta_json).exists():
        muestra_archivo = Path(instrumento.ruta_json).read_text(
            encoding="utf-8", errors="ignore"
        )[:2000]

    return f"""Eres un asistente que ayuda a decidir reglas de limpieza para un instrumento de tipo "{instrumento.plataforma}".

Aquí tienes una muestra del contenido real del archivo:
---
{muestra_archivo}
---

Identifica 1-3 posibles problemas de calidad de datos (celdas vacías, preguntas sin responder, columnas con datos inconsistentes, etc.) y pregúntale al usuario, UNO a la vez, si quiere que apliques cada regla antes de continuar.

Cuando termines de revisar los problemas relevantes, incluye exactamente esta marca al final de tu último mensaje: {MARCADOR_FINAL}"""


def guardar_limpieza_asistida(db: Session, instrumento_id: int, historial: list[dict] | None) -> dict:
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()
    if not instrumento:
        return {"ok": False, "error": "Instrumento no encontrado."}

    metadatos_actuales = instrumento.metadatos or {}
    metadatos_actuales["limpieza_asistida"] = {
        "historial_chat": historial or [],
        "omitido": historial is None,
    }
    instrumento.metadatos = metadatos_actuales
    db.commit()
    return {"ok": True, "instrumento_id": instrumento.instrumento_id}