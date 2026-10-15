"""Pruebas del espacio vectorial (mapa 2D, PCA, clusters y fuente de chunks)."""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pytest

from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from conftest import token, vector_de

ANA = token(2)


def _json(titulo: str, preguntas: list[str]) -> dict:
    return {
        "instrument": {
            "title": titulo,
            "sections": [{"name": "Reactivos", "questions": [{"question_id": f"q{i}", "text": t} for i, t in enumerate(preguntas, 1)]}],
        },
        "metadata": {"dublin_core": {"dc:title": titulo, "dc:description": f"Mide {titulo.lower()}. Segunda oración."}},
    }


@pytest.fixture()
def espacio(db, tmp_path, chroma):
    from services.espacio import mapa, vectores_instrumento

    mapa._cache.clear()
    vectores_instrumento._cache.clear()
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    textos_kpi = {
        1: "satisfaccion estudiantes servicios bienestar",
        2: "satisfaccion bienestar apoyo estudiantes",
        3: "graduacion eficiencia terminal egreso",
        4: "graduacion egreso titulacion tiempo",
        5: "investigacion publicaciones patentes",
        6: "investigacion proyectos financiamiento publicaciones",
    }
    for kid, texto in textos_kpi.items():
        db.add(KPI(kpi_id=kid, nombre=f"KPI {kid}", texto_contexto_rag_vectorial=texto,
                   descripcion_ampliada_educativa=f"Definición del KPI {kid}. Más detalle.",
                   polaridad_rendimiento="POSITIVO (Maximizar)"))
    # El KPI 6 no está en Chroma: se embebe al vuelo.
    col_kpis = chroma.crear("kpis")
    for kid, texto in textos_kpi.items():
        if kid != 6:
            col_kpis.agregar(str(kid), texto, {"nombre": f"KPI {kid}"})

    def instrumento(id_crudo: int, titulo: str, preguntas: list[str]) -> InstrumentoProcesado:
        ruta = tmp_path / f"inst_{id_crudo}.json"
        ruta.write_text(json.dumps(_json(titulo, preguntas)), encoding="utf-8")
        db.add(RawData(id_crudo=id_crudo, id_owner=2, tipo_instrumento="encuesta", nombre_archivo=f"i{id_crudo}.csv",
                       raw_archivo=f"raw/{id_crudo}", fecha_carga=datetime(2024, 5, 2)))
        db.flush()
        p = InstrumentoProcesado(id_crudo=id_crudo, estado="estandarizado", ruta_json=str(ruta))
        db.add(p)
        db.flush()
        return p

    p1 = instrumento(1, "Bienestar estudiantil", ["satisfaccion con servicios", "apoyo bienestar"])
    instrumento(2, "Trayectoria de egreso", ["tiempo de graduacion", "titulacion egreso"])
    db.add(RawData(id_crudo=3, id_owner=2, tipo_instrumento="entrevista", nombre_archivo="sin_json.txt",
                   raw_archivo="raw/3", fecha_carga=datetime(2024, 5, 2)))
    db.commit()

    # El instrumento 1 ya tiene summary del analysis-service (id = id_instrumento).
    chroma.crear("summary_instrument").agregar(str(p1.id_instrumento), "satisfaccion bienestar servicios", {})
    # Chunks del RAG (provisionales).
    chunks = chroma.crear("instrumentos")
    chunks.agregar("inst-1-0", "encabezado bienestar", {"instrumentoId": "1", "seccion": "encabezado"})
    chunks.agregar("inst-1-1", "satisfaccion con servicios", {"instrumentoId": "1", "seccion": "pregunta"})
    chunks.agregar("inst-2-1", "tiempo de graduacion", {"instrumentoId": "2", "seccion": "pregunta"})
    return db


# ── Álgebra ────────────────────────────────────────────────────────────────────


def test_pca_varianza_y_misma_transformacion():
    from services.espacio.algebra import ajustar_pca

    rng = np.random.default_rng(0)
    base = rng.normal(size=(40, 5)) * np.array([10, 3, 1, 0.1, 0.1])
    proy = ajustar_pca(base)
    assert proy.varianza[0] > proy.varianza[1] > 0
    assert 0.9 < proy.varianza_total <= 1.0
    # Proyectar un punto existente da lo mismo que proyectarlo dentro del conjunto.
    assert np.allclose(proy.proyectar(base)[7], proy.proyectar(base[7]))


def test_kmeans_esferico_separa_temas_y_es_determinista():
    from services.espacio.algebra import kmeans_esferico

    x = np.array([[1, 0.1, 0], [0.9, 0, 0.1], [0, 1, 0.1], [0.1, 0.9, 0]], dtype=float)
    a, _ = kmeans_esferico(x, 2)
    b, _ = kmeans_esferico(x, 2)
    assert list(a) == list(b)
    assert a[0] == a[1] and a[2] == a[3] and a[0] != a[2]


# ── Endpoint ───────────────────────────────────────────────────────────────────


def test_mapa_requiere_token(cliente, espacio):
    assert cliente.get("/visualizacion/espacio/mapa").status_code == 401


def test_mapa_kpis_instrumentos_varianza_y_clusters(cliente, espacio):
    r = cliente.get("/visualizacion/espacio/mapa", headers=ANA)
    assert r.status_code == 200, r.text
    m = r.json()
    assert m["conteos"] == {"kpis": 6, "instrumentos": 2, "chunks": 0}
    assert m["dimension"] == 16
    assert len(m["pca"]["varianza"]) == 2 and 0 < m["pca"]["varianzaTotal"] <= 1
    assert m["fuenteChunks"] == {"nombre": "rag_instrumentos", "provisional": True}

    puntos = {p["id"]: p for p in m["puntos"]}
    assert puntos["kpi:1"]["resumen"] == "Definición del KPI 1."
    assert puntos["kpi:1"]["detalle"] == "POSITIVO"
    # Origen del vector: summary del analysis-service o calculado en memoria.
    assert puntos["inst:1"]["origenVector"] == "summary"
    assert puntos["inst:2"]["origenVector"] == "calculado"
    assert puntos["inst:2"]["detalle"].startswith("Encuesta")
    assert "inst:3" not in puntos  # sin JSON estandarizado no hay vector

    # Clusters: los KPIs del mismo tema caen juntos; el instrumento hereda el de su KPI más cercano.
    assert m["clusters"] and all(c["representativos"] for c in m["clusters"])
    assert puntos["kpi:3"]["clusterId"] == puntos["kpi:4"]["clusterId"]
    assert puntos["inst:2"]["clusterId"] == puntos["kpi:4"]["clusterId"]


def test_mapa_con_chunks_proyectados_con_el_mismo_pca(cliente, espacio):
    from services.espacio import mapa

    m = cliente.get("/visualizacion/espacio/mapa?chunks=true", headers=ANA).json()
    assert m["conteos"]["chunks"] == 3
    chunk = next(p for p in m["puntos"] if p["id"] == "chunk:inst-1-1")
    assert chunk["tipo"] == "chunk" and chunk["instrumentoId"] == "1"
    esperado = mapa._cache["vigente"].proyeccion.proyectar(np.asarray(vector_de("satisfaccion con servicios")))[0]
    assert chunk["x"] == pytest.approx(esperado[0], abs=1e-3)
    assert chunk["y"] == pytest.approx(esperado[1], abs=1e-3)


def test_mapa_usa_cache_mientras_no_cambian_los_datos(cliente, espacio):
    primero = cliente.get("/visualizacion/espacio/mapa", headers=ANA).json()["generadoEn"]
    segundo = cliente.get("/visualizacion/espacio/mapa", headers=ANA).json()["generadoEn"]
    assert primero == segundo
    espacio.add(KPI(kpi_id=7, nombre="KPI 7", texto_contexto_rag_vectorial="nuevo indicador"))
    espacio.commit()
    tercero = cliente.get("/visualizacion/espacio/mapa", headers=ANA).json()
    assert tercero["generadoEn"] != primero and tercero["conteos"]["kpis"] == 7
