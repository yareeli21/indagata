"""Fixtures de prueba del metadata-service.

- BD: SQLite en memoria con el esquema `tt_rag` adjunto.
- storage-service y Ollama: dobles en memoria (sin red).

Ejecutar desde la carpeta del servicio:  python -m pytest tests
"""
from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
_REPO = _SERVICIO.parents[1]
sys.path.insert(0, str(_SERVICIO))
sys.path.insert(1, str(_REPO))
# METADATA_EXIGIR_LIMPIEZA=false: las pruebas clásicas analizan el archivo crudo; las de
# integración con la limpieza lo activan con monkeypatch.
os.environ.update(
    {"SECRET_KEY": "clave-de-pruebas", "DEBUG": "false", "METADATA_USAR_LLM": "false", "METADATA_EXIGIR_LIMPIEZA": "false"}
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


import shared.models  # noqa: E402,F401
from shared.auth import crear_access_token  # noqa: E402
from shared.db.base import Base  # noqa: E402
from shared.db.session import get_db  # noqa: E402
from shared.models.documento_vectorizado import DocumentoVectorizado  # noqa: E402
from shared.models.instrumento_procesado import InstrumentoProcesado  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.usuario import Usuario  # noqa: E402

DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None


class StorageFalso:
    """Doble del storage-service (mismas firmas que services.storage_client)."""

    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}
        self.json: dict[tuple[int, str], list[dict]] = {}
        self.indexados: list[int] = []
        self.desindexados: list[int] = []
        self.fallar_indice = False

    def tabla(self, ruta: str, max_filas: int = 20000) -> dict:
        # Como el storage real: UTF-8 con o sin BOM y delimitador , o ; (el CSV limpio usa ;).
        texto = self.archivos[ruta].decode("utf-8-sig")
        primera = texto.splitlines()[0] if texto else ""
        delimitador = ";" if primera.count(";") > primera.count(",") else ","
        filas = list(csv.reader(io.StringIO(texto), delimiter=delimitador))
        cuerpo = [f for f in filas[1:] if any(c.strip() for c in f)]
        return {"headers": filas[0], "rows": cuerpo, "n_filas": len(cuerpo), "notas": [], "truncado": False}

    def texto(self, ruta: str) -> dict:
        return {"texto": self.archivos[ruta].decode("utf-8")}

    def descargar(self, ruta: str) -> bytes:
        return self.archivos[ruta]

    def guardar_json(self, id_crudo: int, tipo: str, contenido: dict, nombre: str) -> dict:
        versiones = self.json.setdefault((id_crudo, tipo), [])
        versiones.append(contenido)
        v = len(versiones)
        return {
            "key": f"{tipo}/{id_crudo}/{v}__x.json",
            "version": v,
            "ruta_absoluta": f"/app/storage/json/{id_crudo}/{v}__x.json",
        }

    def obtener_json(self, id_crudo: int, tipo: str) -> dict | None:
        versiones = self.json.get((id_crudo, tipo))
        return versiones[-1] if versiones else None

    def indexar(self, id_crudo: int, reindexar: bool = True) -> dict:
        from services.storage_client import StorageError

        if self.fallar_indice:
            raise StorageError("Vector store no disponible.", 502)
        self.indexados.append(id_crudo)
        return {"estado": "indexado", "chunks": 7}

    def desindexar(self, id_crudo: int) -> dict:
        self.desindexados.append(id_crudo)
        return {"vectores_eliminados": 7}


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
def db(engine):
    sesion = sessionmaker(bind=engine, autoflush=False, future=True)()
    yield sesion
    sesion.close()


@pytest.fixture()
def storage(monkeypatch):
    from services import analizador, propuestas, storage_client

    falso = StorageFalso()
    for nombre in ("tabla", "texto", "descargar", "guardar_json", "obtener_json", "indexar", "desindexar"):
        monkeypatch.setattr(storage_client, nombre, getattr(falso, nombre))
    analizador.limpiar_cache()
    propuestas.limpiar_cache()
    return falso


@pytest.fixture()
def llm(monkeypatch):
    """Doble de Ollama: registra las peticiones y responde lo configurado."""
    from services import llm_client

    estado = {"respuesta": {}, "llamadas": []}

    def sugerir(tipo_ui, titulo, contexto, campos):  # noqa: ANN001
        estado["llamadas"].append(set(campos))
        return {k: v for k, v in estado["respuesta"].items() if k in campos}

    monkeypatch.setattr(llm_client, "sugerir", sugerir)
    return estado


@pytest.fixture()
def cliente(engine, storage, llm):
    from main import app

    fabrica = sessionmaker(bind=engine, autoflush=False, future=True)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def usuarios(db):
    db.add_all(
        [
            Usuario(usuario_id=1, nombre="Admin", email="admin@x.com", password_hash="x", rol="administrador"),
            Usuario(usuario_id=2, nombre="Ana Beltrán", email="ana@x.com", password_hash="x", rol="investigador"),
            Usuario(usuario_id=3, nombre="Luis", email="luis@x.com", password_hash="x", rol="investigador"),
        ]
    )
    db.commit()


def token(usuario_id: int, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(usuario_id, rol)}"}


@pytest.fixture()
def ana(usuarios):
    return token(2, "investigador")


@pytest.fixture()
def luis(usuarios):
    return token(3, "investigador")


@pytest.fixture()
def admin(usuarios):
    return token(1, "administrador")


@pytest.fixture()
def crear_instrumento(db, storage, usuarios):
    """Registra un instrumento de Ana (raw_data + instrumento_procesado) con su archivo."""

    def _crear(nombre: str, contenido: str, tipo: str = "encuesta", id_owner: int = 2) -> int:
        ruta = f"raw/_/{len(storage.archivos) + 1}__{nombre}"
        storage.archivos[ruta] = contenido.encode("utf-8")
        raw = RawData(id_owner=id_owner, tipo_instrumento=tipo, nombre_archivo=nombre, raw_archivo=ruta)
        db.add(raw)
        db.flush()
        db.add(InstrumentoProcesado(id_crudo=raw.id_crudo, estado="recibido"))
        db.commit()
        return raw.id_crudo

    return _crear


@pytest.fixture()
def crear_limpieza(db, storage):
    """Registra una limpieza CONFIRMADA (cleaning-service) con su CSV limpio en storage."""
    from shared.models.limpieza_ejecucion import LimpiezaEjecucion

    def _crear(id_crudo: int, csv_limpio: str, reporte: dict, version: int = 1) -> str:
        ruta = f"clean/{id_crudo}/{version}__v{version}_limpio.csv"
        storage.archivos[ruta] = csv_limpio.encode("utf-8-sig")
        db.add(
            LimpiezaEjecucion(
                id_crudo=id_crudo, version=version, estado="confirmada", ruta_csv_limpio=ruta, reporte=reporte
            )
        )
        db.commit()
        return ruta

    return _crear
