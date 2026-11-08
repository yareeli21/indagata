"""Fase 4 (7 nov): operaciones de entrevista sin modelo y menciones con «o»."""
from __future__ import annotations

from services import ejecutor, entrevista_ops
from services.enrutador import Instrumento
from tests import docs_ejemplo


def _ent() -> Instrumento:
    return Instrumento("3", "Entrevistas sobre evaluación", "entrevista", docs_ejemplo.entrevista())


def test_detecta_las_operaciones_solo_en_entrevistas():
    ent, enc = [_ent()], [Instrumento("1", "E", "encuesta", docs_ejemplo.encuesta())]
    casos = {"¿Cuántas palabras dijo la participante y cuántas el entrevistador?": "hablantes",
             "¿Respondió todas las preguntas de la guía? ¿Cuáles no?": "cobertura",
             "¿Cuál fue su respuesta más larga y a qué pregunta corresponde?": "extension",
             "¿Hubo preguntas de seguimiento que no estaban en la guía?": "fuera_guia",
             "¿La participante tiene depresión?": "diagnostico"}
    for pregunta, op in casos.items():
        assert entrevista_ops.detectar(pregunta, ent) == op, pregunta
        assert entrevista_ops.detectar(pregunta, enc) is None
    assert entrevista_ops.detectar("¿Qué dijo E01 sobre su tutor?", ent) is None


def test_cobertura_extension_y_diagnostico_salen_del_documento():
    ins = _ent()
    cobertura = entrevista_ops.responder("cobertura", "¿Respondió todas las preguntas de la guía?", [ins])
    assert "preguntas de la guía" in cobertura and "| Participante | Respondió | Sin respuesta |" in cobertura
    larga = entrevista_ops.responder("extension", "¿Cuál fue la respuesta más larga de E01?", [ins])
    assert larga.startswith("La respuesta más larga de E01 es la de") and "palabras" in larga
    diag = entrevista_ops.responder("diagnostico", "¿El participante E01 tiene ansiedad?", [ins])
    assert diag.startswith("No hago diagnósticos") and "ansiedad" in diag


def test_menciones_con_o_y_con_calificativo():
    assert ejecutor.grupos_termino("estrés o ansiedad") == [["estre"], ["ansie"]]
    assert ejecutor.grupos_termino("familia como apoyo") == [["famil"]]


def test_opcionales_y_escalas_del_instrumento():
    from services import instrumento_ops

    doc = docs_ejemplo.encuesta()
    doc["preguntas"][0]["escala"] = {"etiquetas": {"1": "Nada", "2": "2", "3": "3", "4": "4", "5": "Mucho"}}
    enc = [Instrumento("1", "Experiencia", "encuesta", doc)]
    assert instrumento_ops.detectar("¿Qué preguntas eran opcionales?", enc) == "opcionales"
    assert instrumento_ops.detectar("¿Cuáles preguntas usan escala del 1 al 5 y qué significan sus extremos?", enc) == "escalas"
    assert "no registra qué preguntas eran opcionales" in instrumento_ops.responder("opcionales", enc)
    escalas = instrumento_ops.responder("escalas", enc)
    assert "1 = Nada" in escalas and "5 = Mucho" in escalas and "p01" in escalas


def test_hallazgos_de_entrevista_salen_del_analisis_de_lo_que_cuentan():
    from services import hallazgos

    doc = docs_ejemplo.entrevista()
    i = doc["entrevistas"][0]["intercambios"][0]
    i["analisis"] = {"nlp": {"temas": [{"tema": "Exámenes", "cita": "x", "origen": "llm"}], "citas_clave": [i["respuesta"][:30]],
                             "valoracion": {"valor": "negativo", "cita": "x", "origen": "llm"}}}
    candidatos = hallazgos.candidatos("entrevista", doc)
    assert candidatos[0]["tipo"] == "lo_que_cuentan" and "habla de: exámenes" in candidatos[0]["texto"]
    assert "valoración negativo" in candidatos[0]["texto"] and "«" in candidatos[0]["texto"]
