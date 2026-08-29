# app/services/metadatos_enriquecidos_service.py
"""
Lógica de negocio para el chat de metadatos enriquecidos (Nivel 2).
El LLM analiza el instrumento (metadatos base + muestra del archivo)
y hace preguntas para enriquecer los chunks antes de vectorizar.
"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.instrumento import InstrumentoProcesado

MARCADOR_FINAL = "[METADATOS_LISTOS]"


def _leer_muestra_archivo(ruta_archivo: str, max_caracteres: int = 2000) -> str:
    """Lee las primeras líneas del archivo crudo, como contexto para el LLM."""
    try:
        ruta = Path(ruta_archivo)
        if not ruta.exists():
            return "(no se pudo leer el archivo original)"
        contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        return contenido[:max_caracteres]
    except Exception as e:
        return f"(error leyendo archivo: {e})"


def construir_prompt_sistema(db: Session, instrumento_id: int) -> str:
    """
    Arma el system prompt inicial: quién es el asistente, qué tiene que hacer,
    y le da como contexto los metadatos base + una muestra del archivo real.
    """
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()

    if not instrumento:
        raise ValueError("Instrumento no encontrado")

    metadatos_base = {}
    if instrumento.metadatos and "base" in instrumento.metadatos:
        metadatos_base = instrumento.metadatos["base"]

    muestra_archivo = ""
    if instrumento.ruta_json:
        muestra_archivo = _leer_muestra_archivo(instrumento.ruta_json)

    return f"""Eres un asistente que ayuda a enriquecer los metadatos de instrumentos de recolección de datos educativos (encuestas, entrevistas, pruebas estandarizadas) para un sistema RAG.

Ya se capturaron estos metadatos base del instrumento:
- Título: {metadatos_base.get('titulo', 'N/A')}
- Institución responsable: {metadatos_base.get('institucion_responsable', 'N/A')}
- Objetivo: {metadatos_base.get('objetivo', 'N/A')}
- Tipo de instrumento: {metadatos_base.get('tipo_instrumento', 'N/A')}
- Población y alcance: {metadatos_base.get('poblacion_alcance', 'N/A')}

Aquí tienes una muestra del contenido real del archivo subido:
---
{muestra_archivo}
---

Tu tarea: analiza el contenido del archivo y los metadatos base, e identifica 2-4 áreas de oportunidad donde metadatos adicionales enriquecerían la búsqueda semántica futura (por ejemplo: dimensiones o constructos que mide, subgrupos de la población, contexto institucional relevante, limitaciones del instrumento, etc.).

Hazle preguntas al usuario UNA a la vez, de forma breve y clara, para obtener esos metadatos adicionales.

Cuando consideres que ya tienes suficiente información (después de 2-4 preguntas respondidas), termina tu último mensaje incluyendo exactamente esta marca al final: {MARCADOR_FINAL}

No uses la marca antes de tiempo — solo cuando realmente hayas terminado de recopilar información."""


def guardar_metadatos_enriquecidos(db: Session, instrumento_id: int, historial: list[dict] | None) -> dict:
    """Guarda el historial del chat (o lo omite) dentro de metadatos.enriquecidos."""
    instrumento = db.query(InstrumentoProcesado).filter(
        InstrumentoProcesado.instrumento_id == instrumento_id
    ).first()

    if not instrumento:
        return {"ok": False, "error": "Instrumento no encontrado."}

    metadatos_actuales = instrumento.metadatos or {}
    metadatos_actuales["enriquecidos"] = {
        "historial_chat": historial or [],
        "omitido": historial is None,
    }
    instrumento.metadatos = metadatos_actuales
    instrumento.estado = "estandarizado"  # avanza el pipeline
    db.commit()

    return {"ok": True}