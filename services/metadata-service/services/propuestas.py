"""Orquesta la propuesta de metadatos: análisis → heurísticas → LLM.

Las dos pantallas del asistente (Dublin Core y metadatos del tipo) piden su
propuesta por separado; ambas comparten el análisis del archivo y una sola
consulta al LLM (cacheadas por instrumento).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from services import analizador, llm_client
from services.analizador import Analisis
from services.campos import TIPO_UI, campos_de
from services.dc_manager import DCManager
from services.enrichment_engine import EnrichmentEngine

# Campos interpretativos que el LLM puede completar, con la instrucción para él.
CAMPOS_LLM: dict[str, str] = {
    "dc_description": "descripción breve (2 o 3 oraciones) de qué mide el instrumento y a quién se dirige",
    "dc_subject": "temas principales separados por comas",
    "objetivo": "objetivo del instrumento en una oración",
    "poblacion_objetivo": "población a la que se dirige",
    "constructo_principal": "constructo o concepto teórico principal que mide",
    "palabras_clave": "arreglo de 5 a 8 palabras clave",
    "dimensiones": "arreglo con las dimensiones o subescalas",
    "metodologia": "tipo de entrevista (estructurada, semiestructurada, a profundidad o grupo focal)",
    "unidad_de_aprendizaje": "materia o unidad de aprendizaje evaluada",
    "objetivo_de_evaluacion": "qué se busca evaluar con la prueba",
    "tipo_de_prueba": "diagnóstica, formativa o sumativa",
    "subareas": "subáreas o temas evaluados",
    "competencias": "competencias evaluadas",
}

_TTL = 900.0
_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


@dataclass
class Propuesta:
    analisis: Analisis
    dc: dict[str, Any]
    dc_origen: dict[str, str]
    especificos: dict[str, Any]
    especificos_origen: dict[str, str]


def _vacio(valor: Any) -> bool:
    return valor in (None, "", [], {})


def _sugerencias(raw: Any, analisis: Analisis, pendientes: dict[str, str]) -> dict[str, Any]:
    clave = (raw.id_crudo, raw.raw_archivo, tuple(sorted(pendientes)))
    ahora = time.monotonic()
    with _lock:
        guardado = _cache.get(clave)
        if guardado and guardado[0] > ahora:
            return guardado[1]
    tipo_ui = TIPO_UI.get((raw.tipo_instrumento or "").lower(), "instrumento")
    sugerencias = llm_client.sugerir(tipo_ui, analisis.titulo, analisis.contexto_llm(), pendientes)
    # Solo se cachea una respuesta útil: si el modelo no respondió, se reintenta luego.
    if sugerencias:
        with _lock:
            _cache[clave] = (ahora + _TTL, sugerencias)
    return sugerencias


def construir(raw: Any, procesado: Any, autor_nombre: str, *, usar_llm: bool) -> Propuesta:
    analisis = analizador.analizar(raw, procesado)
    dc, dc_origen = DCManager.proponer(raw, autor_nombre, analisis)
    especificos, esp_origen = EnrichmentEngine.proponer(raw, analisis, dc)

    if usar_llm:
        aplicables = {"dc_description", "dc_subject"} | {c.clave for c in campos_de(raw.tipo_instrumento)}
        pendientes = {
            clave: descripcion
            for clave, descripcion in CAMPOS_LLM.items()
            if clave in aplicables
            and (
                _vacio(dc.get(clave) if clave.startswith("dc_") else especificos.get(clave))
                or (clave in analisis.plantillas and (dc_origen.get(clave) or esp_origen.get(clave)) == "inferido")
            )
        }
        sugerencias = _sugerencias(raw, analisis, pendientes) if pendientes else {}
        for clave, valor in sugerencias.items():
            if clave.startswith("dc_"):
                dc[clave] = ", ".join(valor) if isinstance(valor, list) else valor
                dc_origen[clave] = "llm"
            elif clave in especificos:
                especificos[clave] = valor
                esp_origen[clave] = "llm"

    return Propuesta(analisis, dc, dc_origen, especificos, esp_origen)


def limpiar_cache() -> None:
    with _lock:
        _cache.clear()
