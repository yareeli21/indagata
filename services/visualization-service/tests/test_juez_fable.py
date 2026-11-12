"""Juez Claude Fable 5.2: fórmulas de las seis métricas, cola en segundo plano y endpoint.

El juez se reemplaza por respuestas fijas (sin red): se verifican las FÓRMULAS de RAGAS 0.4.3 que se calculan aquí a
partir de sus veredictos, y que cada respuesta del chat quede agendada y visible en GET …/metricas.
"""
from __future__ import annotations

import asyncio

import pytest

from conftest import token
from services import juez_fable
from shared.db.core.config import settings
from shared.models.rag_evaluacion import RagMetricaJuez
from shared.models.rag_log import RagLog

ANA = token(2)


def _llamar(referencia: dict, veredictos: dict, preguntas: dict | None = None):
    """Juez falso: responde según el esquema pedido y guarda los prompts."""
    llamadas: list[tuple[str, str]] = []

    async def llamar(prompt, esquema, esfuerzo):  # noqa: ANN001
        llamadas.append((prompt, esfuerzo))
        meta = {"modelo": "claude-fable-5-2", "fallback": False, "uso": {"entrada": 10, "salida": 5}}
        if esquema is juez_fable.ESQUEMA_REFERENCIA:
            return referencia, meta
        if esquema is juez_fable.ESQUEMA_VEREDICTOS:
            return veredictos, meta
        return preguntas or {"preguntas": ["¿cuántos trabajan?"] * 3, "evasiva": False}, meta

    llamar.llamadas = llamadas
    return llamar


def _embeber(textos):  # noqa: ANN001 — todo apunta al mismo lado: relevancia 1
    return [[1.0, 0.0] for _ in textos]


def test_formulas_de_las_cinco_metricas_con_referencia():
    # 3 contextos; referencia de 2 afirmaciones: R1 sale del contexto 1, R2 de ninguno (la recuperación la perdió).
    # Respuesta: A1 correcta y apoyada en C1; A2 incorrecta pero apoyada en C1 (relevante) → ruido;
    # A3 incorrecta apoyada solo en C3 (irrelevante); A4 sin apoyo.
    veredictos = {
        "afirmaciones_respuesta": [
            {"texto": "A1", "contextos": [1], "en_referencia": True},
            {"texto": "A2", "contextos": [1], "en_referencia": False},
            {"texto": "A3", "contextos": [3], "en_referencia": False},
            {"texto": "A4", "contextos": [], "en_referencia": False},
        ],
        "afirmaciones_referencia": [{"n": 1, "contextos": [1], "en_respuesta": True},
                                    {"n": 2, "contextos": [], "en_respuesta": False}],
        "contextos": [{"n": 1, "util": True, "razon": ""}, {"n": 2, "util": False, "razon": ""},
                      {"n": 3, "util": True, "razon": ""}],
    }
    p, d = juez_fable.calcular(veredictos, 3, 2)
    assert p["precision_contexto"] == pytest.approx((1 + 2 / 3) / 2)  # [1, 0, 1]
    assert p["fidelidad"] == pytest.approx(3 / 4)
    assert p["recuerdo_contexto"] == pytest.approx(1 / 2)
    # VP 1, FP 3, FN 1 → P 0.25, R 0.5, F1 1/3
    assert p["correccion_factual"] == pytest.approx(1 / 3)
    assert d["correccion_precision"] == 0.25 and d["correccion_recuerdo"] == 0.5
    assert p["sensibilidad_ruido"] == pytest.approx(1 / 4)  # solo A2
    assert d["sensibilidad_ruido_irrelevante"] == pytest.approx(0.25)  # solo A3
    assert d["no_sustentadas"] == ["A4"] and d["incorrectas"] == ["A2", "A3", "A4"]
    assert d["referencia_no_cubierta"] == [2] and d["referencia_sin_contexto"] == [2]


def test_sin_referencia_solo_se_calculan_las_metricas_que_no_la_necesitan():
    veredictos = {"afirmaciones_respuesta": [{"texto": "A1", "contextos": [1], "en_referencia": False}],
                  "afirmaciones_referencia": [], "contextos": [{"n": 1, "util": True, "razon": ""}]}
    p, _ = juez_fable.calcular(veredictos, 1, 0)
    assert p["fidelidad"] == 1.0 and p["precision_contexto"] == pytest.approx(1.0)
    assert p["recuerdo_contexto"] is None and p["correccion_factual"] is None and p["sensibilidad_ruido"] is None


def test_numeros_de_contexto_fuera_de_rango_se_ignoran():
    veredictos = {"afirmaciones_respuesta": [{"texto": "A1", "contextos": [7, 0], "en_referencia": True}],
                  "afirmaciones_referencia": [], "contextos": []}
    p, _ = juez_fable.calcular(veredictos, 2, 0)
    assert p["fidelidad"] == 0.0 and p["precision_contexto"] == pytest.approx(0.0)


def test_evaluar_completo_la_referencia_no_ve_la_respuesta_y_la_relevancia_es_cero_si_evade():
    llamar = _llamar(
        {"suficiente": True, "respuesta_referencia": "Trabajan 12 de 40.", "afirmaciones": ["Trabajan 12 de 40."]},
        {"afirmaciones_respuesta": [{"texto": "Trabajan 12 de 40.", "contextos": [1], "en_referencia": True}],
         "afirmaciones_referencia": [{"n": 1, "contextos": [1], "en_respuesta": True}],
         "contextos": [{"n": 1, "util": True, "razon": "trae la cifra"}]},
        {"preguntas": ["a", "b", "c"], "evasiva": True},
    )
    usados = [{"tipo": "resultado", "texto": "Cumplen la condición 12 de 40 respondentes."}]
    ampliado = [{"tipo": "ampliado", "etiqueta": "127 pregunta", "texto": "p03 ¿Trabajas?"}]
    m = asyncio.run(juez_fable.evaluar("¿cuántos trabajan?", "RESPUESTA-DEL-SISTEMA 12 de 40", usados, ampliado,
                                       llamar, _embeber))
    assert m["estado"] == "listo" and m["fidelidad"] == 1.0 and m["recuerdo_contexto"] == 1.0
    assert m["correccion_factual"] == 1.0 and m["sensibilidad_ruido"] == 0.0 and m["precision_contexto"] == 1.0
    assert m["relevancia"] == 0.0  # evasiva
    assert m["modelo_real"] == "claude-fable-5-2" and m["fallback"] is False and m["uso"]["entrada"] == 30
    prompt_ref = next(p for p, _ in llamar.llamadas if "respuesta de REFERENCIA" in p)
    assert "RESPUESTA-DEL-SISTEMA" not in prompt_ref and "p03 ¿Trabajas?" in prompt_ref
    prompt_ver = next(p for p, _ in llamar.llamadas if "AFIRMACIONES DE REFERENCIA" in p)
    assert "p03 ¿Trabajas?" not in prompt_ver  # el contexto ampliado no cuenta como recuperado
    assert {e for _, e in llamar.llamadas} == {settings.RAG_JUEZ_FABLE_ESFUERZO, "low"}


def test_referencia_insuficiente_deja_motivo():
    llamar = _llamar({"suficiente": False, "respuesta_referencia": "No hay datos.", "afirmaciones": ["x"]},
                     {"afirmaciones_respuesta": [], "afirmaciones_referencia": [], "contextos": []})
    m = asyncio.run(juez_fable.evaluar("p", "r", [], [], llamar, _embeber))
    assert m["recuerdo_contexto"] is None and "referencia" in m["motivo"]
    assert m["detalle"]["referencia"]["afirmaciones"] == []


# ── Integración con el chat ────────────────────────────────────────────────────


@pytest.fixture()
def con_fable(db, chroma, monkeypatch):
    """Un instrumento indexado y el juez Fable encendido con clave falsa; la cola se registra en vez de ejecutarse."""
    from shared.models.usuario import Usuario

    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.commit()
    col = chroma.crear("instrumentos")
    col.agregar("a-0", "compromiso académico de los estudiantes", {"instrumentoId": "1", "seccion": "pregunta", "titulo": "A"})
    col.agregar("a-1", "horas de estudio por semana", {"instrumentoId": "1", "seccion": "pregunta", "titulo": "A"})
    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)
    monkeypatch.setattr(settings, "RAG_JUEZ_FABLE", True)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "clave-de-pruebas")
    monkeypatch.setattr(settings, "RAG_ZONA_GRIS_MAX", 0.0)
    programadas: list[int] = []
    monkeypatch.setattr(juez_fable, "programar", lambda rag_log_id, fabrica: programadas.append(rag_log_id))
    from services import evaluacion

    monkeypatch.setattr(evaluacion, "programar", lambda *a, **k: None)
    return programadas


def test_cada_respuesta_se_evalua_sola_y_se_ve_en_las_metricas(cliente, con_fable, fabrica):
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    assert con_fable == [r["consultaId"]]
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["juezFable"]["estado"] == "calculando" and m["juezFable"]["modelo"] == "claude-fable-5-2"

    llamar = _llamar(
        {"suficiente": True, "respuesta_referencia": "Hay compromiso.", "afirmaciones": ["Hay compromiso académico."]},
        {"afirmaciones_respuesta": [{"texto": "Hay compromiso académico.", "contextos": [1], "en_referencia": True}],
         "afirmaciones_referencia": [{"n": 1, "contextos": [1], "en_respuesta": True}],
         "contextos": [{"n": 1, "util": True, "razon": "lo dice"}]},
        {"preguntas": ["compromiso académico"] * 3, "evasiva": False},
    )
    asyncio.run(juez_fable.evaluar_consulta(r["consultaId"], fabrica, llamar))
    j = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()["juezFable"]
    assert j["estado"] == "listo" and j["fidelidad"] == 1.0 and j["recuerdoContexto"] == 1.0
    assert j["correccionFactual"] == 1.0 and j["sensibilidadRuido"] == 0.0 and j["relevancia"] == pytest.approx(1.0, abs=1e-3)
    assert j["respuestaReferencia"] == "Hay compromiso." and j["origenReferencia"] in ("contexto_ampliado", "solo_contexto_usado")

    # Volver a pedirla no la duplica mientras está lista, salvo con ?juez=<modelo Fable> (fuerza).
    cliente.post(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA)
    assert con_fable == [r["consultaId"]]
    cliente.post(f"/rag/consultas/{r['consultaId']}/metricas?juez=claude-fable-5-2", headers=ANA)
    assert con_fable == [r["consultaId"], r["consultaId"]]


def test_rechazos_no_pasan_por_el_juez_fable(cliente, con_fable):
    r = cliente.post("/rag/chat", json={"pregunta": "¿Cuál es el nombre del respondente R017?", "stream": False},
                     headers=ANA).json()
    assert con_fable == []
    assert cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()["juezFable"] is None


def test_sin_clave_queda_omitida_con_el_motivo(cliente, con_fable, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    j = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()["juezFable"]
    assert con_fable == [] and j["estado"] == "omitida" and "ANTHROPIC_API_KEY" in j["motivo"]


def test_un_error_del_juez_queda_guardado(fabrica):
    s = fabrica()
    s.add(RagLog(pregunta="p", respuesta="r", contexto_usado=[{"tipo": "resultado", "texto": "c"}],
                 metricas={"estado": "listo"}))
    s.commit()
    rag_log_id = s.query(RagLog).one().rag_log_id

    async def llamar(prompt, esquema, esfuerzo):  # noqa: ANN001
        raise juez_fable.RechazoJuez("El juez declinó evaluar (cyber).")

    asyncio.run(juez_fable.evaluar_consulta(rag_log_id, fabrica, llamar))
    fila = s.query(RagMetricaJuez).one()
    s.refresh(fila)
    assert fila.modelo_juez == "claude-fable-5-2" and fila.metricas["estado"] == "error" and "cyber" in fila.metricas["motivo"]
