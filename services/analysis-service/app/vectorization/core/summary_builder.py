"""Construcción del texto del SUMMARY del instrumento.

El summary es lo ÚNICO que se vectoriza en la colección `summary_instrument`:
el instrumento original (texto del .md, solo preguntas) + los metadatos clave
extraídos del JSON. NO incluye las respuestas de los respondentes.

El texto resultante es la entrada del embedding; mantenerlo limpio y centrado en
lo semánticamente relevante es lo que hace que la búsqueda de KPIs sea precisa.

El modelo de embeddings solo lee los primeros 128 tokens (~450 caracteres), así
que el vector del summary refleja sobre todo sus metadatos. Para que las preguntas
también cuenten, `trocear_instrumento()` parte el instrumento en fragmentos que sí
caben y `kpi_search.vector_instrumento()` los combina con el summary.
"""
from __future__ import annotations

import re

# ~115 tokens del modelo de embeddings: cabe completo en sus 128.
VENTANA_FRAGMENTO = 450
_RE_PALABRA = re.compile(r"[^\W\d_]{3}")


def build_summary(metadatos: dict[str, str], instrumento_original: str) -> str:
    """Arma el texto del summary a partir de metadatos clave + instrumento original.

    Args:
        metadatos:            {etiqueta: valor} de metadata_extractor.
        instrumento_original: Texto del instrumento (contenido del .md).

    Returns:
        Un texto único listo para vectorizar.
    """
    partes: list[str] = []

    if metadatos:
        partes.append("## Metadatos del instrumento")
        for etiqueta, valor in metadatos.items():
            partes.append(f"{etiqueta}: {valor}")

    texto_original = (instrumento_original or "").strip()
    if texto_original:
        partes.append("")
        partes.append("## Instrumento original")
        partes.append(texto_original)

    return "\n".join(partes).strip()


def _lineas_con_contenido(texto: str) -> list[str]:
    """Líneas con al menos una palabra; descarta separadores (`=====`, `-----`) y
    casillas de respuesta (`[ ] 1   [ ] 2`), que no aportan significado."""
    lineas: list[str] = []
    for cruda in (texto or "").splitlines():
        linea = " ".join(cruda.split())
        if linea and _RE_PALABRA.search(linea):
            lineas.append(linea)
    return lineas


def trocear_instrumento(texto: str, ventana: int = VENTANA_FRAGMENTO) -> list[str]:
    """Fragmentos de hasta `ventana` caracteres con líneas completas del instrumento.

    Una línea más larga que la ventana se corta por palabras.
    """
    fragmentos: list[str] = []
    actual = ""
    for linea in _lineas_con_contenido(texto):
        piezas: list[str] = []
        while len(linea) > ventana:
            corte = linea.rfind(" ", 0, ventana)
            corte = corte if corte > 0 else ventana
            piezas.append(linea[:corte])
            linea = linea[corte:].strip()
        piezas.append(linea)
        for pieza in piezas:
            candidato = f"{actual}\n{pieza}" if actual else pieza
            if len(candidato) <= ventana:
                actual = candidato
            else:
                fragmentos.append(actual)
                actual = pieza
    if actual:
        fragmentos.append(actual)
    return fragmentos
