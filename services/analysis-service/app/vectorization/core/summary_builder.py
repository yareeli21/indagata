"""Construcción del texto del SUMMARY del instrumento.

El summary es lo ÚNICO que se vectoriza en la colección `summary_instrument`:
el instrumento original (texto del .md, solo preguntas) + los metadatos clave
extraídos del JSON. NO incluye las respuestas de los respondentes.

El texto resultante es la entrada del embedding; mantenerlo limpio y centrado en
lo semánticamente relevante es lo que hace que la búsqueda de KPIs sea precisa.
"""
from __future__ import annotations


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
