"""Trazabilidad de las fuentes del chat: pasajes por tarjeta y documento indexado navegable."""
from __future__ import annotations

from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado

from conftest import token
from services import trazabilidad
from test_visualizacion import acervo  # noqa: F401 — fixture compartido

ANA = token(2)


def test_etiqueta_dice_que_parte_del_instrumento_es():
    assert trazabilidad.etiqueta("encabezado") == "Ficha"
    assert trazabilidad.etiqueta("pregunta", "INS-0012-p04") == "Pregunta p04"
    assert trazabilidad.etiqueta("intercambio", "INS-0012-p04", "INS-0012-E02") == "Intercambio E02 · p04"
    assert trazabilidad.etiqueta("otra") == "Otra"


def test_pasajes_por_fuente_sin_repetidos_y_por_similitud():
    fragmentos = [
        {"numero": 1, "seccion": "pregunta", "preguntaId": "p01", "fragmento": "sin cifras", "fragmentoOriginal": "con 32%",
         "score": 0.5, "chunkIndex": 3},
        {"numero": 1, "seccion": "pregunta", "preguntaId": "p01", "fragmento": "repetido", "score": 0.5, "chunkIndex": 3},
        {"numero": 1, "seccion": "encabezado", "fragmento": "ficha", "score": None, "chunkIndex": 0},
        {"numero": 1, "seccion": "respondente", "respondenteId": "INS-1-R017", "fragmento": "R017 dijo", "score": 0.8,
         "chunkIndex": 9},
        {"numero": 2, "seccion": "pregunta", "fragmento": "otra fuente", "score": 0.9, "chunkIndex": 1},
        # Mismo texto en otra posición (piezas que se solapan): no se repite.
        {"numero": 1, "seccion": "respondente", "fragmento": "R017  dijo", "score": 0.7, "chunkIndex": 10},
    ]
    pasajes = trazabilidad.pasajes(fragmentos, 1)
    assert [p.chunkIndex for p in pasajes] == [9, 3, 0]  # más parecido primero; la ficha (sin score) al final
    assert pasajes[0].etiqueta == "Respondente R017" and pasajes[0].respondenteId == "R017"
    assert pasajes[1].texto == "con 32%"  # el texto original, no el que se le dio al modelo sin cifras


def _fuente(numero: int, titulo: str, texto: str):
    from models import FuenteChatOut, PasajeOut

    return FuenteChatOut(numero=numero, instrumentoId=str(numero), titulo=titulo, tipo="Encuesta", investigador="",
                         kpis=[], fragmento=texto,
                         pasajes=[PasajeOut(seccion="pregunta", etiqueta="Pregunta p01", texto=texto, chunkIndex=1)])


FUENTES = [
    _fuente(1, "Escala RAU de Rendimiento Académico Universitario", "Aporto ideas relevantes durante las clases"),
    _fuente(2, "Cuestionario de Compromiso Estudiantil", "Reflexiono profundamente sobre los conceptos"),
    _fuente(3, "Encuesta de Bienestar y Salud Mental", "Me siento emocionalmente equilibrado"),
]


def test_solo_las_fuentes_citadas():
    respuesta = "La escala mide la participación en clase [Fuente 1] y el compromiso (Fuentes 1 y 3)."
    assert [f.numero for f in trazabilidad.citadas(FUENTES, respuesta)] == [1, 3]


def test_las_del_resultado_calculado_cuentan_como_usadas():
    resultado = "[Fuente 2] Cuestionario de Compromiso Estudiantil\n- 32 % respondió «A veces»"
    assert [f.numero for f in trazabilidad.citadas(FUENTES, "El 32 % respondió «A veces».", resultado)] == [2]


def test_si_la_respuesta_cita_solo_cuentan_sus_citas_aunque_el_calculo_nombre_mas():
    resultado = "[Fuente 1] Escala RAU\n- p01: 41 %\n\n[Fuente 2] Compromiso\n- p03: 20 %\n\n[Fuente 3] Bienestar\n- p02: 9 %"
    respuesta = "El 41 % organiza su material [Fuente 1]."
    assert [f.numero for f in trazabilidad.citadas(FUENTES, respuesta, resultado)] == [1]


def test_sin_citas_del_calculo_queda_el_bloque_que_coincide_con_la_respuesta():
    resultado = ("[Fuente 1] Inventario de Estrategias\n- p01 «Organizo el material de estudio antes de comenzar»: 41 %\n\n"
                 "[Fuente 2] Compromiso\n- p03 «Participo en clase con mis compañeros»: 20 %\n\n"
                 "[Fuente 3] Bienestar\n- p02 «Me siento emocionalmente equilibrado»: 9 %")
    respuesta = "El 41 % de los alumnos organiza el material de estudio antes de comenzar."
    assert [f.numero for f in trazabilidad.citadas(FUENTES, respuesta, resultado)] == [1]
    # Si ningún bloque destaca, se quedan todas las del cálculo.
    assert [f.numero for f in trazabilidad.citadas(FUENTES, "Listo.", resultado)] == [1, 2, 3]


def test_sin_citas_quedan_las_que_comparten_contenido():
    respuesta = ("La Escala RAU de Rendimiento Académico Universitario pregunta si los alumnos aportan ideas relevantes "
                 "durante las clases.")
    assert [f.numero for f in trazabilidad.citadas(FUENTES, respuesta)] == [1]


def test_respuesta_sin_relacion_no_muestra_fuentes():
    assert trazabilidad.citadas(FUENTES, "La capital de Francia es París y tiene muchos museos famosos.") == []


def test_citar_agrega_la_fuente_a_cada_linea_que_sale_de_ella():
    respuesta = ("La escala pregunta si los alumnos aportan ideas relevantes durante las clases.\n"
                 "En la encuesta de bienestar dicen sentirse emocionalmente equilibrados.\n"
                 "Esto es una conclusión general sin datos.")
    citada = trazabilidad.citar(respuesta, FUENTES)
    assert citada.split("\n") == [
        "La escala pregunta si los alumnos aportan ideas relevantes durante las clases [Fuente 1].",
        "En la encuesta de bienestar dicen sentirse emocionalmente equilibrados [Fuente 3].",
        "Esto es una conclusión general sin datos.",  # no sale de ninguna fuente: no se cita
    ]
    assert [f.numero for f in trazabilidad.citadas(FUENTES, citada)] == [1, 3]


def test_citar_no_toca_respuestas_que_ya_citan_ni_lineas_ambiguas():
    ya_citada = "Aportan ideas relevantes durante las clases [Fuente 2]."
    assert trazabilidad.citar(ya_citada, FUENTES) == ya_citada
    iguales = [_fuente(n, f"Encuesta {n}", "Aporto ideas relevantes durante las clases") for n in (1, 2, 3)]
    ambigua = "Los alumnos aportan ideas relevantes durante las clases."
    assert trazabilidad.citar(ambigua, iguales) == ambigua  # tres fuentes dicen lo mismo: no se elige una al azar


def test_el_stream_manda_la_respuesta_con_las_citas_añadidas(cliente, acervo, chroma, monkeypatch):  # noqa: F811
    import json as _json

    from shared.db.core.config import settings

    from services import ollama_client

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)

    async def stream(texto, modelo, sistema=None):  # noqa: ANN001
        yield "Los estudiantes dicen: me esfuerzo mucho en clase compromiso."  # sin cita

    monkeypatch.setattr(ollama_client, "generar_stream", stream)
    r = cliente.post("/rag/chat", json={"pregunta": "¿qué tanto se esfuerzan en clase?", "instrumentoIds": ["1"],
                                        "stream": True}, headers=ANA)
    bloque = next(b for b in r.text.split("\n\n") if b.startswith("event: fuentes"))
    evento = _json.loads(bloque.split("data: ", 1)[1])
    assert "[Fuente 1]" in evento["respuesta"]
    assert [f["numero"] for f in evento["fuentes"]] == [1]


def test_las_fuentes_del_chat_traen_sus_pasajes(cliente, acervo, chroma, monkeypatch):  # noqa: F811
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)
    for n, pid in enumerate(["inst-1-0", "inst-1-1", "inst-1-2"]):
        chroma.colecciones["instrumentos"].puntos[pid]["metadata"]["chunk_index"] = n
    r = cliente.post(
        "/rag/chat",
        json={"pregunta": "¿qué tanto se esfuerzan en clase?", "instrumentoIds": ["1"], "stream": False},
        headers=ANA,
    )
    assert r.status_code == 200, r.text
    fuente = r.json()["fuentes"][0]
    pasajes = fuente["pasajes"]
    assert pasajes, "cada tarjeta debe decir de qué parte del documento salió"
    assert {p["chunkIndex"] for p in pasajes} <= {0, 1, 2}
    assert any(p["etiqueta"] == "Pregunta q1" for p in pasajes)
    scores = [p["score"] for p in pasajes if p["score"] is not None]
    assert scores == sorted(scores, reverse=True)


def _indexar(db, id_crudo: int, n: int) -> None:
    col = db.query(ColeccionVectorial).filter(ColeccionVectorial.nombre == "instrumentos").one()
    procesado = db.query(InstrumentoProcesado).filter(InstrumentoProcesado.id_crudo == id_crudo).one()
    secciones = ["encabezado", "pregunta", "respondente", "respondente", "kpi"]
    for i in range(n):
        db.add(DocumentoVectorizado(
            instrumento_id=procesado.id_instrumento, coleccion_id=col.coleccion_id, chunk_index=i,
            seccion=secciones[i % len(secciones)], chunk_texto=f"Fragmento {i}",
            chunk_metadata={"titulo": "Compromiso en posgrado", "tipo": "Encuesta", "fuente": "documento",
                            "preguntaId": f"INS-2-p0{i}" if i else "", "respondenteId": "INS-2-R003" if i in (2, 3) else ""},
        ))
    db.commit()


def test_documento_indexado_por_tramos(cliente, acervo, db):  # noqa: F811
    _indexar(db, 2, 7)
    r = cliente.get("/visualizacion/instrumentos/2/documento", params={"desde": 2, "hasta": 5}, headers=ANA)
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["total"], d["desde"], d["hasta"], d["origen"]) == (7, 2, 5, "documento")
    assert d["titulo"] == "Compromiso en posgrado"
    assert [f["chunkIndex"] for f in d["fragmentos"]] == [2, 3, 4]
    assert d["fragmentos"][0]["etiqueta"] == "Respondente R003 · p02"
    # Sin `hasta`: desde el inicio, hasta el tope por petición o el final.
    completo = cliente.get("/visualizacion/instrumentos/2/documento", headers=ANA).json()
    assert [f["chunkIndex"] for f in completo["fragmentos"]] == list(range(7))


def test_documento_de_instrumento_sin_indexar_es_404(cliente, acervo):  # noqa: F811
    r = cliente.get("/visualizacion/instrumentos/3/documento", headers=ANA)
    assert r.status_code == 404
