"""Fixtures de prueba del visualization-service.

- BD: SQLite en memoria con el esquema `tt_rag` adjunto.
- ChromaDB, embeddings, storage-service y Ollama: dobles en memoria.

Ejecutar desde la carpeta del servicio:  python -m pytest tests
"""
from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
_REPO = _SERVICIO.parents[1]
sys.path.insert(0, str(_SERVICIO))
sys.path.insert(1, str(_REPO))
os.environ.update({"SECRET_KEY": "clave-de-pruebas", "DEBUG": "false"})

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


import shared.models  # noqa: E402,F401
from shared.auth import crear_access_token  # noqa: E402
from shared.db.base import Base  # noqa: E402
from shared.db.session import get_db  # noqa: E402
from shared.models.documento_vectorizado import DocumentoVectorizado  # noqa: E402

DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None


def vector_de(texto: str) -> list[float]:
    """Embedding falso determinista: bolsa de palabras en 16 dimensiones."""
    v = [0.0] * 16
    for palabra in texto.lower().split():
        v[int(hashlib.md5(palabra.encode()).hexdigest(), 16) % 16] += 1.0
    norma = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norma for x in v]


def _coincide(meta: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_coincide(meta, w) for w in where["$and"])
    for clave, cond in where.items():
        valor = meta.get(clave)
        if isinstance(cond, dict):
            if "$in" in cond and valor not in cond["$in"]:
                return False
        elif valor != cond:
            return False
    return True


class ColeccionFalsa:
    def __init__(self, nombre: str) -> None:
        self.name = nombre
        self.puntos: dict[str, dict] = {}
        self.consultas: list[dict] = []

    def agregar(self, pid: str, texto: str, meta: dict, embedding: list[float] | None = None) -> None:
        self.puntos[pid] = {"document": texto, "metadata": meta, "embedding": embedding or vector_de(texto)}

    def get(self, ids=None, where=None, include=None):  # noqa: ANN001
        sel = [(i, p) for i, p in self.puntos.items() if (ids is None or i in ids) and _coincide(p["metadata"], where)]
        return {
            "ids": [i for i, _ in sel],
            "embeddings": [p["embedding"] for _, p in sel],
            "metadatas": [p["metadata"] for _, p in sel],
            "documents": [p["document"] for _, p in sel],
        }

    def query(self, query_embeddings, n_results, where=None, include=None):  # noqa: ANN001
        self.consultas.append({"where": where, "n_results": n_results})
        q = query_embeddings[0]
        candidatos = [p for p in self.puntos.values() if _coincide(p["metadata"], where)]
        candidatos.sort(key=lambda p: -sum(a * b for a, b in zip(q, p["embedding"])))
        top = candidatos[:n_results]
        return {
            "metadatas": [[p["metadata"] for p in top]],
            "documents": [[p["document"] for p in top]],
            "distances": [[1 - sum(a * b for a, b in zip(q, p["embedding"])) for p in top]],
        }


class ClienteFalso:
    def __init__(self) -> None:
        self.colecciones: dict[str, ColeccionFalsa] = {}

    def crear(self, nombre: str) -> ColeccionFalsa:
        return self.colecciones.setdefault(nombre, ColeccionFalsa(nombre))

    def list_collections(self):
        return list(self.colecciones.values())

    def get_or_create_collection(self, name, metadata=None):  # noqa: ANN001
        return self.crear(name)


class StorageFalso:
    def __init__(self) -> None:
        self.archivos: dict[str, tuple[bytes, str]] = {}
        self.json: dict[tuple[int, str], dict] = {}
        self.tablas: dict[str, dict] = {}
        self.guardados: list[tuple] = []
        self.indice: dict[int, dict] = {}

    def descargar(self, ruta):  # noqa: ANN001
        from services.storage_client import Descarga, StorageError

        if ruta not in self.archivos:
            raise StorageError("Archivo no encontrado.", 404)
        contenido, nombre = self.archivos[ruta]
        return Descarga(contenido=contenido, nombre=nombre, mime_type="text/csv", sha256=None)

    def tabla(self, ruta, max_filas=200000):  # noqa: ANN001
        return self.tablas[ruta]

    def obtener_json(self, id_crudo, tipo):  # noqa: ANN001
        return self.json.get((id_crudo, tipo))

    def ultimo_artefacto(self, id_crudo, tipo):  # noqa: ANN001
        return None

    def guardar_archivo(self, id_crudo, tipo, nombre, contenido):  # noqa: ANN001
        self.guardados.append((id_crudo, tipo, nombre, contenido))
        return {"key": f"{tipo}/{id_crudo}/1__{nombre}"}

    def estado_indice(self, id_crudo):  # noqa: ANN001
        return self.indice.get(id_crudo, {"indexado": False, "chunks": 0})

    def indexar(self, id_crudo, reindexar=True):  # noqa: ANN001
        from services.storage_client import StorageError

        if id_crudo not in self.indice:
            raise StorageError("Los metadatos del instrumento no han sido aprobados por su autor.", 409)
        return {"estado": "indexado", "chunks": self.indice[id_crudo]["chunks"]}


@pytest.fixture(autouse=True)
def _sin_cache_de_respuestas(monkeypatch):
    """Las pruebas repiten preguntas a propósito: la caché se prueba aparte (test_cache.py)."""
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_CACHE_HORAS", 0)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _adjuntar(conexion, _registro):  # noqa: ANN001
        conexion.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def fabrica(engine):
    return sessionmaker(bind=engine, autoflush=False, future=True)


@pytest.fixture()
def db(fabrica):
    sesion = fabrica()
    yield sesion
    sesion.close()


@pytest.fixture()
def chroma(monkeypatch):
    from services import query_engine, vectores

    cliente = ClienteFalso()
    monkeypatch.setattr(vectores, "get_client", lambda: cliente)
    monkeypatch.setattr(vectores, "embed_texts", lambda textos: [vector_de(t) for t in textos])
    query_engine._kpi_vectores.clear()
    return cliente


@pytest.fixture()
def storage(monkeypatch):
    from services import storage_client

    falso = StorageFalso()
    for nombre in ("descargar", "tabla", "obtener_json", "ultimo_artefacto", "guardar_archivo", "estado_indice", "indexar"):
        monkeypatch.setattr(storage_client, nombre, getattr(falso, nombre))
    return falso


@pytest.fixture()
def ollama(monkeypatch):
    from services import ollama_client

    # `clasificador`: veredicto del clasificador de dominio de la zona gris (llamada con formato JSON).
    estado = {"prompts": [], "sistemas": [], "clasificaciones": [], "clasificador": {"dentro": True, "motivo": "prueba"}}

    async def no_stream(prompt, modelo, sistema=None, *, formato=None, opciones=None):  # noqa: ANN001
        if formato == "json":
            estado["clasificaciones"].append(prompt)
            import json as _json

            return _json.dumps(estado["clasificador"]), False
        estado["prompts"].append(prompt)
        estado["sistemas"].append(sistema)
        return "Respuesta fundamentada [Fuente 1].", False

    async def stream(prompt, modelo, sistema=None):  # noqa: ANN001
        estado["prompts"].append(prompt)
        estado["sistemas"].append(sistema)
        for trozo in ("Hola ", "mundo"):
            yield trozo

    monkeypatch.setattr(ollama_client, "generar_no_stream", no_stream)
    monkeypatch.setattr(ollama_client, "generar_stream", stream)
    return estado


@pytest.fixture()
def cliente(engine, fabrica, chroma, storage, ollama, monkeypatch):
    from main import app
    from services import rag_service

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    monkeypatch.setattr(rag_service, "fabrica_sesiones", fabrica)
    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()


def token(usuario_id: int, rol: str = "investigador") -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(usuario_id, rol)}"}
