"""Métricas automáticas por respuesta (tipo RAGAS): fórmulas, segundo plano y endpoint.

El juez se reemplaza por respuestas fijas para verificar las FÓRMULAS (las mismas de
RAGAS 0.4.3); la calidad del juez real se mide fuera de línea (tools/rag/evaluar_ragas.py).
"""
from __future__ import annotations

import asyncio

import pytest

from shared.models.rag_log import RagLog
from shared.models.usuario import Usuario

from conftest import token
from services import evaluacion

ANA = token(2)


def _juez(respuestas: dict[str, dict]):  # noqa: ANN001
    """Juez falso: elige la respuesta por una palabra clave del prompt."""
    llamadas: list[str] = []

    async def juez(prompt: str):  # noqa: ANN001
        llamadas.append(prompt)
        for clave, datos in respuestas.items():
            if clave in prompt:
                return datos
        return None

    juez.llamadas = llamadas
    return juez


def test_precision_media_igual_que_ragas():
    # Ejemplo de la documentación de RAGAS: [1, 0, 1] ≈ 0.833; el irrelevante primero baja el puntaje.
    assert evaluacion.precision_media([1, 1]) == pytest.approx(1.0)
    assert evaluacion.precision_media([1, 0, 1]) == pytest.approx((1 + 2 / 3) / 2)
    assert evaluacion.precision_media([0, 1]) == pytest.approx(0.5)
    assert evaluacion.precision_media([0, 0]) == pytest.approx(0.0)


def test_fidelidad_afirmaciones_sustentadas_entre_total():
    juez = _juez({
        "Divide la RESPUESTA": {"afirmaciones": ["El 13.3 % está de acuerdo.", "Son 4 de 30.", "Es el turno matutino."]},
        "AFIRMACIONES:": {"veredictos": [{"veredicto": 1}, {"veredicto": 1}, {"veredicto": 0}]},
    })
    valor, detalle = asyncio.run(evaluacion.fidelidad("¿% vespertino?", "…", ["13.3 % (4 de 30) del turno vespertino"], juez))
    assert valor == pytest.approx(2 / 3) and detalle["no_sustentadas"] == ["Es el turno matutino."]


def test_fidelidad_sin_afirmaciones_es_none_y_veredictos_incompletos_fallan():
    assert asyncio.run(evaluacion.fidelidad("p", "r", ["c"], _juez({})))[0] is None
    juez = _juez({"Divide la RESPUESTA": {"afirmaciones": ["a", "b"]}, "AFIRMACIONES:": {"veredictos": [{"veredicto": 1}]}})
    with pytest.raises(ValueError):
        asyncio.run(evaluacion.fidelidad("p", "r", ["c"], juez))


def test_relevancia_coseno_medio_y_cero_si_es_evasiva():
    def embeber(textos):  # noqa: ANN001  la pregunta original = [1, 0]
        return [[1.0, 0.0] if i == 0 else ([1.0, 0.0] if "porcentaje" in t else [0.0, 1.0]) for i, t in enumerate(textos)]

    juez = _juez({"RESPUESTA:": {"pregunta": "¿Qué porcentaje está de acuerdo?", "evasiva": False}})
    valor, detalle = asyncio.run(evaluacion.relevancia("¿qué porcentaje?", "El 13.3 %…", juez, embeber))
    assert valor == pytest.approx(1.0) and len(detalle["preguntas_generadas"]) == 3 and len(juez.llamadas) == 3
    evasiva = _juez({"RESPUESTA:": {"pregunta": "¿Qué porcentaje está de acuerdo?", "evasiva": True}})
    assert asyncio.run(evaluacion.relevancia("¿qué porcentaje?", "No lo sé.", evasiva, embeber))[0] == 0.0


def test_precision_de_contexto_por_fragmento_en_orden():
    juez = _juez({"CONTEXTO: util": {"veredicto": 1}, "CONTEXTO: ruido": {"veredicto": 0}})
    valor, detalle = asyncio.run(evaluacion.precision_contexto("p", "r", ["ruido", "util"], juez))
    assert detalle["utiles"] == [0, 1] and valor == pytest.approx(0.5)


def test_evaluar_una_metrica_fallida_no_tumba_las_demas():
    juez = _juez({
        "Divide la RESPUESTA": {"afirmaciones": ["a", "b"]},
        "AFIRMACIONES:": {"veredictos": [{"veredicto": 1}]},  # incompleto → fidelidad falla
        "Escribe UNA pregunta": {"pregunta": "¿x?", "evasiva": False},
        "sirvió para llegar": {"veredicto": 1},
    })
    m = asyncio.run(evaluacion.evaluar("¿x?", "r", ["c"], juez, lambda t: [[1.0, 0.0] for _ in t]))
    assert m["estado"] == "listo" and m["fidelidad"] is None and "error" in m["detalle"]["fidelidad"]
    assert m["relevancia"] == 1.0 and m["precision_contexto"] == 1.0


# ── Integración con el chat ────────────────────────────────────────────────────


@pytest.fixture()
def con_chat(db, chroma, monkeypatch):
    from shared.db.core.config import settings

    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.commit()
    col = chroma.crear("instrumentos")
    col.agregar("a-0", "compromiso académico de los estudiantes", {"instrumentoId": "1", "seccion": "pregunta", "titulo": "A"})
    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)
    monkeypatch.setattr(settings, "RAG_ZONA_GRIS_MAX", 0.0)
    programadas: list[int] = []
    monkeypatch.setattr(evaluacion, "programar", lambda rag_log_id, fabrica: programadas.append(rag_log_id))
    return programadas


def test_la_respuesta_se_entrega_y_las_metricas_quedan_calculando(cliente, con_chat, db, fabrica, monkeypatch):
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    assert con_chat == [r["consultaId"]]
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "calculando" and m["fidelidad"] is None

    # El trabajador en segundo plano calcula y guarda (juez falso).
    async def juez(prompt):  # noqa: ANN001
        if "Divide la RESPUESTA" in prompt:
            return {"afirmaciones": ["Hay compromiso académico."]}
        if "AFIRMACIONES:" in prompt:
            return {"veredictos": [{"veredicto": 1}]}
        if "Escribe UNA pregunta" in prompt:
            return {"pregunta": "compromiso académico", "evasiva": False}
        return {"veredicto": 1}

    monkeypatch.setattr(evaluacion, "_juez_ollama", juez)
    asyncio.run(evaluacion._evaluar_consulta(r["consultaId"], fabrica))
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "listo" and m["fidelidad"] == 1.0 and m["precisionContexto"] == 1.0
    assert m["relevancia"] == pytest.approx(1.0, abs=1e-3) and m["modeloJuez"] and m["fecha"]
    detalle = cliente.get(f"/rag/consultas/{r['consultaId']}", headers=ANA).json()
    assert detalle["contexto"][0]["texto"] == "compromiso académico de los estudiantes"


def test_rechazos_no_se_evaluan(cliente, con_chat):
    r = cliente.post("/rag/chat", json={"pregunta": "¿Cuál es el nombre del respondente R017?", "stream": False}, headers=ANA).json()
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "omitida" and con_chat == []


def test_metricas_desactivadas(cliente, con_chat, monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_METRICAS", False)
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "omitida" and "desactivadas" in m["motivo"] and con_chat == []
    assert cliente.get("/rag/consultas/9999/metricas", headers=ANA).status_code == 404


def test_rag_log_guarda_metricas_y_juez(fabrica):
    s = fabrica()
    s.add(RagLog(pregunta="p", respuesta="r", metricas={"estado": "listo", "fidelidad": 0.5}, modelo_juez="llama3.2:3b"))
    s.commit()
    assert s.query(RagLog).one().metricas["fidelidad"] == 0.5


def test_veredictos_por_numero_o_por_posicion():
    assert evaluacion.veredictos_por_numero([{"n": 2, "veredicto": 0}, {"n": 1, "veredicto": 1}], 2) == [1, 0]
    assert evaluacion.veredictos_por_numero([{"veredicto": "1"}, {"veredicto": 0}], 2) == [1, 0]
    with pytest.raises(ValueError):
        evaluacion.veredictos_por_numero([{"veredicto": 1}], 2)
