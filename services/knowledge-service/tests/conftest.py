"""Fixtures de prueba del knowledge-service.

- BD: SQLite en memoria con el esquema `tt_rag` adjunto (ATTACH), creada desde los
  modelos de `shared` (JSONB se compila como JSON).
- storage-service: doble en memoria (`StorageFalso`), sin red.
- Limpiezas: `tests/datos/limpieza_<tipo>.json`, generadas con los motores REALES de
  cleaning-service (`tests/datos/generar_limpiezas.py`).
- Usuarios: 1 = admin, 2 = Ana (autora), 3 = Luis (otro investigador).

Ejecutar desde la carpeta del servicio:  python -m pytest tests
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

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
from shared.models.metadatos_dc import MetadatosDC  # noqa: E402
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas  # noqa: E402
from shared.models.metadatos_entrevistas import MetadatosEnriquecidosEntrevistas  # noqa: E402
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.usuario import Usuario  # noqa: E402

# El DEFAULT '{}'::jsonb es sintaxis de Postgres; en SQLite se omite.
DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None

DATOS = Path(__file__).resolve().parent / "datos"


def limpieza(tipo: str) -> dict[str, Any]:
    """{"reporte": …, "csv": {"headers", "rows"}} generado con los motores de cleaning-service."""
    return json.loads((DATOS / f"limpieza_{tipo}.json").read_text(encoding="utf-8"))


def texto_dato(nombre: str) -> str:
    return (DATOS / nombre).read_text(encoding="utf-8")


class StorageFalso:
    """Doble del storage-service: tablas, textos y JSON en memoria."""

    def __init__(self) -> None:
        self.tablas: dict[str, dict[str, Any]] = {}
        self.textos: dict[str, str] = {}
        self.jsons: dict[tuple[int, str], dict[str, Any]] = {}
        self.guardados: dict[str, dict[str, Any]] = {}
        self.indexados: list[int] = []
        self.caido = False
        self.indice_caido = False

    def _revisar(self, ruta: str, almacen: dict) -> None:  # noqa: ANN001
        from services.storage_client import StorageError

        if self.caido:
            raise StorageError("El servicio de almacenamiento no está disponible.")
        if ruta not in almacen:
            raise StorageError("No existe el artefacto.", 404)

    def tabla(self, ruta: str, max_filas: int = 50000) -> dict[str, Any]:
        self._revisar(ruta, self.tablas)
        return self.tablas[ruta]

    def texto(self, ruta: str) -> str:
        self._revisar(ruta, self.textos)
        return self.textos[ruta]

    def obtener_json(self, id_crudo: int, tipo: str) -> dict[str, Any] | None:
        return self.jsons.get((id_crudo, tipo))

    def guardar_json(self, id_crudo: int, tipo: str, contenido: dict[str, Any], nombre: str) -> dict[str, Any]:
        from services.storage_client import StorageError

        if self.caido:
            raise StorageError("El servicio de almacenamiento no está disponible.")
        n = sum(1 for k in self.guardados if k.startswith(f"{tipo}/{id_crudo}/")) + 1
        key = f"{tipo}/{id_crudo}/{n}__{nombre}.json"
        self.guardados[key] = json.loads(json.dumps(contenido))
        return {"key": key, "version": n, "sha256": f"sha-{n}"}

    def descargar_json(self, ruta: str) -> dict[str, Any]:
        self._revisar(ruta, self.guardados)
        return self.guardados[ruta]

    def indexar(self, id_crudo: int) -> dict[str, Any]:
        from services.storage_client import StorageError

        if self.caido or self.indice_caido:
            raise StorageError("El servicio de almacenamiento no está disponible.")
        self.indexados.append(id_crudo)
        return {"instrumentoId": str(id_crudo), "chunks": 1, "estado": "indexado"}


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
    monkeypatch.setattr(storage_client, "tabla", falso.tabla)
    monkeypatch.setattr(storage_client, "texto", falso.texto)
    monkeypatch.setattr(storage_client, "obtener_json", falso.obtener_json)
    monkeypatch.setattr(storage_client, "guardar_json", falso.guardar_json)
    monkeypatch.setattr(storage_client, "descargar_json", falso.descargar_json)
    monkeypatch.setattr(storage_client, "indexar", falso.indexar)
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

METADATOS = {
    "encuesta": (
        {"dc_title": "Experiencia estudiantil 2026", "dc_subject": "experiencia estudiantil, satisfacción",
         "dc_description": "Encuesta sobre la experiencia en la carrera.", "dc_coverage": "Licenciatura — Ciudad de México, 2026",
         "dc_publisher": "Universidad Ejemplo"},
        {"objetivo": "Conocer la satisfacción de los estudiantes con su carrera.", "poblacion_objetivo": "Estudiantes de licenciatura",
         "carrera": "Pedagogía", "constructo_principal": "Satisfacción académica", "palabras_clave": ["satisfacción", "carrera"],
         "dimensiones": ["Docencia", "Infraestructura"], "n_respondentes": 20},
    ),
    "entrevista": (
        {"dc_title": "Entrevistas sobre evaluación", "dc_subject": "evaluación, retroalimentación", "dc_coverage": "Licenciatura"},
        {"objetivo": "Explorar percepciones sobre la evaluación.", "metodologia": "Semiestructurada", "institucion": "Universidad Ejemplo"},
    ),
    "prueba_estandarizada": (
        {"dc_title": "Diagnóstico de matemáticas", "dc_subject": "aritmética, álgebra", "dc_coverage": "Bachillerato"},
        {"objetivo_de_evaluacion": "Diagnosticar habilidades matemáticas básicas.", "nivel_educativo": "Media superior",
         "unidad_de_aprendizaje": "Matemáticas I", "tipo_de_prueba": "Diagnóstica", "subareas": "Aritmética, Álgebra"},
    ),
}
_TABLA_ESP = {
    "encuesta": MetadatosEnriquecidosEncuestas,
    "entrevista": MetadatosEnriquecidosEntrevistas,
    "prueba_estandarizada": MetadatosEnriquecidosPruebas,
}


def crear_instrumento(
    db,
    storage: StorageFalso,
    tipo: str = "encuesta",
    *,
    original: str | None = None,
    con_limpieza: bool = True,
    aprobado: bool = False,
    id_owner: int = 2,
) -> int:
    """raw_data + instrumento_procesado (+ limpieza confirmada, original y metadatos aprobados)."""
    raw = RawData(id_owner=id_owner, tipo_instrumento=tipo, nombre_archivo=f"{tipo}.csv", raw_archivo=f"raw/_/{tipo}.csv")
    db.add(raw)
    db.flush()
    if original:
        raw.raw_archivo_original = f"raw/_/{raw.id_crudo}__original.txt"
        storage.textos[raw.raw_archivo_original] = texto_dato(original)
    db.add(InstrumentoProcesado(id_crudo=raw.id_crudo, estado="limpio" if con_limpieza else "estandarizado"))
    if con_limpieza:
        datos = limpieza(tipo)
        ruta = f"clean/{raw.id_crudo}/1__v1_{tipo}_limpio.csv"
        storage.tablas[ruta] = dict(datos["csv"], n_filas=len(datos["csv"]["rows"]))
        db.add(LimpiezaEjecucion(id_crudo=raw.id_crudo, version=1, estado="confirmada", ruta_csv_limpio=ruta, reporte=datos["reporte"]))
    if aprobado:
        dc, esp = METADATOS[tipo]
        db.add(MetadatosDC(id_crudo=raw.id_crudo, **dc))
        db.add(_TABLA_ESP[tipo](id_crudo=raw.id_crudo, **esp))
    db.commit()
    return raw.id_crudo


def csv_de(filas: list[list[str]]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(filas)
    return buffer.getvalue()
