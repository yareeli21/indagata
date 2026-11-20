"""Exportación de encuestas a SPSS (.sav).

Convierte la tabla de respuestas (encabezados + filas de texto) en un archivo
.sav listo para análisis cuantitativo:
  - nombres de variable válidos para SPSS (P1, P2… para preguntas largas; el
    nombre del encabezado si es corto, p. ej. «Edad», «Carrera»);
  - etiqueta de variable = texto completo de la pregunta;
  - columnas numéricas → escala; columnas de texto con pocas categorías → códigos
    con etiquetas de valor (ordinales si son escalas de acuerdo/frecuencia);
  - el resto → texto.

Con la limpieza confirmada (`fichas`: las columnas del reporte) el archivo sale de lo que ella decidió, no de heurísticas:
  - etiqueta de variable = texto de la pregunta de la limpieza (o del diccionario de datos);
  - escalas Likert con sus puntos en orden: el número de cada punto con su etiqueta de valor, medida ordinal;
    las respuestas fuera de la escala («No aplica») reciben códigos 97, 98… declarados como perdidos;
  - escala lineal → ordinal; numérica y calificación → escala; selección múltiple, ranking y texto → cadena;
  - binarias y categóricas → códigos con etiquetas de valor.

Microdatos: con los significados de la limpieza (diccionario de datos o lo escrito por la investigadora),
la etiqueta de variable es el texto de la pregunta y cada código conserva su número con su etiqueta de
valor («1 = Hombre»).
"""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata

_RESERVADAS = {"ALL", "AND", "BY", "EQ", "GE", "GT", "LE", "LT", "NE", "NOT", "OR", "TO", "WITH"}
_MAX_CATEGORIAS = 12
_CODIGO_FUERA = 97  # primer código para respuestas fuera de la escala (perdidos declarados)
_COMO_CADENA = {"opcion_multiple_varias", "ranking", "texto_corto", "texto_largo"}


def columnas_de_reporte(reporte: dict | None) -> dict[str, dict]:
    """{id de columna: su ficha} de las columnas conservadas en el reporte de una limpieza confirmada de encuesta."""
    especifico = ((reporte or {}).get("especifico") or {}).get("encuesta") or {}
    return {c["id"]: c for c in especifico.get("columnas") or [] if c.get("id") and c.get("estado") != "eliminada"}


def _texto_pregunta(columna: dict) -> str:
    texto = str(columna.get("etiqueta") or "").strip()
    if " " not in texto and "_" in texto:  # encabezado con guiones bajos en lugar de espacios
        texto = re.sub(r"_+", " ", texto).strip()
    return texto


def _ancla(valor: str, puntos: int) -> float | None:
    """Punto de la escala de una etiqueta de acuerdo o frecuencia: todas en 5 puntos, solo los extremos en otras."""
    p = _puntaje(valor)
    if p is None or (puntos != 5 and p not in (1.0, 5.0)):
        return None
    return float(puntos) if p == 5.0 else p


def _escala(valores: list[str], likert: dict) -> tuple[list, dict[float, str], list[float]] | None:
    """Códigos de una escala Likert de la limpieza: (valores, etiquetas de valor, códigos perdidos)."""
    codigos = {_sin_acentos(str(k)).strip().lower(): float(v) for k, v in (likert.get("codigos") or {}).items()}
    etiquetas = [str(e) for e in likert.get("etiquetas") or []]
    puntos = int(likert.get("puntos") or len(etiquetas) or 0)
    if not puntos:
        return None
    if not codigos and etiquetas and all(_numero(e) is None for e in etiquetas):
        codigos = {_sin_acentos(e).strip().lower(): float(i) for i, e in enumerate(etiquetas, start=1)}
    etiquetas_valor: dict[float, str] = {}
    if codigos:
        for i, e in enumerate(etiquetas, start=1):
            etiquetas_valor[float(codigos.get(_sin_acentos(e).strip().lower(), i))] = e[:120]
    else:  # escala numérica: solo se etiquetan los puntos que traen texto
        etiquetas_valor = {float(i): e[:120] for i, e in enumerate(etiquetas, start=1) if _numero(e) is None}
    fuera: dict[str, float] = {}
    salida: list = []
    for v in valores:
        if not v:
            salida.append(None)
            continue
        clave = _sin_acentos(v).strip().lower()
        if clave in codigos:
            salida.append(codigos[clave])
        elif _numero(v) is not None:
            salida.append(_numero(v))
        elif _ancla(v, puntos) is not None:  # extremo escrito en una escala numérica («Totalmente de acuerdo» = 5)
            salida.append(_ancla(v, puntos))
            etiquetas_valor.setdefault(_ancla(v, puntos), v[:120])
        else:
            if v not in fuera:
                fuera[v] = float(_CODIGO_FUERA + len(fuera))
                etiquetas_valor[fuera[v]] = v[:120]
            salida.append(fuera[v])
    return salida, etiquetas_valor, sorted(fuera.values())


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


def generar_sav(headers: list[str], filas: list[list[str]], titulo: str = "",
                significados: dict[str, dict] | None = None, fichas: dict[str, dict] | None = None) -> bytes:
    """Genera el contenido binario de un .sav (requiere pandas y pyreadstat).

    `significados`: {encabezado: {"pregunta": …, "valores": {código: etiqueta}}} de la limpieza confirmada.
    `fichas`: {encabezado: ficha de la columna} del reporte de esa limpieza (`columnas_de_reporte`).
    """
    import pandas as pd
    import pyreadstat

    nombres = nombres_variables(headers)
    columnas: dict[str, list] = {}
    etiquetas_valor: dict[str, dict[float, str]] = {}
    medidas: dict[str, str] = {}
    perdidos: dict[str, list[dict[str, float]]] = {}

    significados = significados or {}
    fichas = fichas or {}
    for j, nombre in enumerate(nombres):
        valores = [(f[j] if j < len(f) else "").strip() for f in filas]
        presentes = [v for v in valores if v]
        numeros = [_numero(v) for v in presentes]
        codigos_valor = (significados.get(headers[j]) or {}).get("valores") or {}
        tipo = (fichas.get(headers[j]) or {}).get("tipo_canonico")
        likert = (fichas.get(headers[j]) or {}).get("likert")
        if not codigos_valor and likert and tipo in {"likert", "cuadricula"}:
            escala = _escala(valores, likert)
            if escala is not None:
                columnas_sav, etiquetas_sav, fuera = escala
                columnas[nombre] = columnas_sav
                if etiquetas_sav:
                    etiquetas_valor[nombre] = etiquetas_sav
                if fuera:
                    perdidos[nombre] = [{"lo": c, "hi": c} for c in fuera]
                medidas[nombre] = "ordinal"
                continue
        si_no = {_sin_acentos(v).lower() for v in presentes}
        if not codigos_valor and tipo == "binaria" and si_no and si_no <= {"si", "no"}:
            columnas[nombre] = [None if not v else (1.0 if _sin_acentos(v).lower() == "si" else 0.0) for v in valores]
            etiquetas_valor[nombre] = {1.0: "Sí", 0.0: "No"}
            medidas[nombre] = "nominal"
            continue
        if not codigos_valor and tipo in _COMO_CADENA:
            columnas[nombre] = valores
            medidas[nombre] = "nominal"
            continue
        if not codigos_valor and tipo in {"escala_lineal", "numerica", "calificacion"} and all(x is not None for x in numeros):
            columnas[nombre] = [_numero(v) if v else None for v in valores]
            medidas[nombre] = "ordinal" if tipo == "escala_lineal" else "scale"
            continue
        if presentes and all(x is not None for x in numeros) and codigos_valor and all(_numero(k) is not None for k in codigos_valor):
            # Códigos numéricos con su significado: se conserva el número y se etiqueta.
            columnas[nombre] = [_numero(v) if v else None for v in valores]
            etiquetas_valor[nombre] = {float(_numero(k)): str(e)[:120] for k, e in codigos_valor.items()}
            medidas[nombre] = "ordinal" if tipo in {"likert", "cuadricula", "escala_lineal"} else "nominal"
            continue
        if codigos_valor:  # letras («A» = Libros): la categoría es su etiqueta
            valores = [codigos_valor.get(v, codigos_valor.get(v.upper(), v)) if v else v for v in valores]
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
    etiquetas = []
    for h, n in zip(headers, nombres):
        ficha = fichas.get(h) or {}
        texto = (significados.get(h) or {}).get("pregunta") or _texto_pregunta(ficha) or h
        if (ficha.get("likert") or {}).get("invertido"):
            texto += " (ítem invertido)"
        etiquetas.append(texto[:250] or n)
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
            missing_ranges=perdidos or None,
        )
        with open(ruta, "rb") as archivo:
            return archivo.read()
    finally:
        os.unlink(ruta)
