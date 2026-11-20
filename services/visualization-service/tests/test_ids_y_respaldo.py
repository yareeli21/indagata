"""Reglas sin IDs de ejemplo y respaldo de los datos de un respondente (12 nov, consulta 4046).

llama3.2:3b copiaba «R017» de las reglas 11 y 12 cuando la pregunta no nombraba a nadie; la verificación rechazaba la
redacción y el respaldo era solo «Respuestas interpretadas de E01 (…)»."""
from types import SimpleNamespace

from services import consulta_planificada, ejecutor, prompt


def test_reglas_sin_ids_de_ejemplo():
    assert not prompt.personas(prompt.SISTEMA)


def test_mensaje_lleva_los_ids_reales():
    texto = prompt.construir("¿cuál fue su experiencia con el psicólogo?",
                             [{"numero": 1, "titulo": "T", "tipo": "Entrevista", "seccion": "intercambio",
                               "fragmento": "Participante E01, pregunta guía p04: …"}],
                             resultado="Respuestas interpretadas de E01.")
    assert "PERSONAS EN LOS DATOS (cítalas solo con estos IDs): E01\n" in texto


def test_mensaje_sin_personas_no_lleva_la_linea():
    assert "PERSONAS EN LOS DATOS" not in prompt.construir("¿de qué trata?", [], resultado="p04: 3 de 10.")


def _ejecucion():
    tabla = ejecutor.Tabla("Respuestas interpretadas", ["Pregunta", "E01"], [
        ["Contexto: Edad", "21"],
        ["p03 «¿Sabías que la universidad ofrece servicios?»", "Sabía que existía algo."],
        ["p04 «¿Has utilizado alguno de esos servicios?»", "Sí, fui a orientación psicológica este semestre."],
        ["p07 «¿Cómo valoras la atención que recibiste?»", "La psicóloga fue muy amable."]])
    return SimpleNamespace(intencion="datos_respondente", respondentes=["INS-0129-E01"], tablas=[tabla],
                           criterio="el primero por número de respondente (de 1)", lineas=[],
                           instrumento=SimpleNamespace(titulo="Salud mental"))


def test_respaldo_cita_las_respuestas_mas_parecidas():
    apoyo = [{"preguntaId": "INS-0129-p04", "respondenteId": "INS-0129-E01"},
             {"preguntaId": "INS-0129-p04", "respondenteId": "INS-0129-E01"},
             {"preguntaId": "INS-0129-p07", "respondenteId": ""},
             {"preguntaId": "INS-0129-p03", "respondenteId": "INS-0129-E01"}]
    texto = consulta_planificada.directa([_ejecucion()], apoyo)
    assert "«Sí, fui a orientación psicológica este semestre.»" in texto
    assert "«La psicóloga fue muy amable.»" in texto
    assert "Sabía que existía" not in texto  # solo las dos más parecidas
    assert texto.index("p04") < texto.index("p07")


def test_respaldo_no_cita_respuestas_de_otra_persona():
    apoyo = [{"preguntaId": "INS-0129-p04", "respondenteId": "INS-0129-E02"}]
    assert consulta_planificada.directa([_ejecucion()], apoyo).startswith("Respuestas interpretadas de E01")


def test_respaldo_sin_apoyo_queda_igual():
    assert consulta_planificada.directa([_ejecucion()]).startswith("Respuestas interpretadas de E01")

