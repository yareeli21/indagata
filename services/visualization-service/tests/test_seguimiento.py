"""Hilo de la conversación: seguimientos de inferencia sobre la respuesta anterior (services/seguimiento.py)."""
from __future__ import annotations

import pytest

from conftest import token
from services import seguimiento
from test_visualizacion import acervo  # noqa: F401 — fixture compartido

ANA = token(2)


@pytest.mark.parametrize("pregunta", [
    "¿Y por qué crees que pasa eso?",
    "¿Cómo podría afectar eso su rendimiento académico?",
    "¿Qué podría hacer la universidad para ayudarles?",
    "¿Qué podría implicar eso?",
    "¿Quién lo dijo?",
    "¿A qué se debe?",
])
def test_detecta_inferencias_sobre_lo_anterior(pregunta):
    assert seguimiento.es_inferencia(pregunta)


@pytest.mark.parametrize("pregunta", [
    "¿Y de ellos cuántos tienen beca?",  # dato nuevo: filtro sobre lo anterior (interpretación)
    "¿Qué porcentaje respondió que sí?",
    "¿Qué dijo R017 en p04?",
    "¿Qué opinan los docentes sobre la evaluación en línea en las universidades públicas?",  # tema nuevo, largo
    "¿Qué dicen los estudiantes sobre el apoyo de sus compañeros?",
])
def test_no_toma_por_seguimiento_lo_que_pide_datos_o_un_tema_nuevo(pregunta):
    assert not seguimiento.es_inferencia(pregunta)


def _conversar(cliente, ollama, monkeypatch):  # noqa: ANN001
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)  # vectores falsos
    primera = "¿qué tanto se esfuerzan en clase?"
    r = cliente.post("/rag/chat", json={"pregunta": primera, "instrumentoIds": ["1"], "stream": False}, headers=ANA)
    assert r.status_code == 200, r.text
    previa = r.json()
    assert previa["fuentes"], "la primera respuesta debe tener evidencia"
    historial = [{"rol": "usuario", "texto": primera},
                 {"rol": "asistente", "texto": previa["respuesta"], "consultaId": previa["consultaId"]}]
    return previa, historial


def test_seguimiento_razona_con_la_evidencia_de_la_respuesta_anterior(cliente, acervo, ollama, monkeypatch):  # noqa: F811
    previa, historial = _conversar(cliente, ollama, monkeypatch)
    r = cliente.post("/rag/chat", json={"pregunta": "¿Y por qué crees que pasa eso?", "instrumentoIds": ["1"],
                                        "stream": False, "historial": historial}, headers=ANA)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["decision"] == "dentro"
    prompt = ollama["prompts"][-1]
    assert "Es una pregunta de seguimiento" in prompt  # el formato de seguimiento
    assert "¿qué tanto se esfuerzan en clase?" in prompt  # la pregunta anterior en la conversación
    pasaje = previa["fuentes"][0]["pasajes"][0]["texto"]
    assert pasaje[:40] in prompt  # la misma evidencia, sin una búsqueda nueva
    # Las tarjetas son las de la respuesta anterior, con su numeración y sus pasajes.
    assert [f["instrumentoId"] for f in d["fuentes"]] == [previa["fuentes"][0]["instrumentoId"]]
    assert d["fuentes"][0]["pasajes"]


def test_un_dato_nuevo_en_la_conversacion_no_usa_el_seguimiento(cliente, acervo, ollama, monkeypatch):  # noqa: F811
    _, historial = _conversar(cliente, ollama, monkeypatch)
    cliente.post("/rag/chat", json={"pregunta": "¿Cuántos respondieron de acuerdo?", "instrumentoIds": ["1"],
                                    "stream": False, "historial": historial}, headers=ANA)
    assert all("Es una pregunta de seguimiento" not in p for p in ollama["prompts"])


def test_sin_consulta_anterior_valida_sigue_el_camino_normal(cliente, acervo, ollama, monkeypatch):  # noqa: F811
    _, historial = _conversar(cliente, ollama, monkeypatch)
    historial[0]["texto"] = "otra pregunta"  # el consultaId no corresponde a esa pregunta: no se lee
    cliente.post("/rag/chat", json={"pregunta": "¿Y por qué crees que pasa eso?", "instrumentoIds": ["1"],
                                    "stream": False, "historial": historial}, headers=ANA)
    assert all("Es una pregunta de seguimiento" not in p for p in ollama["prompts"])


def test_tras_una_aclaracion_retoma_la_ultima_respuesta_con_evidencia(cliente, acervo, ollama, monkeypatch):  # noqa: F811
    _, historial = _conversar(cliente, ollama, monkeypatch)
    # «¿Y de ellos cuántos tienen beca?» → aclaración (sin fuentes): el seguimiento siguiente se refiere a lo de antes.
    historial += [{"rol": "usuario", "texto": "¿y de ellos?"}, {"rol": "asistente", "texto": "¿A qué te refieres?"}]
    r = cliente.post("/rag/chat", json={"pregunta": "¿Qué podría implicar eso?", "instrumentoIds": ["1"],
                                        "stream": False, "historial": historial}, headers=ANA)
    assert r.status_code == 200, r.text
    assert "Es una pregunta de seguimiento" in ollama["prompts"][-1]
    assert "¿qué tanto se esfuerzan en clase?" in ollama["prompts"][-1]


def test_resultado_calculado_anterior_entra_como_evidencia():
    anterior = seguimiento.Anterior(
        7, "¿Cuántos trabajan más de 30 horas?", "Cumplen 44 de 180 (24.4 %).",
        fuentes=[{"numero": 1, "instrumentoId": "86", "titulo": "IEAE", "tipo": "Encuesta", "investigador": "",
                  "pasajes": []}],
        resultados=["[Fuente 1] IEAE (Encuesta)\nCriterio: horas_trabajo_semana > 30.\nCumplen 44 de 180 (24.4 %)."],
    )
    fragmentos = anterior.fragmentos()
    assert len(fragmentos) == 1 and fragmentos[0]["seccion"] == "resultado" and fragmentos[0]["numero"] == 1
    assert "24.4 %" in fragmentos[0]["fragmento"]


def test_el_formato_dice_que_personas_aparecen_en_la_evidencia():
    fragmentos = [{"fragmento": "Participante E02, pregunta p01: Soy el primero de mi familia…", "respondenteId": "E02"},
                  {"fragmento": "Pregunta guía p07", "respondenteId": ""}]
    assert "son E02: si mencionas a alguien" in seguimiento.formato(fragmentos)
    assert "no menciones ninguno" in seguimiento.formato([{"fragmento": "Ficha del instrumento"}])


def test_que_significa_eso_usa_el_seguimiento_si_la_interpretacion_no_retoma_el_plan():
    """Tras un cálculo, «¿qué significa eso?» se difiere: si el plan no se retoma (la interpretación eligió otra
    intención, 10 nov, consulta 176: un «hallazgo» de otras preguntas), responde el seguimiento con la evidencia."""
    anterior = seguimiento.Anterior(1, "¿qué porcentaje…?", "40 % de acuerdo", fuentes=[{"numero": 1}],
                                    intencion="resumen_pregunta", ultima=True)
    from services.plan_consulta import ESTRUCTURADAS

    assert seguimiento.lo_retoma_el_plan("¿Qué significa eso?", anterior, ESTRUCTURADAS)
    assert not seguimiento.lo_retoma_el_plan("¿Por qué crees que pasa?", anterior, ESTRUCTURADAS)
    anterior.intencion = "semantica_abierta"
    assert not seguimiento.lo_retoma_el_plan("¿Qué significa eso?", anterior, ESTRUCTURADAS)


def test_pide_cuentas_de_un_sin_informacion():
    assert seguimiento.pide_cuentas("Cómo inferiste que no existen estrategias en el instrumento?")
    assert seguimiento.pide_cuentas("¿Por qué dices que no hay información?")
    assert not seguimiento.pide_cuentas("¿Qué estrategias usan los estudiantes?")


def test_explicacion_sin_llm_con_la_parte_mas_parecida():
    anterior = seguimiento.SinRespuesta(5, "¿Qué estrategias usan?", "sin_informacion", 0.62, ["117"])
    cercano = {"etiqueta": "pregunta p03", "titulo": "Simulación", "score": 0.6234, "fragmento": "Pregunta p03: modalidad"}
    texto = seguimiento.explicar_sin_respuesta(anterior, cercano, 0.65)
    assert "65 % de similitud" in texto and "62 % de similitud [Fuente 1]" in texto and "pregunta p03" in texto
    assert "ninguna parte cercana" in seguimiento.explicar_sin_respuesta(anterior, None, 0.65)


def test_cuentas_de_un_sin_informacion_por_el_chat(cliente, acervo, ollama, monkeypatch):  # noqa: F811
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.999)  # nada alcanza: «sin información»
    primera = "¿qué tanto se esfuerzan en clase?"
    previa = cliente.post("/rag/chat", json={"pregunta": primera, "instrumentoIds": ["1"], "stream": False},
                          headers=ANA).json()
    assert previa["decision"] in ("sin_informacion", "fuera")
    historial = [{"rol": "usuario", "texto": primera},
                 {"rol": "asistente", "texto": previa["respuesta"], "consultaId": previa["consultaId"]}]
    n = len(ollama["prompts"])
    r = cliente.post("/rag/chat", json={"pregunta": "¿Cómo inferiste que no hay información?", "instrumentoIds": ["1"],
                                        "stream": False, "historial": historial}, headers=ANA).json()
    assert r["respuesta"].startswith("Respondí que no tenía información porque busqué «¿qué tanto se esfuerzan")
    assert len(ollama["prompts"]) == n  # sin LLM
