"""Indicadores del sistema por respuesta (sin juez) y evaluación con varios jueces (experimento redactor × juez)."""
from __future__ import annotations

import asyncio

import pytest

from shared.models.rag_evaluacion import RagMetricaJuez
from shared.models.rag_log import RagLog
from shared.models.usuario import Usuario

from conftest import token
from services import evaluacion, indicadores

ANA = token(2)
_CONTEXTO = [{"texto": "Cumplen la condición 486 de 2000 respondentes (24.3 %). Respondentes: R001."}]


def _fila(**campos) -> RagLog:
    base = {"pregunta": "¿cuántos llevan carga máxima?", "decision_dominio": "dentro", "ruta": "estructurada",
            "motivo": "plan:conteo_porcentaje", "contexto_usado": _CONTEXTO, "metricas": evaluacion.pendiente(False),
            "plan": {"plan": {"intencion": "conteo_porcentaje"}}}
    return RagLog(**{**base, **campos})


def test_redaccion_con_cifra_e_id_inventados_y_una_regeneracion():
    fila = _fila(respuesta="Cumplen 486 de 2000 (cerca del 25 %), entre ellos R017.",
                 plan={"plan": {"intencion": "conteo_porcentaje"},
                       "verificacion": {"intentos": 2, "primer_fallo": "negativa_corregida", "resultado": "regenerada"}},
                 tiempos={"interpretacion": 3821, "ejecucion": 94, "redaccion": 4098, "verificacion": 2223},
                 latencia_ms=10300, modelo_usado="llama3.2:3b")
    i = indicadores.calcular(fila)
    assert i["respuesta"] == "redactada" and i["plantilla"] is None and i["intencion"] == "conteo_porcentaje"
    assert (i["cifrasTotal"], i["cifrasConRespaldo"], i["cifrasSinRespaldo"]) == (3, 2, ["25"])
    assert i["idsInventados"] == ["R017"]
    assert i["regeneraciones"] == 1 and i["primerFallo"] == "negativa_corregida"
    assert i["tiempos"]["redaccion"] == 4098 and i["modelo"] == "llama3.2:3b"


def test_redaccion_fiel_tiene_todas_las_cifras_con_respaldo():
    i = indicadores.calcular(_fila(respuesta="Llevan carga máxima 486 de 2000 respondentes (24.3 %).",
                                   plan={"plan": {"intencion": "conteo_porcentaje"},
                                         "verificacion": {"intentos": 1, "resultado": "aceptada"}}))
    assert (i["cifrasTotal"], i["cifrasConRespaldo"], i["idsInventados"], i["regeneraciones"]) == (3, 3, [], 0)


def test_aclaracion_convertida_en_fuera_de_dominio_es_plantilla():
    """Caso 5 de las pruebas (rag_log 1302): el anclaje armó la aclaración, pero salió el mensaje de fuera."""
    i = indicadores.calcular(_fila(respuesta="Solo puedo responder sobre los instrumentos…", decision_dominio="fuera",
                                   ruta=None, motivo="plan:aclaracion_ajena", contexto_usado=[],
                                   metricas=evaluacion.omitida("rechazo"),
                                   plan={"plan": {"intencion": "aclaracion"}}))
    assert i["respuesta"] == "plantilla" and i["plantilla"] == "aclaracion_ajena" and "fuera de dominio" in i["plantillaDetalle"]
    assert i["cifrasTotal"] is None and i["idsInventados"] == []


@pytest.mark.parametrize(("campos", "esperada"), [
    ({"decision_dominio": "privacidad"}, "privacidad"),
    ({"decision_dominio": "manipulacion"}, "manipulacion"),
    ({"ruta": "ayuda", "decision_dominio": "ayuda"}, "ayuda"),
    ({"ruta": "aclaracion"}, "aclaracion"),
    ({"salida": {"degradado": True}}, "modelo_no_disponible"),
    ({"plan": {"plan": {"intencion": "hallazgo"}, "verificacion": {"intentos": 2, "resultado": "respaldo"}}}, "calculo_literal"),
])
def test_tipos_de_plantilla(campos, esperada):
    assert indicadores.calcular(_fila(respuesta="x", **campos))["plantilla"] == esperada


def test_presentacion_fija_del_calculo_no_es_plantilla():
    i = indicadores.calcular(_fila(respuesta="Respuestas interpretadas de R001…", metricas=evaluacion.pendiente(True),
                                   plan={"plan": {"intencion": "datos_respondente"}}))
    assert i["respuesta"] == "presentacion_fija" and i["plantilla"] is None and i["cifrasTotal"] is None


# ── Varios jueces sobre la misma respuesta ─────────────────────────────────────


def _juez_que_aprueba(modelos: list[str]):
    async def juez(prompt, modelo=None):  # noqa: ANN001
        modelos.append(modelo)
        if "Divide la RESPUESTA" in prompt:
            return {"afirmaciones": ["Llevan carga máxima 486 de 2000."]}
        if "AFIRMACIONES:" in prompt:
            return {"veredictos": [{"veredicto": 1}]}
        if "Escribe UNA pregunta" in prompt:
            return {"pregunta": "¿cuántos llevan carga máxima?", "evasiva": False}
        return {"veredicto": 1}

    return juez


def test_otro_juez_guarda_su_evaluacion_aparte_sin_tocar_la_de_la_interfaz(fabrica, chroma, monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_JUEZ_MODELO", "qwen2.5:3b")
    s = fabrica()
    s.add(_fila(respuesta="Llevan carga máxima 486 de 2000 (24.3 %)."))
    s.commit()
    fila = s.query(RagLog).one()
    programadas: list[tuple] = []
    monkeypatch.setattr(evaluacion, "programar", lambda i, f, modelo_juez=None: programadas.append((i, modelo_juez)))

    evaluacion.solicitar(fila, s, fabrica, "llama3.2:3b")
    evaluacion.solicitar(fila, s, fabrica, "llama3.2:3b")  # pedirlo dos veces no lo duplica
    assert programadas == [(fila.rag_log_id, "llama3.2:3b")]
    assert s.query(RagMetricaJuez).one().metricas["estado"] == "calculando"
    assert fila.metricas["estado"] == "pendiente"  # la del juez por defecto sigue esperando el botón

    modelos: list[str] = []
    monkeypatch.setattr(evaluacion, "_juez_ollama", _juez_que_aprueba(modelos))
    asyncio.run(evaluacion._evaluar_consulta(fila.rag_log_id, fabrica, "llama3.2:3b"))
    asyncio.run(evaluacion._evaluar_consulta(fila.rag_log_id, fabrica))  # juez por defecto
    assert set(modelos) == {"llama3.2:3b", "qwen2.5:3b"}

    s2 = fabrica()
    jueces = {j["modeloJuez"]: j for j in evaluacion.jueces_de(s2, fila.rag_log_id)}
    assert set(jueces) == {"llama3.2:3b", "qwen2.5:3b"}
    assert jueces["llama3.2:3b"]["estado"] == "listo" and jueces["llama3.2:3b"]["fidelidad"] == 1.0
    guardada = s2.get(RagLog, fila.rag_log_id)
    assert guardada.metricas["estado"] == "listo" and guardada.modelo_juez == "qwen2.5:3b"


def test_respuesta_calculada_sigue_fiel_por_construccion_con_cualquier_juez(fabrica, chroma, monkeypatch):
    s = fabrica()
    s.add(_fila(respuesta="Cumplen la condición 486 de 2000 respondentes (24.3 %).", metricas=evaluacion.pendiente(True)))
    s.commit()
    rid = s.query(RagLog).one().rag_log_id
    modelos: list[str] = []
    monkeypatch.setattr(evaluacion, "_juez_ollama", _juez_que_aprueba(modelos))
    asyncio.run(evaluacion._evaluar_consulta(rid, fabrica))
    asyncio.run(evaluacion._evaluar_consulta(rid, fabrica, "gemma3:4b"))
    jueces = {j["modeloJuez"]: j for j in evaluacion.jueces_de(fabrica(), rid)}
    assert jueces["gemma3:4b"]["estado"] == "calculada" and jueces["gemma3:4b"]["fidelidad"] == 1.0


def test_respuestas_omitidas_no_se_evaluan_con_otro_juez(fabrica, monkeypatch):
    s = fabrica()
    s.add(_fila(respuesta="Solo puedo responder…", metricas=evaluacion.omitida("rechazo")))
    s.commit()
    programadas: list = []
    monkeypatch.setattr(evaluacion, "programar", lambda *a, **k: programadas.append(a))
    evaluacion.solicitar(s.query(RagLog).one(), s, fabrica, "llama3.2:3b")
    assert programadas == [] and s.query(RagMetricaJuez).count() == 0


# ── Endpoint: indicadores y calificación humana ────────────────────────────────


def test_endpoint_devuelve_indicadores_y_guarda_la_calificacion(cliente, db, monkeypatch):
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.add(_fila(respuesta="Llevan carga máxima 486 de 2000 (24.3 %)."))
    db.commit()
    rid = db.query(RagLog).one().rag_log_id

    m = cliente.get(f"/rag/consultas/{rid}/metricas", headers=ANA).json()
    assert m["indicadores"]["respuesta"] == "redactada" and m["indicadores"]["cifrasConRespaldo"] == 3
    assert m["calificacion"] is None and m["jueces"] == []

    r = cliente.put(f"/rag/consultas/{rid}/calificacion", headers=ANA,
                    json={"calificacion": 1, "entendio": True, "fundamenta": None, "comentario": "  falta el 24.3 %  "})
    assert r.status_code == 200 and r.json()["comentario"] == "falta el 24.3 %"
    cliente.put(f"/rag/consultas/{rid}/calificacion", headers=ANA, json={"calificacion": 2, "entendio": True})
    m = cliente.get(f"/rag/consultas/{rid}/metricas", headers=ANA).json()
    assert m["calificacion"]["calificacion"] == 2 and m["calificacion"]["comentario"] is None

    assert cliente.put(f"/rag/consultas/{rid}/calificacion", headers=ANA, json={"calificacion": 3}).status_code == 422
    assert cliente.put("/rag/consultas/9999/calificacion", headers=ANA, json={"calificacion": 1}).status_code == 404


def test_endpoint_pide_metricas_con_otro_juez(cliente, db, monkeypatch):
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.add(_fila(respuesta="Llevan carga máxima 486 de 2000 (24.3 %)."))
    db.commit()
    rid = db.query(RagLog).one().rag_log_id
    programadas: list = []
    monkeypatch.setattr(evaluacion, "programar", lambda i, f, modelo_juez=None: programadas.append((i, modelo_juez)))
    m = cliente.post(f"/rag/consultas/{rid}/metricas?juez=gemma3:4b", headers=ANA).json()
    assert programadas == [(rid, "gemma3:4b")]
    assert m["estado"] == "pendiente" and m["jueces"][0]["modeloJuez"] == "gemma3:4b"
    assert m["jueces"][0]["estado"] == "calculando"
