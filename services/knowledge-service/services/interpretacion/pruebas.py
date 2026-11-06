"""Intérprete de respuestas de pruebas estandarizadas (CSV largo de la limpieza).

Cada fila del CSV limpio trae: id_alumno; pregunta; respuesta; estado (valida | nula | NR);
motivo. Indagata no califica las pruebas: no hay respuesta correcta. Se convierte en:
  - respuesta:    la letra tal cual (None si vacía)
  - significado:  texto de la opción si el original lo tiene; si no, «Opción C».
                  En las nulas, el motivo legible («Respuesta múltiple (AB)»).
  - estado:       valida | nula | sin_respuesta     (NR → sin_respuesta)
  - motivo:       el de la limpieza (no_respondida, respuesta_multiple, ilegible…)
"""
from __future__ import annotations

from typing import Any

from services.interpretacion.config import reglas


_VF = {"V": "Verdadero", "F": "Falso", "VERDADERO": "Verdadero", "FALSO": "Falso", "CIERTO": "Verdadero"}
_SI_NO = {"SI": "Sí", "SÍ": "Sí", "S": "Sí", "NO": "No", "N": "No"}


def _significado(respuesta: str, tipo: str, letras: dict[str, str], puntos_max: int | None) -> str:
    r = respuesta.strip()
    if tipo == "verdadero_falso":
        return _VF.get(r.upper(), r)
    if tipo == "puntos":
        return f"{r} de {puntos_max} puntos" if puntos_max else f"{r} puntos"
    if tipo == "escala":
        return f"{r} en escala 1–{puntos_max}" if puntos_max else r
    if tipo == "si_no":
        return _SI_NO.get(r.upper(), r)
    if tipo == "numerica":
        return r
    letra = r.upper()
    return letras.get(letra) or f"Opción {letra}"


def interpretar(fila: dict[str, str], letras: dict[str, str], tipo: str = "opcion_multiple", puntos_max: int | None = None) -> dict[str, Any]:
    """Respuesta interpretada: qué eligió el alumno y qué significa (sin calificarla)."""
    respuesta = (fila.get("respuesta") or "").strip()
    estado = (fila.get("estado") or "").strip()
    motivo = (fila.get("motivo") or "").strip()
    salida: dict[str, Any] = {"respuesta": respuesta or None}
    if estado == "valida":
        salida.update(estado="valida", significado=_significado(respuesta, tipo, letras, puntos_max))
        return salida
    if estado == "NR" or (not respuesta and estado != "nula"):
        salida.update(estado="sin_respuesta", motivo=motivo or "no_respondida")
        return salida
    legible = (reglas().get("motivos_prueba") or {}).get(motivo) or "Respuesta nula"
    salida.update(estado="nula", motivo=motivo or "desconocido", significado=f"{legible} ({respuesta})" if respuesta else legible)
    return salida
