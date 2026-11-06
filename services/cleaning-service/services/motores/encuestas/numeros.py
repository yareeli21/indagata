"""Números escritos de otra forma en columnas numéricas de una encuesta (sin decisión del investigador).

Solo se aplican en columnas donde casi todo ya es un número, y cada cambio se reporta con su fila:
  - Coma decimal → punto: «4,5» → «4.5» (las columnas mezclaban «4,5» y «4.5»).
  - Número con la etiqueta de la escala: «4 (De acuerdo)», «4 - De acuerdo» → «4», solo si la etiqueta
    está en esa posición en alguna escala del diccionario (si no coinciden, no se adivina).
  - Número escrito con palabras, del cero al diez: «cuatro» → «4».
  - Número con su unidad: «19 años», «25 hrs», «$300» → «19», «25», «300».

Va antes de inferir los tipos: antes, estos valores salían como «fuera de rango» y se sugería vaciarlos.
"""
from __future__ import annotations

import re

from services.configuracion import normalizar_texto
from services.motores.encuestas import universales
from services.motores.encuestas.likert import numero, posiciones

_COMA_DECIMAL = re.compile(r"^-?\d+,(\d{1,2}|\d{4,})$")  # «1,500» puede ser un millar: no se toca
_CON_ETIQUETA = re.compile(r"^(?P<n>\d{1,2})\s*(?:[-–—:.=]\s*|\(\s*)(?P<etq>[^\d()]+?)\s*\)?$")
_PALABRAS = {"cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
             "ocho": 8, "nueve": 9, "diez": 10}
_UNIDAD = re.compile(
    r"^\$?\s*(?P<n>-?\d+(?:[.,]\d+)?)\s*(?:anos?|hrs?|horas?|h|min|mins|minutos?|semanas?|meses|mes|dias?|kg|kilos?|"
    r"cm|km|m|%|pesos|mxn|puntos?|pts?)\.?$"
)
_MIN_PRESENTES = 5
_MIN_NUMERICOS = 0.8

_REGLAS = {
    "coma_decimal": "Números con coma decimal escritos con punto («4,5» → «4.5»).",
    "numero_con_etiqueta": "Número con la etiqueta de la escala pegada: se dejó solo el número («4 (De acuerdo)» → «4»).",
    "numero_en_palabras": "Números escritos con palabras convertidos a cifras («cuatro» → «4»).",
    "unidad_quitada": "Unidad quitada de números en columnas numéricas («19 años» → «19»).",
}


def _texto_numero(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _convertir(valor: str) -> tuple[str, str] | None:
    """(regla, valor nuevo) si el valor es un número escrito de otra forma; None si no."""
    v = valor.strip()
    if _COMA_DECIMAL.match(v):
        return "coma_decimal", v.replace(",", ".")
    if m := _CON_ETIQUETA.match(v):
        if int(m.group("n")) in posiciones(m.group("etq")):
            return "numero_con_etiqueta", m.group("n")
        return None
    n = normalizar_texto(v)
    if n in _PALABRAS:
        return "numero_en_palabras", str(_PALABRAS[n])
    if (m := _UNIDAD.match(n)) and numero(m.group("n")) is not None:
        return "unidad_quitada", _texto_numero(numero(m.group("n")))
    return None


def normalizar(tabla: universales.TablaPreparada) -> list[dict]:
    """Aplica las conversiones en sitio y devuelve una transformación por regla, con sus casos."""
    casos: dict[str, list[dict]] = {}
    totales: dict[str, int] = {}
    for c in tabla.columnas:
        presentes = [v for v in c.valores if v is not None]
        if len(presentes) < _MIN_PRESENTES:
            continue
        convertibles = {i: r for i, v in enumerate(c.valores) if v is not None and (r := _convertir(v))}
        directos = sum(1 for v in presentes if numero(v) is not None)
        # Columna numérica: casi todo es número (contando los que se pueden convertir).
        if directos + sum(1 for i, (r, _) in convertibles.items() if numero(c.valores[i]) is None) < _MIN_NUMERICOS * len(presentes):
            continue
        if directos < 0.5 * len(presentes):
            continue
        for i, (regla, nuevo) in convertibles.items():
            totales[regla] = totales.get(regla, 0) + 1
            if len(casos.setdefault(regla, [])) < universales.MAX_CASOS:
                casos[regla].append({"fila": i + 1, "columna": c.etiqueta, "antes": c.valores[i], "despues": nuevo})
            c.valores[i] = nuevo
    return [{"regla": r, "detalle": _REGLAS[r], "afectados": totales[r], "casos": casos[r]} for r in _REGLAS if r in totales]
