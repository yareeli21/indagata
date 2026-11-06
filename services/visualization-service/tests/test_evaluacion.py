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


def test_fidelidad_sin_afirmaciones_es_none_y_veredictos_incompletos_se_evaluan_uno_por_uno():
    """28 oct (Fase 4): con un veredicto de menos la fidelidad quedaba vacía («—»); ahora se reintenta y, si el
    juez insiste, se evalúa cada afirmación por separado."""
    assert asyncio.run(evaluacion.fidelidad("p", "r", ["c"], _juez({})))[0] is None
    juez = _juez({"Divide la RESPUESTA": {"afirmaciones": ["a", "b"]}, "AFIRMACIONES:": {"veredictos": [{"veredicto": 1}]},
                  "AFIRMACIÓN: a": {"veredicto": 1}, "AFIRMACIÓN: b": {"veredicto": 0}})
    valor, detalle = asyncio.run(evaluacion.fidelidad("p", "r", ["c"], juez))
    assert valor == 0.5 and detalle["modo"] == "una_por_una" and detalle["no_sustentadas"] == ["b"]
    assert sum("AFIRMACIONES:" in l for l in juez.llamadas) == 2


def test_cifras_sin_sustento_sin_juez():
    contexto = ["Cumplen la condición 382 de 2000 respondentes (19.1 %). [Fuente 1] p03 R002"]
    assert evaluacion.cifras_sin_sustento("Son 382 de 2000 (19,1 %) en p03, R002 [Fuente 1].", contexto) == []
    assert evaluacion.cifras_sin_sustento("Son 13 %, unas 11 personas.", contexto) == ["13", "11"]


def test_respuesta_calculada_mide_relevancia_y_precision_con_fidelidad_por_construccion():
    juez = _juez({"Escribe UNA pregunta": {"pregunta": "¿x?", "evasiva": False}, "se usó para escribir la RESPUESTA": {"veredicto": 1}})
    m = asyncio.run(evaluacion.evaluar("¿x?", "382 de 2000", ["382 de 2000"], juez, lambda t: [[1.0, 0.0] for _ in t],
                                       calculada=True))
    assert m["estado"] == "calculada" and m["fidelidad"] == 1.0 and m["relevancia"] == 1.0 and m["precision_contexto"] == 1.0
    assert not any("Divide la RESPUESTA" in l for l in juez.llamadas)


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
    base = _juez({"Escribe UNA pregunta": {"pregunta": "¿x?", "evasiva": False}, "se usó para escribir la RESPUESTA": {"veredicto": 1}})

    async def juez(prompt: str):  # noqa: ANN001
        if "Divide la RESPUESTA" in prompt:
            raise RuntimeError("juez caído")
        return await base(prompt)

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
    monkeypatch.setattr(evaluacion, "programar", lambda rag_log_id, fabrica, modelo_juez=None: programadas.append(rag_log_id))
    return programadas


def test_la_respuesta_se_entrega_y_las_metricas_quedan_calculando(cliente, con_chat, db, fabrica, monkeypatch):
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    assert con_chat == [r["consultaId"]]
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "calculando" and m["fidelidad"] is None

    # El trabajador en segundo plano calcula y guarda (juez falso).
    async def juez(prompt, modelo=None):  # noqa: ANN001
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


def test_afirmacion_copiada_del_contexto_cuenta_como_sustentada_aunque_el_juez_diga_que_no():
    contexto = ["- Dato 1: La pregunta con más respuestas en el nivel bajo es p05 «¿Con qué frecuencia te ha tocado un "
                "cambio de profesor?»: 57.8 % de quienes respondieron (respondieron «Nunca» o «Rara vez»)."]
    copiada = "57.8% de quienes respondieron a esta pregunta (respondieron 'Nunca' o 'Rara vez')"
    inventada = "La mayoría de los estudiantes cambió de profesor varias veces."
    otra_cifra = "61.2% de quienes respondieron (respondieron 'Nunca' o 'Rara vez')"
    assert evaluacion.sustento_literal(copiada, contexto)
    assert not evaluacion.sustento_literal(inventada, contexto) and not evaluacion.sustento_literal(otra_cifra, contexto)
    juez = _juez({"Divide la RESPUESTA": {"afirmaciones": [copiada, inventada]},
                  "AFIRMACIONES:": {"veredictos": [{"n": 1, "veredicto": 0}, {"n": 2, "veredicto": 0}]}})
    valor, detalle = asyncio.run(evaluacion.fidelidad("p", "r", contexto, juez))
    assert valor == 0.5 and detalle["sustento_literal"] == 1 and detalle["no_sustentadas"] == [inventada]



def test_bajo_demanda_la_respuesta_queda_pendiente_y_se_calcula_al_pedirla(cliente, con_chat, monkeypatch):
    """28 oct: evaluar cada respuesta recargaba el modelo en la GPU de 4 GiB (31–38 s por pregunta)."""
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_METRICAS_BAJO_DEMANDA", True)
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso académico", "stream": False}, headers=ANA).json()
    m = cliente.get(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "pendiente" and m["fidelidad"] is None and con_chat == []
    m = cliente.post(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "calculando" and con_chat == [r["consultaId"]]
    cliente.post(f"/rag/consultas/{r['consultaId']}/metricas", headers=ANA)  # pedirla dos veces no la duplica
    assert con_chat == [r["consultaId"]]


def test_bajo_demanda_respuesta_calculada_trae_la_fidelidad_y_espera_lo_demas(fabrica):
    s = fabrica()
    s.add(RagLog(pregunta="p", respuesta="r", metricas=evaluacion.pendiente(calculada=True)))
    s.commit()
    publico = evaluacion.estado_publico(s.query(RagLog).one())
    assert publico["estado"] == "pendiente" and publico["fidelidad"] == 1.0 and publico["relevancia"] is None
