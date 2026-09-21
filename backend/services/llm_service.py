# services/llm_service.py
"""
Servicio LLM de INDAGATA — contratos FUTUROS (RAG / KPIs).

NO accede a la base de datos ni a FastAPI. Recibe datos planos y devuelve dicts.

Estado actual: este módulo solo conserva los PUNTOS DE EXTENSIÓN del RAG principal
(funciones pendientes de implementación). El análisis ETL de instrumentos NO vive
aquí: lo realiza el Survey Intelligent System (SIS), invocado por el host vía
`services/sis_adapter.py`.

Histórico: la función `generar_propuestas_etl` y su parser JSON (el flujo ETL de un
solo paso, anterior al SIS) se retiraron por obsoletos. El parseo robusto de
respuestas del LLM ahora vive en `survey_intelligence/engine/parsing/robust_json.py`.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Contratos FUTUROS (RAG principal / inferencia de KPIs desde texto)
#
# Son puntos de extensión planificados, NO código muerto: se implementarán cuando
# se active el módulo de RAG principal (consumidor del JSON consolidado del SIS).
# ─────────────────────────────────────────────────────────────────────────────

def responder_consulta_rag(
    pregunta: str,
    contexto_chunks: list[str],
    historial: list[dict] | None = None,
) -> str:
    """
    [FUTURO] Responde preguntas sobre instrumentos usando RAG.

    Args:
        pregunta:        Pregunta del usuario.
        contexto_chunks: Fragmentos de texto recuperados del vectorstore.
        historial:       Historial de la conversación (opcional).

    Returns:
        Respuesta generada por el LLM en texto plano.
    """
    raise NotImplementedError(
        "Se implementará al activar el módulo RAG principal. "
        "El retriever vivirá en services/ (raíz del backend)."
    )


def inferir_kpis_desde_texto(
    texto: str,
    kpis_disponibles: list[dict],
) -> list[dict]:
    """
    [FUTURO] Infiere qué KPIs del catálogo están presentes en el texto.

    Nota: la inferencia de KPIs del flujo vigente ya la hace el SIS (etapa S7b).
    Este contrato queda reservado para usos futuros fuera del pipeline del SIS.

    Args:
        texto:             Contenido del instrumento.
        kpis_disponibles:  Lista de KPIs con {"kpi_id": int, "nombre": str, "descripcion": str}.

    Returns:
        Lista de {"kpi_id": int, "score": float, "evidencia": str}.
    """
    raise NotImplementedError(
        "Reservado para una futura iteración fuera del pipeline del SIS."
    )
