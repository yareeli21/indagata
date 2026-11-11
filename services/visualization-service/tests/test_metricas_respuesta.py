"""Métricas de cada respuesta para «Ver métricas» (services/metricas_respuesta.py): deterministas, sin juez."""
from __future__ import annotations

from types import SimpleNamespace

from services import metricas_respuesta as m

CONTEXTO = [
    "Pregunta p03: ¿En qué modalidad cursas tu programa? Presencial 64.2 %, Mixta/híbrida 22.3 %, En línea 13.5 %.",
    "Participante E02, pregunta p01: Soy el primero de mi familia en ir a la universidad y hay mucha presión.",
]


def test_fundamentacion_cuenta_las_oraciones_respaldadas():
    respuesta = ("La mayoría cursa su programa en modalidad presencial (64.2 %) [Fuente 1]. "
                 "E02 cuenta que es el primero de su familia en ir a la universidad y siente presión [Fuente 2]. "
                 "Los docentes deberían organizar talleres de liderazgo comunitario regional.")
    f = m.fundamentacion(respuesta, CONTEXTO)
    assert (f["oraciones"], f["respaldadas"]) == (3, 2)
    assert f["proporcion"] == round(2 / 3, 3)
    assert f["sinRespaldo"] == ["Los docentes deberían organizar talleres de liderazgo comunitario regional."]


def test_las_tablas_del_calculo_no_se_cuentan():
    respuesta = "La modalidad presencial predomina entre quienes cursan el programa [Fuente 1].\n| Opción | % |\n|---|---|"
    assert m.fundamentacion(respuesta, CONTEXTO)["oraciones"] == 1


def test_citas_y_citas_a_fuentes_que_no_existen():
    respuesta = ("La mayoría cursa su programa en modalidad presencial [Fuente 1]. "
                 "E02 cuenta que es el primero de su familia en ir a la universidad [Fuente 4]. "
                 "Esto sugiere que hace falta acompañamiento durante el primer año universitario.")
    c = m.citas(respuesta, {1, 2})
    assert (c["oraciones"], c["conCita"]) == (3, 2)
    assert c["fuentesCitadas"] == [1, 4] and c["citasInvalidas"] == [4]


def test_recuperacion_dice_por_que_paso_cada_fragmento(monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.65)
    monkeypatch.setattr(settings, "RAG_MIN_COBERTURA", 0.75)
    fila = SimpleNamespace(score_max=0.74, contexto_usado=[
        {"tipo": "resultado", "texto": "[Fuente 1] …"},
        {"tipo": "fragmento", "etiqueta": "p03", "instrumentoId": "117", "score": 0.46, "coincidencia": 1.0,
         "palabras": 3, "rangos": {"semantica": None, "palabras": 1}, "texto": CONTEXTO[0]},
        {"tipo": "fragmento", "etiqueta": "E02 en p01", "instrumentoId": "114", "score": 0.74, "coincidencia": 1.0,
         "palabras": 2, "rangos": {"semantica": 1, "palabras": 2}, "texto": CONTEXTO[1]},
    ])
    r = m.recuperacion(fila)
    assert r["modo"] == "hibrida" and r["umbral"] == 0.65
    assert [f["paso"] for f in r["fragmentos"]] == ["palabras", "ambos"]
    assert r["fragmentos"][0]["rangoPalabras"] == 1 and r["fragmentos"][0]["rangoSemantico"] is None
    assert r["similitudMaxima"] == 0.74 and r["similitudPromedio"] == 0.6


def test_un_calculo_presentado_tal_cual_no_se_fundamenta():
    fila = SimpleNamespace(score_max=1.0, contexto_usado=[], respuesta="Cumplen 44 de 180.", salida={"fuentes": []})
    salida = m.calcular(fila, respuesta_redactada=False)
    assert salida["fundamentacion"] is None and salida["citas"] is None
    assert salida["recuperacion"]["similitudMaxima"] is None  # 1.0 es el marcador de las rutas calculadas


def test_una_cita_sola_al_final_cuenta_para_la_oracion_anterior():
    respuesta = "La mayoría cursa su programa en modalidad presencial, con 64.2 %.\n\n[ Fuente 1 ]"
    c = m.citas(respuesta, {1})
    assert (c["oraciones"], c["conCita"]) == (1, 1)
