"""Documento final: el insumo de los chunks del RAG (se construye después de los KPIs).

Principios:
  - Cada respuesta se guarda UNA sola vez, dentro de su respondente / alumno / participante.
  - Las preguntas llevan su definición y un resumen precalculado (distribución por
    significado y por nivel, porcentajes, media): el RAG no debe contar filas.
  - IDs globales con prefijo del instrumento (INS-0012-p03, INS-0012-R001), porque el
    RAG consultará varios instrumentos a la vez.
  - Relación KPI ↔ pregunta navegable en ambos sentidos (evidencia ↔ kpis_relacionados).
  - Sin datos personales; se valida contra su JSON Schema antes de devolverse.
"""
from __future__ import annotations

from typing import Any

from services.documento import encuesta, entrevista, prueba
from services.documento.esquema import ESQUEMA_VERSION, DocumentoInvalido, validar
from services.estructura import Estructura

_CONSTRUCTORES = {
    "encuesta": encuesta.construir,
    "prueba_estandarizada": prueba.construir,
    "entrevista": entrevista.construir,
}

__all__ = ["ESQUEMA_VERSION", "DocumentoInvalido", "construir", "validar"]


def construir(
    perfil: dict[str, Any],
    estructura: Estructura,
    reporte: dict[str, Any],
    filas: list[dict[str, str]],
    avisos_previos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Documento final validado del tipo del perfil (lanza DocumentoInvalido si no cumple el esquema).

    `avisos_previos`: avisos de la estructura (p. ej. «sin instrumento original»), que
    se anteponen a los del propio documento.
    """
    documento = _CONSTRUCTORES[perfil["tipo"]](perfil, estructura, reporte, filas)
    if avisos_previos:
        documento["avisos"] = [{k: v for k, v in a.items() if k in ("codigo", "mensaje", "n", "pregunta_id")} for a in avisos_previos] + documento["avisos"]
    validar(documento)
    return documento
