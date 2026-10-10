"""Exportación de encuestas a SPSS (.sav).

Convierte la tabla de respuestas (encabezados + filas de texto) en un archivo
.sav listo para análisis cuantitativo:
  - nombres de variable válidos para SPSS (P1, P2… para preguntas largas; el
    nombre del encabezado si es corto, p. ej. «Edad», «Carrera»);
  - etiqueta de variable = texto completo de la pregunta;
  - columnas numéricas → escala; columnas de texto con pocas categorías → códigos
    con etiquetas de valor (ordinales si son escalas de acuerdo/frecuencia);
  - el resto → texto.
"""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata

_RESERVADAS = {"ALL", "AND", "BY", "EQ", "GE", "GT", "LE", "LT", "NE", "NOT", "OR", "TO", "WITH"}
_MAX_CATEGORIAS = 12


def _sin_acentos(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _puntaje(valor: str) -> float | None:
    v = _sin_acentos(valor).lower()
    if "desacuerdo" in v:
        return 1.0 if "totalmente" in v or "muy en" in v else 2.0
    if "ni de acuerdo" in v or "neutral" in v:
        return 3.0
    if "acuerdo" in v:
        return 5.0 if "totalmente" in v or "muy de" in v else 4.0
    for puntaje, claves in ((2.0, ("casi nunca",)), (4.0, ("casi siempre", "frecuentemente")),
                            (1.0, ("nunca",)), (5.0, ("siempre",)), (3.0, ("a veces", "algunas veces"))):
        if any(c in v for c in claves):
            return puntaje
    return None


def _numero(valor: str) -> float | None:
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def nombres_variables(headers: list[str]) -> list[str]:
    usados: set[str] = set()
    nombres: list[str] = []
    for j, encabezado in enumerate(headers, start=1):
        base = re.sub(r"[^A-Za-z0-9_]+", "_", _sin_acentos(encabezado)).strip("_")
        if not base or len(base) > 24 or not base[0].isalpha() or base.upper() in _RESERVADAS:
            base = f"P{j}"
        nombre, n = base, 2
        while nombre.lower() in usados:
            nombre, n = f"{base}_{n}", n + 1
        usados.add(nombre.lower())
        nombres.append(nombre)
    return nombres


def generar_sav(headers: list[str], filas: list[list[str]], titulo: str = "") -> bytes:
    """Genera el contenido binario de un .sav (requiere pandas y pyreadstat)."""
    import pandas as pd
    import pyreadstat

    nombres = nombres_variables(headers)
    columnas: dict[str, list] = {}
    etiquetas_valor: dict[str, dict[float, str]] = {}
    medidas: dict[str, str] = {}

    for j, nombre in enumerate(nombres):
        valores = [(f[j] if j < len(f) else "").strip() for f in filas]
        presentes = [v for v in valores if v]
        numeros = [_numero(v) for v in presentes]
        if presentes and all(x is not None for x in numeros):
            columnas[nombre] = [_numero(v) if v else None for v in valores]
            medidas[nombre] = "scale"
            continue
        categorias = sorted(set(presentes))
        if presentes and len(categorias) <= _MAX_CATEGORIAS:
            puntajes = {c: _puntaje(c) for c in categorias}
            ordinal = all(p is not None for p in puntajes.values())
            if ordinal:
                categorias.sort(key=lambda c: puntajes[c] or 0.0)
            codigos = {c: float(i) for i, c in enumerate(categorias, start=1)}
            columnas[nombre] = [codigos[v] if v else None for v in valores]
            etiquetas_valor[nombre] = {codigo: c[:120] for c, codigo in codigos.items()}
            medidas[nombre] = "ordinal" if ordinal else "nominal"
            continue
        columnas[nombre] = valores
        medidas[nombre] = "nominal"

    df = pd.DataFrame(columnas, columns=nombres)
    etiquetas = [h[:250] or n for h, n in zip(headers, nombres)]
    descriptor, ruta = tempfile.mkstemp(suffix=".sav")
    os.close(descriptor)
    try:
        pyreadstat.write_sav(
            df,
            ruta,
            file_label=_sin_acentos(titulo)[:60],
            column_labels=etiquetas,
            variable_value_labels=etiquetas_valor,
            variable_measure=medidas,
        )
        with open(ruta, "rb") as archivo:
            return archivo.read()
    finally:
        os.unlink(ruta)
