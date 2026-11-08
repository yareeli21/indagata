"""7 nov: la búsqueda por similitud deja fuera los chunks de personas salvo que la consulta nombre a alguien."""
from __future__ import annotations

from services.rag_service import _donde

SIN_PERSONAS = {"seccion": {"$nin": ["respondente", "alumno"]}}


def test_sin_persona_nombrada_no_entran_respondentes_ni_alumnos():
    assert _donde(["127"], "¿Cuántos trabajan en algo relacionado con su carrera?") == {
        "$and": [{"instrumentoId": {"$in": ["127"]}}, SIN_PERSONAS]}
    assert _donde([], "¿Qué opinan del comedor?") == SIN_PERSONAS


def test_con_persona_nombrada_entran_sus_chunks():
    assert _donde(["130"], "¿Qué respondió el alumno A001?") == {"instrumentoId": {"$in": ["130"]}}
    assert _donde([], "¿Qué dijo E02 sobre su tutor?") is None
    # «r03» es un reactivo, no una persona.
    assert _donde(["130"], "¿Cómo respondieron el r03?")["$and"][1] == SIN_PERSONAS
