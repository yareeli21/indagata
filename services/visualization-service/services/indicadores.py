"""Indicadores del sistema de cada respuesta del chat: deterministas, sin modelo juez (28 oct 2026).

Se calculan al leer la consulta, desde lo que ya guarda `rag_log` (plan, motivo, verificación, tiempos, contexto), y
se muestran en el panel de cada respuesta junto a las métricas del juez:

  intención        lo que entendió la etapa de interpretación (`plan.plan.intencion`), o «reglas» si respondió el
                   enrutador anterior.
  respuesta        quién escribió lo que se mostró: «redactada» (el modelo), «presentacion_fija» (el cálculo tal cual,
                   por diseño: tablas de respondentes, descripción, estructura) o «plantilla» (un mensaje fijo o de
                   respaldo: fuera de dominio, privacidad, manipulación, ayuda, aclaración armada por el código,
                   resultado literal porque la redacción falló dos veces, modelo no disponible).
  regeneraciones   cuántas veces la verificación rechazó la redacción y por qué (`plan.verificacion`).
  cifras           de las cifras que escribió el modelo, cuántas están en el contexto que vio (inventó números o no).
  ids_inventados   respondentes, preguntas o KPIs que el modelo nombró sin que estuvieran en el contexto.
  fragmentosRag    qué partes del instrumento recuperó Chroma por similitud y vio el modelo (4 nov).
  tiempos          milisegundos por etapa (interpretación, ejecución, recuperación, redacción, verificación) y total.
"""
from __future__ import annotations

from typing import Any

from shared.models.rag_log import RagLog

from services import dominio, evaluacion, metricas_respuesta

# Plantillas: mensajes fijos o de respaldo, con una explicación corta para la interfaz.
PLANTILLAS = {
    "privacidad": "Mensaje fijo de privacidad (no se identifica a nadie).",
    "manipulacion": "Mensaje fijo ante un intento de cambiar las reglas.",
    "fuera_de_dominio": "Mensaje fijo de pregunta fuera de dominio.",
    "aclaracion_ajena": "La interpretación pidió una aclaración, pero la pregunta se tomó como ajena al instrumento y se "
                        "respondió con el mensaje de fuera de dominio.",
    "sin_informacion": "Mensaje de que no hay información relacionada.",
    "ayuda": "Respuesta de la base de ayuda de la plataforma.",
    "aclaracion": "Pregunta de aclaración armada por el sistema.",
    "calculo_literal": "La redacción del modelo no pasó la verificación (también al reintentar): se mostró el resultado "
                       "calculado.",
    "modelo_no_disponible": "El modelo local no respondió.",
}


def _plantilla(fila: RagLog, verificacion: dict[str, Any]) -> str | None:
    motivo = fila.motivo or ""
    if fila.decision_dominio == dominio.PRIVACIDAD:
        return "privacidad"
    if fila.decision_dominio == dominio.MANIPULACION:
        return "manipulacion"
    if fila.decision_dominio == dominio.FUERA:
        return "aclaracion_ajena" if motivo.startswith("plan:aclaracion_ajena") else "fuera_de_dominio"
    if fila.decision_dominio == dominio.SIN_INFORMACION:
        return "sin_informacion"
    if fila.decision_dominio == dominio.AYUDA or fila.ruta == "ayuda":
        return "ayuda"
    if fila.ruta == "aclaracion":
        return "aclaracion"
    if (fila.salida or {}).get("degradado"):
        return "modelo_no_disponible"
    if verificacion.get("resultado") == "respaldo":
        return "calculo_literal"
    return None


def _contextos(fila: RagLog) -> list[str]:
    return [c.get("texto", "") for c in fila.contexto_usado or [] if c.get("texto")]


def _cifras(texto: str) -> set[float]:
    return {float(c.replace(",", ".")) for c in evaluacion._CIFRA.findall(evaluacion._NO_CIFRA.sub(" ", texto))}


def calcular(fila: RagLog) -> dict[str, Any]:
    """Indicadores de una consulta registrada (ver el docstring del módulo)."""
    from services.rag_service import _ID_DATO  # import tardío: rag_service importa este módulo indirectamente

    registro = fila.plan or {}
    plan = registro.get("plan") or {}
    verificacion = registro.get("verificacion") or {}
    metricas = fila.metricas or {}
    plantilla = _plantilla(fila, verificacion)
    calculada = bool(metricas.get("calculada")) or metricas.get("estado") == evaluacion.CALCULADA
    if plantilla:
        respuesta = "plantilla"
    elif calculada:
        respuesta = "presentacion_fija"
    else:
        respuesta = "redactada"

    salida: dict[str, Any] = {
        "modelo": fila.modelo_usado,
        "intencion": plan.get("intencion") or ("reglas" if (fila.motivo or "").startswith("estructurada") else None),
        "ruta": fila.ruta,
        "decision": fila.decision_dominio,
        "respuesta": respuesta,
        "plantilla": plantilla,
        "plantillaDetalle": PLANTILLAS.get(plantilla or ""),
        "regeneraciones": None,
        "primerFallo": verificacion.get("primer_fallo"),
        "verificacion": verificacion.get("resultado"),
        "cifrasTotal": None,
        "cifrasConRespaldo": None,
        "cifrasSinRespaldo": [],
        "idsInventados": [],
        # 4 nov: qué aportó la recuperación vectorial (Chroma) a esta respuesta: «E01 en p04», «p03»…
        "fragmentosRag": [str(c.get("etiqueta") or c.get("seccion") or "fragmento")
                          for c in fila.contexto_usado or [] if c.get("tipo") == "fragmento"],
        "tiempos": dict(fila.tiempos or {}),
        "latenciaMs": fila.latencia_ms,
    }
    if verificacion.get("intentos"):
        salida["regeneraciones"] = int(verificacion["intentos"]) - 1
    if respuesta == "redactada" and fila.respuesta:
        contextos = _contextos(fila)
        sin = evaluacion.cifras_sin_sustento(fila.respuesta, contextos)
        total = len(_cifras(fila.respuesta))
        salida.update(cifrasTotal=total, cifrasConRespaldo=total - len(sin), cifrasSinRespaldo=sin)
        en_contexto = set(_ID_DATO.findall("\n".join(contextos)))
        salida["idsInventados"] = sorted(set(_ID_DATO.findall(fila.respuesta)) - en_contexto)
    salida.update(metricas_respuesta.calcular(fila, respuesta == "redactada"))
    return salida
