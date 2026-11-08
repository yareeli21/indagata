"""Fase 3 (7 nov): saludos, consejos personales, malestar y pruebas sin calificar, con ejemplos del catálogo."""
from __future__ import annotations

import pytest

from services import cortesia
from services.enrutador import Instrumento
from tests import docs_ejemplo

ENCUESTA = {"encuesta"}
PRUEBA = {"prueba_estandarizada"}


@pytest.mark.parametrize("pregunta, tipo", [
    ("Hola", cortesia.CORTESIA), ("Buenas tardes", cortesia.CORTESIA), ("¿Qué tal? ¿Qué puedes hacer?", cortesia.CORTESIA),
    ("Gracias", cortesia.CORTESIA), ("Muchas gracias, adiós", cortesia.CORTESIA),
    ("¿Qué carrera me recomiendas estudiar?", cortesia.CONSEJO), ("Dame un consejo para no reprobar", cortesia.CONSEJO),
    ("Estoy muy estresada con mis exámenes, ¿qué me recomiendas?", cortesia.MALESTAR),
])
def test_detecta_cortesia_consejo_y_malestar(pregunta, tipo):
    assert cortesia.detectar(pregunta, ENCUESTA) == tipo


@pytest.mark.parametrize("pregunta", [
    "¿Qué recomendarían los estudiantes para mejorar la biblioteca?",  # pide datos, no un consejo para quien pregunta
    "¿Qué cambiaría la participante de los servicios?",
    "¿Qué análisis me recomiendas para estos datos?",                    # sugerencias de análisis: calidad de datos
    "Hola, ¿cuántos estudiantes trabajan más de 30 horas y además tienen beca en el turno vespertino?",  # larga: es una consulta
    "¿Cuántos están estresados por la carga académica?",                 # «estresados» de los respondentes, no de quien pregunta
])
def test_no_confunde_preguntas_sobre_los_datos(pregunta):
    assert cortesia.detectar(pregunta, ENCUESTA) is None


def test_pruebas_sin_calificar_solo_con_pruebas_en_el_alcance_y_sin_reactivo():
    assert cortesia.detectar("¿Cuántos alumnos aprobaron y cuál fue el promedio?", PRUEBA) == cortesia.SIN_CALIFICAR
    assert cortesia.detectar("¿Cuál es la respuesta correcta del reactivo 3?", PRUEBA) is None  # la responde el plan
    assert cortesia.detectar("¿Cuántos reprobaron alguna materia?", ENCUESTA) is None           # dato de la encuesta


def test_la_bienvenida_dice_el_instrumento_y_da_ejemplos_de_su_catalogo():
    encuesta = Instrumento("1", "Encuesta de satisfacción", "encuesta", docs_ejemplo.encuesta())
    entrevista = Instrumento("3", "Entrevistas sobre evaluación", "entrevista", docs_ejemplo.entrevista())
    hola = cortesia.responder(cortesia.CORTESIA, "Hola", [encuesta])
    assert "asistente de investigación de INDAGATA" in hola and "«Encuesta de satisfacción» (encuesta)" in hola
    textos = [p["texto"].rstrip("?").lstrip("¿")[:30] for p in docs_ejemplo.encuesta()["preguntas"]]
    assert hola.count("\n- ") == 3 and any(t in hola for t in textos)
    assert "R017" not in hola  # nada de ejemplos fijos ajenos al instrumento
    ejemplos = cortesia.ejemplos(entrevista)
    primero = docs_ejemplo.entrevista()["entrevistas"][0]["participante"].rsplit("-", 1)[-1]
    assert ejemplos and ejemplos[0].startswith(f"¿Qué dijo {primero} sobre «")
    assert cortesia.responder(cortesia.CORTESIA, "Gracias", [encuesta]).startswith("¡Con gusto!")
    consejo = cortesia.responder(cortesia.CONSEJO, "¿Qué carrera me recomiendas?", [encuesta])
    assert consejo.startswith("No doy consejos ni recomendaciones personales") and "\n- " in consejo
    malestar = cortesia.responder(cortesia.MALESTAR, "Estoy muy estresada", [encuesta])
    assert "servicios de apoyo" in malestar and "\n- " not in malestar
