"""Pruebas del visualization-service: catálogo, KPIs, relacionados, descargas y RAG."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.kpi_inferido_chunk import KpiInferidoChunk
from shared.models.metadatos_dc import MetadatosDC
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.rag_log import RagLog
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from conftest import token, vector_de

ENCABEZADO = "Instrumento: Compromiso escolar universitario Tipo: Encuesta compromiso esfuerzo escuela"


def _json(titulo: str, preguntas: list[tuple[str, str]], kpis=None, hints=None) -> dict:
    return {
        "instrument": {
            "title": titulo,
            "objective": f"Medir {titulo.lower()}",
            "sections": [{"name": "Reactivos", "questions": [{"question_id": q, "text": t} for q, t in preguntas]}],
        },
        "metadata": {"dublin_core": {"dc:title": titulo, "dc:date": "2024-05-01", "dc:coverage": "Licenciatura"}},
        "design_reference": {"kpi_hints": hints or []},
        "inferred_kpis": kpis or [],
        "statistics": {"per_question": {"q1": {"n": 10, "mean": 4.1}}},
    }


@pytest.fixture()
def acervo(db, tmp_path, chroma, storage):
    db.add_all(
        [
            Usuario(usuario_id=1, nombre="Admin", email="a@x.com", password_hash="x", rol="administrador"),
            Usuario(usuario_id=2, nombre="Ana Beltrán", email="ana@x.com", password_hash="x", rol="investigador"),
            Usuario(usuario_id=3, nombre="Luis Ordóñez", email="luis@x.com", password_hash="x", rol="investigador"),
            KPI(kpi_id=5, nombre="Compromiso académico", descripcion_ampliada_educativa="Grado de involucramiento del estudiante.",
                polaridad_rendimiento="POSITIVO (Maximizar)", texto_contexto_rag_vectorial="Compromiso académico"),
            KPI(kpi_id=6, nombre="Satisfacción estudiantil", texto_contexto_rag_vectorial="Satisfacción estudiantil"),
        ]
    )
    db.flush()

    def instrumento(id_crudo, owner, tipo, data, estado, aprobado):
        ruta_json = None
        if data is not None:
            ruta = tmp_path / f"inst_{id_crudo}.json"
            ruta.write_text(json.dumps(data), encoding="utf-8")
            ruta_json = str(ruta)
        db.add(
            RawData(
                id_crudo=id_crudo, id_owner=owner, tipo_instrumento=tipo, nombre_archivo=f"inst_{id_crudo}.csv",
                raw_archivo=f"raw/_/{id_crudo}__inst.csv", fecha_carga=datetime(2024, 5, 2),
            )
        )
        db.flush()
        procesado = InstrumentoProcesado(
            id_crudo=id_crudo, estado=estado, ruta_json=ruta_json,
            fecha_aprobado=datetime(2024, 5, 3) if aprobado else None,
        )
        db.add(procesado)
        db.flush()
        return procesado

    a = instrumento(
        1, 2, "encuesta",
        _json("Compromiso escolar", [("q1", "Me esfuerzo mucho en clase"), ("q2", "Me gusta mi escuela")],
              kpis=[{"kpi_id": 5, "nombre_kpi": "Compromiso académico", "score": 0.7}]),
        "vectorizado", True,
    )
    instrumento(2, 3, "encuesta", _json("Compromiso en posgrado", [("q1", "Participo en seminarios")], hints=["Compromiso académico"]), "estandarizado", False)
    instrumento(3, 3, "entrevista", None, "recibido", False)

    db.add(MetadatosDC(id_crudo=1, dc_title="Compromiso escolar universitario", dc_subject="compromiso, escuela", dc_coverage="Licenciatura — Pedagogía", dc_description="Mide el compromiso."))
    db.add(MetadatosEnriquecidosEncuestas(id_crudo=1, palabras_clave=["compromiso", "esfuerzo"]))
    col = ColeccionVectorial(nombre="instrumentos")
    db.add(col)
    db.flush()
    doc = DocumentoVectorizado(instrumento_id=a.id_instrumento, coleccion_id=col.coleccion_id, chunk_texto="x", chunk_metadata={})
    db.add(doc)
    db.add(KPIInferido(id_procesado=a.id_instrumento, kpi_id=5))
    db.flush()
    db.add(KpiInferidoChunk(id_procesado=a.id_instrumento, kpi_id=5, documento_vectorizado_id=doc.documento_vectorizado_id, score=0.81))
    db.commit()

    instrumentos = chroma.crear("instrumentos")
    base = {"titulo": "Compromiso escolar universitario", "tipo": "Encuesta", "investigador": "Ana Beltrán", "kpis": '["Compromiso académico"]'}
    instrumentos.agregar("inst-1-0", ENCABEZADO, {**base, "instrumentoId": "1", "seccion": "encabezado", "preguntaId": "", "pregunta": ""})
    instrumentos.agregar("inst-1-1", "Pregunta q1: Me esfuerzo mucho en clase compromiso", {**base, "instrumentoId": "1", "seccion": "pregunta", "preguntaId": "q1", "pregunta": "Me esfuerzo mucho en clase"})
    instrumentos.agregar("inst-1-2", "Pregunta q2: Me gusta mi escuela", {**base, "instrumentoId": "1", "seccion": "pregunta", "preguntaId": "q2", "pregunta": "Me gusta mi escuela"})
    instrumentos.agregar("inst-2-0", ENCABEZADO + " posgrado", {**base, "instrumentoId": "2", "titulo": "Compromiso en posgrado", "investigador": "Luis", "seccion": "encabezado", "preguntaId": "", "pregunta": ""})
    chroma.crear("kpis").agregar("5", "compromiso esfuerzo clase", {"kpi_id": 5})

    storage.archivos["raw/_/2__inst.csv"] = (b"P1,P2\n1,2\n", "inst_2.csv")
    storage.tablas["raw/_/1__inst.csv"] = {
        "headers": ["Carrera", "¿Qué tan de acuerdo estás con que te gusta tu escuela?", "Edad"],
        "rows": [["Derecho", "De acuerdo", "21"], ["Medicina", "Totalmente de acuerdo", "22"], ["Derecho", "", "20"]],
    }
    return db


ANA, LUIS = token(2), token(3)


def test_catalogo_filtros_y_facetas(cliente, acervo):
    r = cliente.get("/visualizacion/catalogo", headers=ANA).json()
    assert r["total"] == 3
    ficha = next(i for i in r["items"] if i["id"] == "1")
    assert ficha["titulo"] == "Compromiso escolar universitario"  # la tabla aprobada gana al JSON
    assert ficha["autorNombre"] == "Ana Beltrán"
    assert ficha["estado"] == "Estandarizado" and ficha["aprobado"] and ficha["indexado"]
    assert ficha["etiquetas"] == ["compromiso", "esfuerzo"]
    assert ficha["reactivos"] == 2 and ficha["anio"] == 2024
    assert r["facetas"]["tipo"] == {"Encuesta": 2, "Entrevista": 1}

    propios = cliente.get("/visualizacion/catalogo", params={"propios": "true"}, headers=ANA).json()
    assert [i["id"] for i in propios["items"]] == ["1"]
    por_kpi = cliente.get("/visualizacion/catalogo", params={"kpi": "5"}, headers=ANA).json()
    assert {i["id"] for i in por_kpi["items"]} == {"1", "2"}
    por_nombre = cliente.get("/visualizacion/catalogo", params={"kpi": "Compromiso académico"}, headers=ANA).json()
    assert {i["id"] for i in por_nombre["items"]} == {"1", "2"}
    assert cliente.get("/visualizacion/catalogo", params={"kpi": "inexistente"}, headers=ANA).json()["total"] == 0
    texto = cliente.get("/visualizacion/catalogo", params={"q": "posgrado"}, headers=ANA).json()
    assert [i["id"] for i in texto["items"]] == ["2"]
    aprobados = cliente.get("/visualizacion/catalogo", params={"aprobados": "true"}, headers=ANA).json()
    assert {i["id"] for i in aprobados["items"]} == {"1", "2"}
    assert cliente.get("/visualizacion/catalogo").status_code == 401


def test_detalle_e_investigadores(cliente, acervo):
    d = cliente.get("/visualizacion/catalogo/1", headers=ANA).json()
    assert d["dublin_core"]["dc_title"] == "Compromiso escolar universitario"
    assert d["enriquecidos"]["palabras_clave"] == ["compromiso", "esfuerzo"]
    assert [p["id"] for p in d["preguntas"]] == ["q1", "q2"]
    assert d["estadisticas"]["q1"]["mean"] == 4.1
    inv = cliente.get("/visualizacion/investigadores", headers=ANA).json()
    assert {i["id"]: i["nombre"] for i in inv}["3"] == "Luis Ordóñez"


def test_catalogo_de_kpis_y_resumen(cliente, acervo):
    cat = {k["id"]: k for k in cliente.get("/visualizacion/kpis/catalogo", headers=ANA).json()}
    assert cat["5"]["instrumentos"] == 2
    assert cat["5"]["icono"] == "BookOpen"
    assert cat["6"]["icono"] == "Smile" and cat["6"]["instrumentos"] == 0
    resumen = {m["id"]: m for m in cliente.get("/visualizacion/kpis/resumen", headers=ANA).json()}
    assert resumen["acervo"]["valor"] == "3"
    assert resumen["aprobados"]["valor"] == "2"
    assert resumen["kpis"]["valor"] == "1"


def test_dashboard_con_preguntas_que_miden_el_kpi(cliente, acervo, chroma):
    r = cliente.post("/visualizacion/kpis/5/datos", json={"instrumentoIds": ["1", "2", "3"]}, headers=ANA)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fuentesConteo"] == 2
    assert {p["etiqueta"]: p["valor"] for p in d["porTipo"]} == {"Encuesta": 2}
    assert d["porAnio"] == [{"etiqueta": "2024", "valor": 3}]
    ins = {i["instrumentoId"]: i for i in d["instrumentos"]}
    assert ins["1"]["origen"] == "aceptado" and ins["1"]["score"] == pytest.approx(0.81)
    assert ins["1"]["preguntas"][0]["preguntaId"] == "q1"
    assert ins["2"]["origen"] == "referencia" and ins["2"]["preguntas"] == []  # no ingerido aún
    consulta = chroma.colecciones["instrumentos"].consultas[-1]
    assert consulta["where"] == {"$and": [{"instrumentoId": "1"}, {"seccion": "pregunta"}]}
    assert cliente.post("/visualizacion/kpis/999/datos", json={}, headers=ANA).status_code == 404


def test_kpis_de_un_instrumento(cliente, acervo):
    r = cliente.get("/visualizacion/instrumentos/1/kpis", headers=ANA).json()
    assert r[0]["nombre"] == "Compromiso académico"
    assert r[0]["origen"] == "aceptado"
    assert r[0]["preguntas"][0]["texto"] == "Me esfuerzo mucho en clase"


def test_relacionados(cliente, acervo):
    r = cliente.post("/visualizacion/relacionados", json={"ids": ["1"]}, headers=ANA).json()
    assert [x["instrumento"]["id"] for x in r] == ["2", "3"]
    primero = r[0]
    assert primero["nivel"] == "alta"
    assert {razon["tipo"] for razon in primero["razones"]} == {"kpi", "nivel", "descripcion"}
    assert primero["coincideCon"] == ["1"]
    assert r[1]["nivel"] == "baja"  # solo comparte el nivel


def test_descargas_con_regla_de_propiedad(cliente, acervo, storage):
    crudo = cliente.get("/visualizacion/descargas/2", params={"formato": "crudo"}, headers=ANA)
    assert crudo.status_code == 200 and crudo.content == b"P1,P2\n1,2\n"
    assert "inst_2.csv" in crudo.headers["content-disposition"]

    assert cliente.get("/visualizacion/descargas/2", params={"formato": "json"}, headers=ANA).status_code == 403
    propio = cliente.get("/visualizacion/descargas/2", params={"formato": "json"}, headers=LUIS)
    assert propio.status_code == 200 and propio.json()["instrument"]["title"] == "Compromiso en posgrado"
    assert cliente.get("/visualizacion/descargas/3", params={"formato": "json"}, headers=LUIS).status_code == 404
    assert cliente.get("/visualizacion/descargas/3", params={"formato": "sav"}, headers=LUIS).status_code == 422


def test_descarga_sav(cliente, acervo, storage):
    pyreadstat = pytest.importorskip("pyreadstat")
    r = cliente.get("/visualizacion/descargas/1", params={"formato": "sav"}, headers=ANA)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"$FL2"
    assert storage.guardados[0][1] == "sav"

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as f:
        f.write(r.content)
    df, meta = pyreadstat.read_sav(f.name)
    assert meta.column_names == ["Carrera", "P2", "Edad"]
    assert meta.column_names_to_labels["P2"].startswith("¿Qué tan de acuerdo")
    assert meta.variable_value_labels["P2"] == {1.0: "De acuerdo", 2.0: "Totalmente de acuerdo"}
    assert meta.variable_measure["Edad"] == "scale"


def test_rag_index(cliente, acervo, storage):
    storage.indice[1] = {"indexado": True, "chunks": 3}
    r = cliente.post("/rag/index", json={"investigacionId": "res-1", "instrumentoIds": ["1", "3"]}, headers=ANA).json()
    estados = {i["instrumentoId"]: i for i in r["instrumentos"]}
    assert estados["1"]["estado"] == "indexado" and estados["1"]["chunks"] == 3
    assert estados["3"]["estado"] == "omitido" and "aprobados" in estados["3"]["motivo"]
    assert r["coleccion"] == "instrumentos"


def test_chat_json_filtrado_por_investigacion_y_registrado(cliente, acervo, chroma, ollama, db):
    r = cliente.post(
        "/rag/chat",
        json={
            "investigacionId": "res-1",
            "pregunta": "¿qué tanto se esfuerzan en clase?",
            "instrumentoIds": ["1"],
            "stream": False,
            "contexto": {"objetivo": "Analizar el compromiso", "nivel": "Licenciatura"},
        },
        headers=ANA,
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["respuesta"].startswith("Respuesta fundamentada")
    assert [f["instrumentoId"] for f in cuerpo["fuentes"]] == ["1"]
    assert cuerpo["fuentes"][0]["kpis"] == ["Compromiso académico"]
    assert chroma.colecciones["instrumentos"].consultas[-1]["where"] == {"instrumentoId": {"$in": ["1"]}}
    assert "Analizar el compromiso" in ollama["prompts"][-1]
    db.expire_all()
    log = db.query(RagLog).one()
    assert log.pregunta == "¿qué tanto se esfuerzan en clase?" and log.chunks_usados == 3


def test_chat_sse_y_sin_coleccion(cliente, acervo, chroma):
    r = cliente.post("/rag/chat", json={"pregunta": "compromiso", "stream": True}, headers=ANA)
    assert r.status_code == 200
    texto = r.text
    assert "event: token" in texto and "Hola " in texto
    assert texto.index("event: fuentes") < texto.index("event: fin")
    assert chroma.colecciones["instrumentos"].consultas[-1]["where"] is None  # todo el sistema

    chroma.colecciones.clear()
    assert cliente.post("/rag/chat", json={"pregunta": "x", "stream": False}, headers=ANA).status_code == 409


def test_vector_de_es_determinista():
    assert vector_de("hola mundo") == vector_de("hola mundo")
