"""Fixtures de prueba del storage-service.

- BD: SQLite en memoria con el esquema `tt_rag` adjunto (ATTACH), creada desde los
  modelos de `shared` (JSONB se compila como JSON).
- Almacenamiento: directorios temporales (RAW_PATH, JSON_PATH, ...).
- ChromaDB y embeddings: dobles en memoria (sin red ni modelos).

Ejecutar desde la carpeta del servicio:  python -m pytest tests
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
_REPO = _SERVICIO.parents[1]
sys.path.insert(0, str(_SERVICIO))
sys.path.insert(1, str(_REPO))

_TMP = Path(tempfile.mkdtemp(prefix="indagata-storage-"))
os.environ.update(
    {
        "RAW_PATH": str(_TMP / "storage" / "raw"),
        "JSON_PATH": str(_TMP / "storage" / "json"),
        "SAV_PATH": str(_TMP / "storage" / "sav"),
        "CLEAN_PATH": str(_TMP / "storage" / "clean"),
        "TEMP_PATH": str(_TMP / "storage" / "temp"),
        "SECRET_KEY": "clave-de-pruebas",
        "DEBUG": "false",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(tipo, compilador, **kw):  # noqa: ANN001
    return "JSON"


import shared.models  # noqa: E402,F401  (registra todas las tablas)
from shared.auth import crear_access_token, crear_token_servicio  # noqa: E402
from shared.db.base import Base  # noqa: E402
from shared.db.session import get_db  # noqa: E402
from shared.models.documento_vectorizado import DocumentoVectorizado  # noqa: E402

# El DEFAULT '{}'::jsonb es sintaxis de Postgres; en SQLite se omite.
DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None


# ── Dobles de ChromaDB ─────────────────────────────────────────────────────────


def _coincide(meta: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_coincide(meta, w) for w in where["$and"])
    for clave, condicion in where.items():
        valor = meta.get(clave)
        if isinstance(condicion, dict):
            if "$in" in condicion and valor not in condicion["$in"]:
                return False
            if "$eq" in condicion and valor != condicion["$eq"]:
                return False
        elif valor != condicion:
            return False
    return True


class ColeccionFalsa:
    def __init__(self, nombre: str) -> None:
        self.name = nombre
        self.puntos: dict[str, dict] = {}

    def upsert(self, ids, embeddings, documents, metadatas):  # noqa: ANN001
        for i, e, d, m in zip(ids, embeddings, documents, metadatas):
            for valor in m.values():
                assert valor is not None and isinstance(valor, (str, int, float, bool)), m
            self.puntos[i] = {"embedding": e, "document": d, "metadata": m}

    def delete(self, ids=None, where=None):  # noqa: ANN001
        for i in list(self.puntos):
            if (ids and i in ids) or (where and _coincide(self.puntos[i]["metadata"], where)):
                del self.puntos[i]

    def get(self, ids=None, where=None, include=None):  # noqa: ANN001
        seleccion = [
            (i, p)
            for i, p in self.puntos.items()
            if (ids is None or i in ids) and _coincide(p["metadata"], where)
        ]
        return {
            "ids": [i for i, _ in seleccion],
            "documents": [p["document"] for _, p in seleccion],
            "metadatas": [p["metadata"] for _, p in seleccion],
            "embeddings": [p["embedding"] for _, p in seleccion],
        }

    def count(self) -> int:
        return len(self.puntos)


class ClienteFalso:
    def __init__(self) -> None:
        self.colecciones: dict[str, ColeccionFalsa] = {}

    def get_or_create_collection(self, name, metadata=None):  # noqa: ANN001
        return self.colecciones.setdefault(name, ColeccionFalsa(name))

    def get_collection(self, name):  # noqa: ANN001
        return self.colecciones[name]

    def list_collections(self):
        return list(self.colecciones.values())


def embeddings_falsos(textos: list[str]) -> list[list[float]]:
    vectores = []
    for t in textos:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        vectores.append([b / 255 for b in h[:8]])
    return vectores


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(eng, "connect")
    def _adjuntar(conexion, _registro):  # noqa: ANN001
        conexion.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    sesion = sessionmaker(bind=engine, autoflush=False, future=True)()
    yield sesion
    sesion.close()


@pytest.fixture()
def chroma(monkeypatch):
    from services import vectores

    cliente = ClienteFalso()
    monkeypatch.setattr(vectores, "get_client", lambda: cliente)
    monkeypatch.setattr(vectores, "embed_texts", embeddings_falsos)
    return cliente


@pytest.fixture()
def app(engine, chroma):
    from main import app as aplicacion
    from services import file_manager
    from services.cache_manager import cache

    import shutil

    shutil.rmtree(file_manager.raiz(), ignore_errors=True)
    file_manager.preparar_directorios()
    cache.invalidar()

    fabrica = sessionmaker(bind=engine, autoflush=False, future=True)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    aplicacion.dependency_overrides[get_db] = _db
    yield aplicacion
    aplicacion.dependency_overrides.clear()


@pytest.fixture()
def cliente(app):
    return TestClient(app)


@pytest.fixture()
def servicio() -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token_servicio()}"}


@pytest.fixture()
def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(1, 'administrador')}"}


@pytest.fixture()
def investigador() -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(2, 'investigador')}"}
