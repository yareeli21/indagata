"""Pruebas de la ingesta al índice vectorial (colección `instrumentos`)."""
from __future__ import annotations

from datetime import datetime, timezone

from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

JSON_APROBADO = {
    "instrument": {
        "title": "Calidad académica",
        "objective": "Explorar la percepción de exigencia académica.",
        "dimensions_explored": ["Exigencia", "Retroalimentación"],
        "sections": [
            {
                "section_id": "s1",
                "name": "Reactivos",
                "questions": [
                    {"question_id": "q1", "text": "¿Qué tan claro es el nivel esperado?", "options": ["1", "2", "3"]},
                    {"question_id": "q2", "text": "¿Recibes retroalimentación?", "options": ["Sí", "No"]},
                ],
            }
        ],
    },
    "metadata": {
        "dublin_core": {"dc:title": "Calidad académica", "dc:creator": "Ana", "dc:coverage": "Posgrado, CDMX", "dc:date": "2025-03-01"},
        "survey_specific": {"palabras_clave": ["exigencia", "calidad"], "n_respondentes": 40},
    },
    "statistics": {"per_question": {"q1": {"n": 40, "mean": 2.5, "std": 0.5, "distribution": {"2": 20, "3": 20}}}},
    "inferred_kpis": [{"kpi_id": 3, "nombre_kpi": "Satisfacción académica", "score": 0.8}],
}


def _sembrar(db, *, aprobado: bool) -> tuple[int, int]:
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    raw = RawData(id_owner=2, tipo_instrumento="encuesta", nombre_archivo="a.csv", raw_archivo="raw/_/1__a.csv")
    db.add(raw)
    db.flush()
    procesado = InstrumentoProcesado(
        id_crudo=raw.id_crudo,
        estado="estandarizado" if aprobado else "recibido",
        fecha_aprobado=datetime.now(timezone.utc) if aprobado else None,
    )
    db.add(procesado)
    db.commit()
    return raw.id_crudo, procesado.id_instrumento


def _guardar_json(cliente, servicio, id_crudo: int, contenido: dict, tipo: str = "metadata") -> None:
    r = cliente.post(
        "/almacenamiento/json",
        headers=servicio,
        json={"instrumentoId": str(id_crudo), "tipo": tipo, "contenido": contenido},
    )
    assert r.status_code == 200, r.text


def test_no_se_ingiere_sin_aprobacion(cliente, servicio, db):
    id_crudo, _ = _sembrar(db, aprobado=False)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)
    r = cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    assert r.status_code == 409
    assert "aprobados" in r.json()["detail"]


def test_ingesta_por_pregunta_y_registro_en_bd(cliente, servicio, db, chroma):
    id_crudo, id_instrumento = _sembrar(db, aprobado=True)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)

    r = cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "indexado"
    assert cuerpo["idInstrumento"] == id_instrumento

    puntos = chroma.colecciones["instrumentos"].puntos
    assert len(puntos) == cuerpo["chunks"]
    encabezado = puntos[f"inst-{id_crudo}-0"]
    assert encabezado["metadata"]["seccion"] == "encabezado"
    assert "Satisfacción académica" in encabezado["document"]
    assert encabezado["metadata"]["nivel"] == "Posgrado"
    assert encabezado["metadata"]["anio"] == 2025
    preguntas = [p for p in puntos.values() if p["metadata"]["seccion"] == "pregunta"]
    assert {p["metadata"]["preguntaId"] for p in preguntas} == {"q1", "q2"}
    q1 = next(p for p in preguntas if p["metadata"]["preguntaId"] == "q1")
    assert "media 2.50" in q1["document"]

    db.expire_all()
    assert db.query(DocumentoVectorizado).count() == cuerpo["chunks"]
    assert db.get(InstrumentoProcesado, id_instrumento).estado == "vectorizado"

    estado = cliente.get(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio).json()
    assert estado == {
        "instrumentoId": str(id_crudo),
        "coleccion": "instrumentos",
        "indexado": True,
        "chunks": cuerpo["chunks"],
        "aprobado": True,
    }


def test_reingesta_reemplaza_y_no_toca_otras_colecciones(cliente, servicio, db, chroma):
    from shared.models.coleccion_vectorial import ColeccionVectorial

    id_crudo, id_instrumento = _sembrar(db, aprobado=True)
    # Fila de evidencia del analysis-service en otra colección: no debe borrarse.
    col = ColeccionVectorial(nombre="summary_instrument")
    db.add(col)
    db.flush()
    db.add(DocumentoVectorizado(instrumento_id=id_instrumento, coleccion_id=col.coleccion_id, chunk_texto="summary", chunk_metadata={}))
    db.commit()

    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)
    cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    reducido = {**JSON_APROBADO, "instrument": {**JSON_APROBADO["instrument"], "sections": []}}
    _guardar_json(cliente, servicio, id_crudo, reducido, tipo="analysis")
    r = cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio).json()

    assert len(chroma.colecciones["instrumentos"].puntos) == r["chunks"]
    db.expire_all()
    assert db.query(DocumentoVectorizado).filter(DocumentoVectorizado.coleccion_id == col.coleccion_id).count() == 1

    sin_reindexar = cliente.post(
        f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio, json={"reindexar": False}
    ).json()
    assert sin_reindexar["motivo"] == "Ya estaba indexado."


def test_desindexar(cliente, servicio, db, chroma):
    id_crudo, id_instrumento = _sembrar(db, aprobado=True)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)
    cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)

    r = cliente.delete(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio).json()
    assert r["vectores_eliminados"] > 0
    assert chroma.colecciones["instrumentos"].puntos == {}
    db.expire_all()
    assert db.get(InstrumentoProcesado, id_instrumento).estado == "estandarizado"


def test_ruta_json_del_seed(cliente, servicio, db, chroma):
    """Los instrumentos sembrados (sin artefacto) se resuelven por ruta_json."""
    import json

    from services import file_manager

    id_crudo, id_instrumento = _sembrar(db, aprobado=True)
    (file_manager.raiz() / "raw" / "inst_05.v1.json").write_text(json.dumps(JSON_APROBADO), encoding="utf-8")
    db.get(InstrumentoProcesado, id_instrumento).ruta_json = "storage/raw/inst_05.v1.json"
    db.commit()
    r = cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    assert r.status_code == 200, r.text
    assert r.json()["chunks"] >= 3


def test_colecciones(cliente, servicio, db, chroma):
    id_crudo, _ = _sembrar(db, aprobado=True)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)
    cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    cols = cliente.get("/almacenamiento/indice/colecciones", headers=servicio).json()
    assert cols[0]["nombre"] == "instrumentos"
    assert cols[0]["n_vectores"] > 0
    assert cols[0]["chunk_size"] == 800
