"""Tests de integración (TestClient) para metadatos específicos (Bug 2 / FEAT-002).

Cubre:
  - Ruteo: /api/metadata/metadata/{id} sigue resolviendo a register_metadata (DC),
    /api/metadata/{id}/especificos resuelve al handler nuevo, y
    /api/metadata/metadata/{id}/init sigue resolviendo (design §8, Hallazgo 5).
  - UPSERT por tipo (encuesta) y mismatch de tipo (409).

No requiere BD real: se usa un fake de Session vía dependency_overrides[get_db].
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main
from shared.db.database import get_db
from shared.models import (
    MetadatosEnriquecidosEncuestas,
    MetadatosEnriquecidosEntrevistas,
    MetadatosEnriquecidosPruebas,
)
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData


# --------------------------------------------------------------------------- #
# Fake DB mínimo que soporta las cadenas .query(M).filter(...).first() usadas
# por SpecificMetadataManager.upsert, además de add/commit/refresh.
# --------------------------------------------------------------------------- #
class _FakeQuery:
    def __init__(self, store, modelo):
        self._store = store
        self._modelo = modelo

    def filter(self, *criterios):  # noqa: ARG002 - solo necesitamos .first()
        return self

    def first(self):
        return self._store.get(self._modelo)


class _FakeSession:
    """Mantiene una fila por modelo (suficiente para los tests)."""

    def __init__(self, filas: dict):
        # filas: {ModelClass: instancia}
        self._store = dict(filas)
        self.committed = False

    def query(self, modelo):
        return _FakeQuery(self._store, modelo)

    def add(self, obj):
        self._store[type(obj)] = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):  # noqa: D401
        return obj

    def rollback(self):
        self.committed = False


def _instrumento(id_instrumento=7, id_crudo=5):
    inst = InstrumentoProcesado(id_crudo=id_crudo, estado="metadatos_registrados")
    inst.id_instrumento = id_instrumento
    return inst


def _raw(id_crudo=5, tipo="encuesta"):
    raw = RawData(
        id_owner=1,
        tipo_instrumento=tipo,
        nombre_archivo="x.csv",
        raw_archivo="raw/x.csv",
    )
    raw.id_crudo = id_crudo
    return raw


def _client_con_db(filas: dict) -> TestClient:
    app = main.app
    app.dependency_overrides[get_db] = lambda: _FakeSession(filas)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    main.app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Ruteo (Hallazgo 5)
# --------------------------------------------------------------------------- #
def test_rutas_registradas_no_se_interceptan():
    rutas = {
        (tuple(sorted(r.methods)), r.path)
        for r in main.app.routes
        if hasattr(r, "path") and hasattr(r, "methods")
    }
    # register_metadata (DC) intacto
    assert (("POST",), "/api/metadata/metadata/{instrumento_id}") in rutas
    # init (DC) intacto
    assert (("GET",), "/api/metadata/metadata/{instrumento_id}/init") in rutas
    # handler nuevo de específicos
    assert (("POST",), "/api/metadata/{instrumento_id}/especificos") in rutas


def test_especificos_resuelve_al_handler_nuevo():
    """La ruta /especificos NO es capturada por el handler DC."""
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={"tipo": "encuesta", "campos": {"objetivo": "Medir X"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["instrumento_id"] == 7
    assert body["tipo"] == "encuesta"
    assert body["campos"]["objetivo"] == "Medir X"


# --------------------------------------------------------------------------- #
# UPSERT por tipo
# --------------------------------------------------------------------------- #
def test_upsert_encuesta_insert_y_coacciones():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={
            "tipo": "encuesta",
            "campos": {
                "n_respondentes": "250",            # str -> int
                "n_poblacion": "",                  # vacío -> NULL
                "objetivo": "Clima laboral",
                "palabras_clave": ["clima", "satisfaccion"],  # JSON list
                "dimensiones": "",                  # vacío -> NULL
                "campo_desconocido": "ignorar",     # no es columna -> se ignora
            },
        },
    )
    assert resp.status_code == 200
    campos = resp.json()["campos"]
    assert campos["n_respondentes"] == 250
    assert campos["n_poblacion"] is None
    assert campos["objetivo"] == "Clima laboral"
    assert campos["palabras_clave"] == ["clima", "satisfaccion"]
    assert campos["dimensiones"] is None
    assert "campo_desconocido" not in campos


def test_upsert_actualiza_fila_existente():
    fila_previa = MetadatosEnriquecidosEncuestas(id_crudo=5, objetivo="viejo")
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
        MetadatosEnriquecidosEncuestas: fila_previa,
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={"tipo": "encuesta", "campos": {"objetivo": "nuevo"}},
    )
    assert resp.status_code == 200
    assert resp.json()["campos"]["objetivo"] == "nuevo"
    assert fila_previa.objetivo == "nuevo"


def test_upsert_entrevista():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="entrevista"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={"tipo": "entrevista", "campos": {"metodologia": "semiestructurada"}},
    )
    assert resp.status_code == 200
    assert resp.json()["campos"]["metodologia"] == "semiestructurada"


def test_upsert_prueba_json_field():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="prueba_estandarizada"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={
            "tipo": "prueba_estandarizada",
            "campos": {
                "unidad_de_aprendizaje": "Álgebra",
                "mapeo_de_reactivos_por_seccion": {"s1": [1, 2, 3]},
            },
        },
    )
    assert resp.status_code == 200
    campos = resp.json()["campos"]
    assert campos["unidad_de_aprendizaje"] == "Álgebra"
    assert campos["mapeo_de_reactivos_por_seccion"] == {"s1": [1, 2, 3]}


# --------------------------------------------------------------------------- #
# Errores
# --------------------------------------------------------------------------- #
def test_mismatch_de_tipo_409():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={"tipo": "entrevista", "campos": {}},
    )
    assert resp.status_code == 409


def test_instrumento_inexistente_404():
    filas = {RawData: _raw()}  # sin InstrumentoProcesado
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/999/especificos",
        json={"tipo": "encuesta", "campos": {}},
    )
    assert resp.status_code == 404


def test_falta_tipo_422():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
    }
    client = _client_con_db(filas)
    resp = client.post("/api/metadata/7/especificos", json={"campos": {}})
    assert resp.status_code == 422


def test_n_respondentes_no_entero_422():
    filas = {
        InstrumentoProcesado: _instrumento(),
        RawData: _raw(tipo="encuesta"),
    }
    client = _client_con_db(filas)
    resp = client.post(
        "/api/metadata/7/especificos",
        json={"tipo": "encuesta", "campos": {"n_respondentes": "muchos"}},
    )
    assert resp.status_code == 422
