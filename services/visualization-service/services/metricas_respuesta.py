"""Métricas de cada respuesta del chat para el botón «Ver métricas» (11 nov): deterministas, sin modelo juez.

Se calculan al leer la consulta, con lo que guardó `rag_log` (la respuesta, lo que vio el modelo y sus fuentes), así
que valen para cualquier instrumento, incluido uno que se suba mañana:

  recuperacion     qué fragmentos llegaron a la respuesta, su similitud (coseno del embedding), cuántas palabras de la
                   pregunta contienen, en qué lugar los puso cada búsqueda (semántica y por palabras) y por qué pasaron
                   (significado, palabras o ambos), frente al umbral configurado.
  fundamentacion   qué proporción de las oraciones de la respuesta está respaldada por lo recuperado: al menos la mitad
                   de sus palabras con contenido aparece en un mismo fragmento o en el resultado calculado. Es la versión
                   sin juez de la fidelidad («faithfulness») de RAGAS: más estricta con las paráfrasis libres, pero no se
                   equivoca por el juez.
  citas            qué proporción de las oraciones cita una fuente ([Fuente n]) y si alguna cita apunta a una fuente que
                   no existe.

Las cifras e IDs sin respaldo, la ruta y los tiempos ya los calcula `services/indicadores.py`.
"""
from __future__ import annotations

import re
from typing import Any

from shared.db.core.config import settings
from shared.models.rag_log import RagLog

from services import hibrida
from services.trazabilidad import numeros_citados

_MIN_RESPALDO = 0.5  # proporción de palabras de la oración que deben estar en un mismo fragmento
_MIN_PALABRAS_ORACION = 4  # oraciones más cortas (conectores, «En resumen:») no se cuentan
_MAX_EJEMPLOS = 3

_RE_CITA_TEXTO = re.compile(r"[\[(]\s*Fuentes?\s+[\d\s,ye]+[\])]|\[(?:Glosario|Ayuda|Fuente KPI):[^\]]*\]", re.IGNORECASE)
_RE_TABLA = re.compile(r"^\s*\|.*\|\s*$")


def _oraciones(texto: str) -> list[str]:
    """Oraciones y viñetas de la respuesta, sin tablas (las anexa el cálculo, no las escribe el modelo)."""
    lineas = [ln for ln in texto.splitlines() if ln.strip() and not _RE_TABLA.match(ln) and not ln.strip().startswith("**")]
    partes: list[str] = []
    for linea in lineas:
        for p in (p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿«\"*\[-])", linea)):
            # Una cita sola («[Fuente 1]» al final del párrafo, en su línea) es de la oración anterior.
            if partes and p and not _RE_CITA_TEXTO.sub("", p).strip(" .,;"):
                partes[-1] = f"{partes[-1]} {p}"
            elif p:
                partes.append(p)
    return partes


def _palabras(texto: str) -> list[str]:
    return hibrida.terminos(_RE_CITA_TEXTO.sub(" ", texto))


def fundamentacion(respuesta: str, contextos: list[str]) -> dict[str, Any]:
    oraciones = [o for o in _oraciones(respuesta) if len(_palabras(o)) >= _MIN_PALABRAS_ORACION]
    if not oraciones or not contextos:
        return {"oraciones": len(oraciones), "respaldadas": None, "proporcion": None, "sinRespaldo": []}
    respaldadas, sin = 0, []
    for oracion in oraciones:
        palabras = _palabras(oracion)
        mejor = max(hibrida.cobertura(palabras, c)[0] for c in contextos)
        if mejor >= _MIN_RESPALDO:
            respaldadas += 1
        elif len(sin) < _MAX_EJEMPLOS:
            sin.append(oracion[:220])
    return {"oraciones": len(oraciones), "respaldadas": respaldadas,
            "proporcion": round(respaldadas / len(oraciones), 3), "sinRespaldo": sin}


def citas(respuesta: str, fuentes_validas: set[int]) -> dict[str, Any]:
    oraciones = [o for o in _oraciones(respuesta) if len(_palabras(o)) >= _MIN_PALABRAS_ORACION]
    con_cita = sum(1 for o in oraciones if _RE_CITA_TEXTO.search(o))
    citados = numeros_citados(respuesta)
    return {"oraciones": len(oraciones), "conCita": con_cita,
            "proporcion": round(con_cita / len(oraciones), 3) if oraciones else None,
            "fuentesCitadas": sorted(citados), "citasInvalidas": sorted(citados - fuentes_validas)}


def _paso(f: dict[str, Any]) -> str:
    por_significado = f.get("score") is not None and f["score"] >= settings.RAG_MIN_SCORE
    por_palabras = hibrida.pasa_por_palabras(f.get("coincidencia"), f.get("palabras"))
    if por_significado and por_palabras:
        return "ambos"
    return "palabras" if por_palabras else ("significado" if por_significado else "contexto")


def recuperacion(fila: RagLog) -> dict[str, Any]:
    fragmentos = [c for c in fila.contexto_usado or [] if c.get("tipo") == "fragmento"]
    salida = []
    for c in fragmentos:
        rangos = c.get("rangos") or {}
        salida.append({
            "etiqueta": str(c.get("etiqueta") or c.get("seccion") or "fragmento"),
            "instrumentoId": str(c.get("instrumentoId") or ""),
            "similitud": c.get("score"),
            "coincidencia": c.get("coincidencia"),
            "rangoSemantico": rangos.get("semantica"),
            "rangoPalabras": rangos.get("palabras"),
            "paso": _paso(c),
        })
    scores = [f["similitud"] for f in salida if f["similitud"] is not None]
    return {
        "modo": "hibrida" if any(c.get("coincidencia") is not None for c in fragmentos) else "semantica",
        "umbral": settings.RAG_MIN_SCORE,
        "coberturaMinima": settings.RAG_MIN_COBERTURA,
        "similitudMaxima": round(max(scores), 4) if scores else (fila.score_max if fila.score_max is not None and fila.score_max < 1 else None),
        "similitudPromedio": round(sum(scores) / len(scores), 4) if scores else None,
        "fragmentos": salida,
    }


def calcular(fila: RagLog, respuesta_redactada: bool) -> dict[str, Any]:
    """Las tres métricas de una consulta registrada. Fundamentación y citas solo si la respuesta la escribió el
    modelo (un cálculo presentado tal cual o un mensaje fijo no se «fundamentan»: salen de los datos o del sistema)."""
    contextos = [str(c.get("texto") or "") for c in fila.contexto_usado or [] if c.get("texto")]
    fuentes = {int(f["numero"]) for f in ((fila.salida or {}).get("fuentes") or [])
               if isinstance(f, dict) and str(f.get("numero", "")).isdigit()}
    salida: dict[str, Any] = {"recuperacion": recuperacion(fila), "fundamentacion": None, "citas": None}
    if respuesta_redactada and fila.respuesta:
        salida["fundamentacion"] = fundamentacion(fila.respuesta, contextos)
        salida["citas"] = citas(fila.respuesta, fuentes)
    return salida
