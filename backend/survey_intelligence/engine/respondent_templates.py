# survey_intelligence/engine/respondent_templates.py
"""
Plantillas DETERMINISTAS para el resumen de un respondente (rediseño v2, sin LLM).

Reglas por tipo canónico + ensamblado fijo. Universales: lo que cambia entre encuestas
son los datos sustituidos, no la plantilla. Reproducible y auditable.

Ver docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md (perfiles de respondente).
"""
from __future__ import annotations

from survey_intelligence.contracts.enums import CanonicalQuestionType as QT

# Tipos ESTRUCTURADOS que alimentan el resumen (las abiertas NO entran; van íntegras aparte).
STRUCTURED_TYPES = {
    QT.OPCION_UNICA, QT.OPCION_MULTIPLE, QT.LIKERT, QT.NUMERICA, QT.FECHA, QT.MATRIZ,
}
OPEN_TYPES = {QT.TEXTO_CORTO, QT.TEXTO_LARGO}


def _short(text: str, max_words: int = 8) -> str:
    """Acorta la pregunta a algo legible dentro de una frase-resumen."""
    limpio = text.strip().rstrip("?").lstrip("¿").strip()
    palabras = limpio.split()
    if len(palabras) <= max_words:
        return limpio
    return " ".join(palabras[:max_words]) + "…"


def fragment_for(question_type: QT, pregunta: str, labels) -> str | None:
    """
    Devuelve un fragmento de frase para una respuesta estructurada, o None si no aplica.

    `labels` es la parte legible de la respuesta del respondente (str, list o dict).
    """
    q = _short(pregunta)

    if question_type in (QT.OPCION_UNICA, QT.LIKERT):
        val = labels if isinstance(labels, str) else (labels[0] if isinstance(labels, list) and labels else None)
        return f"{q}: {val}" if val else None

    if question_type == QT.OPCION_MULTIPLE:
        if isinstance(labels, list) and labels:
            return f"{q}: {', '.join(str(x) for x in labels)}"
        return None

    if question_type == QT.NUMERICA:
        val = labels if isinstance(labels, str) else None
        return f"{q} = {val}" if val else None

    if question_type == QT.FECHA:
        val = labels if isinstance(labels, str) else None
        return f"{q}: {val}" if val else None

    if question_type == QT.MATRIZ:
        # Resumen breve: nº de ítems respondidos (el detalle queda en `respuestas`).
        if isinstance(labels, dict) and labels:
            return f"{q}: {len(labels)} aspecto(s) evaluado(s)"
        return None

    return None


def assemble_summary(fragments: list[str]) -> str:
    """
    Ensambla los fragmentos en una frase fija. Determinístico.

    "El respondente {f1}, {f2} y {f3}." — con manejo de 0/1/N fragmentos.
    """
    frags = [f for f in fragments if f]
    if not frags:
        return "El respondente no proporcionó respuestas estructuradas."
    if len(frags) == 1:
        cuerpo = frags[0]
    else:
        cuerpo = ", ".join(frags[:-1]) + " y " + frags[-1]
    return f"El respondente {cuerpo}."
