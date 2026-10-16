"""Fixtures de prueba del cleaning-service.

- BD: SQLite en memoria con el esquema `tt_rag` adjunto (ATTACH), creada desde los
  modelos de `shared` (JSONB se compila como JSON).
- storage-service: doble en memoria (`StorageFalso`), sin red.
- Usuarios: 1 = admin, 2 = Ana (autora), 3 = Luis (otro investigador).

Ejecutar desde la carpeta del servicio:  python -m pytest tests
"""
from __future__ import annotations

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


import shared.models  # noqa: E402,F401  (registra todas las tablas)
from shared.auth import crear_access_token  # noqa: E402
from shared.db.base import Base  # noqa: E402
from shared.db.session import get_db  # noqa: E402
from shared.models.documento_vectorizado import DocumentoVectorizado  # noqa: E402
from shared.models.instrumento_procesado import InstrumentoProcesado  # noqa: E402
from shared.models.limpieza_ejecucion import LimpiezaEjecucion  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.usuario import Usuario  # noqa: E402

# El DEFAULT '{}'::jsonb es sintaxis de Postgres; en SQLite se omite.
DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None


class StorageFalso:
    """Doble del storage-service: archivos en un dict {key: bytes}."""

    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}
        self.versiones: dict[int, int] = {}
        self.fallar_guardado = False

    def descargar(self, ruta: str) -> bytes:
        from services.storage_client import StorageError

        if ruta not in self.archivos:
            raise StorageError("No existe el artefacto.", 404)
        return self.archivos[ruta]

    def guardar_limpio(self, id_crudo: int, nombre: str, contenido: bytes) -> str:
        from services.storage_client import StorageError

        if self.fallar_guardado:
            raise StorageError("El servicio de almacenamiento no está disponible.")
        self.versiones[id_crudo] = self.versiones.get(id_crudo, 0) + 1
        key = f"clean/{id_crudo}/{self.versiones[id_crudo]}__{nombre}"
        self.archivos[key] = contenido
        return key


@pytest.fixture()
def engine():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(motor, "connect")
    def _adjuntar(dbapi_conn, _):  # noqa: ANN001
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    Base.metadata.create_all(motor)
    return motor


@pytest.fixture()
def db(engine):
    sesion = sessionmaker(bind=engine, autoflush=False, future=True)()
    sesion.add_all(
        [
            Usuario(usuario_id=1, nombre="Admin", email="admin@x.com", password_hash="x", rol="administrador"),
            Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"),
            Usuario(usuario_id=3, nombre="Luis", email="luis@x.com", password_hash="x", rol="investigador"),
        ]
    )
    sesion.commit()
    yield sesion
    sesion.close()


@pytest.fixture()
def storage(monkeypatch):
    from services import storage_client

    falso = StorageFalso()
    monkeypatch.setattr(storage_client, "descargar", falso.descargar)
    monkeypatch.setattr(storage_client, "guardar_limpio", falso.guardar_limpio)
    return falso


@pytest.fixture()
def cliente(db, storage):
    from main import app

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def token(usuario_id: int, rol: str = "investigador") -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(usuario_id, rol)}"}


ANA = token(2)
LUIS = token(3)
ADMIN = token(1, "administrador")


def crear_instrumento(
    db,
    storage: StorageFalso,
    nombre: str,
    contenido: bytes,
    tipo: str = "encuesta",
    id_owner: int = 2,
    clave: tuple[str, bytes] | None = None,
) -> int:
    """Crea raw_data + instrumento_procesado con el crudo en el storage falso."""
    n = len(storage.archivos) + 1
    ruta = f"raw/_/{n}__{nombre}"
    storage.archivos[ruta] = contenido
    ruta_clave = None
    if clave:
        ruta_clave = f"raw/_/{n}c__{clave[0]}"
        storage.archivos[ruta_clave] = clave[1]
    raw = RawData(
        id_owner=id_owner,
        tipo_instrumento=tipo,
        nombre_archivo=nombre,
        raw_archivo=ruta,
        raw_archivo_clave=ruta_clave,
    )
    db.add(raw)
    db.flush()
    db.add(InstrumentoProcesado(id_crudo=raw.id_crudo, estado="recibido"))
    db.commit()
    return raw.id_crudo
