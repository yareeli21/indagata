"""Troceo de texto para indexado (diseño §4.5).

Ventanas de ~800 caracteres con solape de 150, cortando preferentemente en
límites de párrafo (`\\n\\n`) y luego de oración (`. `), descartando fragmentos
de menos de 40 caracteres. Chunking por caracteres (no tokens) para no añadir
una dependencia de tokenizador; 800/150 entra holgado en la ventana del modelo
de embeddings y da fragmentos citables.
"""
from __future__ import annotations

VENTANA = 800
SOLAPE = 150
MIN_LONGITUD = 40


def _dividir_en_unidades(texto: str) -> list[str]:
    """Parte el texto en unidades por párrafo y luego por oración."""
    unidades: list[str] = []
    for parrafo in texto.split("\n\n"):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        if len(parrafo) <= VENTANA:
            unidades.append(parrafo)
            continue
        # El párrafo es demasiado largo: subdividir por oración ('. ').
        buffer = ""
        for oracion in parrafo.split(". "):
            fragmento = oracion.strip()
            if not fragmento:
                continue
            candidato = f"{buffer}. {fragmento}" if buffer else fragmento
            if len(candidato) <= VENTANA:
                buffer = candidato
            else:
                if buffer:
                    unidades.append(buffer)
                buffer = fragmento
        if buffer:
            unidades.append(buffer)
    return unidades


def trocear(texto: str) -> list[str]:
    """Trocea `texto` en ventanas de ~800 chars con solape de 150.

    Devuelve una lista de fragmentos, cada uno con longitud >= 40. Un texto
    vacío o demasiado corto produce `[]`.
    """
    if not texto or not texto.strip():
        return []

    unidades = _dividir_en_unidades(texto)
    chunks: list[str] = []
    actual = ""

    for unidad in unidades:
        candidato = f"{actual}\n\n{unidad}" if actual else unidad
        if len(candidato) <= VENTANA:
            actual = candidato
            continue
        # Cerrar el chunk actual y arrancar uno nuevo con solape.
        if actual:
            chunks.append(actual)
            cola = actual[-SOLAPE:].strip()
            actual = f"{cola}\n\n{unidad}" if cola else unidad
        else:
            # Unidad individual mayor que la ventana: trocearla por ventana.
            inicio = 0
            while inicio < len(unidad):
                chunks.append(unidad[inicio : inicio + VENTANA])
                inicio += VENTANA - SOLAPE
            actual = ""

    if actual:
        chunks.append(actual)

    return [c.strip() for c in chunks if len(c.strip()) >= MIN_LONGITUD]
