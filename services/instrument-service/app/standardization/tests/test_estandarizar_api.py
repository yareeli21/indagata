"""Integración: upload -> preview -> estandarizar con TestClient (diseño §1.6, §3).

Afirma que tras estandarizar:
  - el estado del instrumento es 'estandarizado' y hay ruta_json;
  - GET /instrumentos NO devuelve el título del seed inst_01.v1.json (Bug 5),
    sino el derivado del upload real.

Se usa SQLite en memoria con el schema `tt_rag` ATTACHado (los modelos ORM
declaran schema='tt_rag') y un storage falso en memoria. No requiere Postgres,
Chroma ni Ollama.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.dependencies import get_current_user
from app.storage.port import StoredRef
from shared.db.base import Base
from shared.db.session import get_db
from shared.models.raw_data import RawData

# Importa todos los modelos para que Base.metadata los conozca al crear tablas.
import shared.models  # noqa: F401


CSV_CONTENIDO = (
    "edad,claridad,comentario\n"
    "18,4,me gusta\n"
    "22,1,regular\n"
    "30,5,excelente\n"
    "25,3,bueno\n"
).encode("utf-8")


class _FakeStorage:
    """Backend de storage en memoria (dict ruta -> bytes)."""

    def __init__(self) -> None:
        self._datos: dict[str, bytes] = {}
        self._contador = 0

    def guardar(self, content: bytes, nombre_original: str) -> StoredRef:
        self._contador += 1
        ruta = f"raw/fake{self._contador}__{nombre_original}"
        self._datos[ruta] = content
        return StoredRef(nombre_original=nombre_original, ruta=ruta, size_bytes=len(content))

    def leer(self, ruta: str) -> bytes:
        return self._datos[ruta]

    def eliminar(self, ruta: str) -> None:
        self._datos.pop(ruta, None)


class _UsuarioFalso:
    usuario_id = 1
    rol = "administrador"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # ── Motor SQLite con schema tt_rag ATTACHado ─────────────────────────────
    # StaticPool + una sola conexión compartida: el ATTACH ':memory:' es por
    # conexión, así que todas (create_all y las sesiones) deben compartirla.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach_schema(dbapi_conn, _rec):  # noqa: ANN001
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    # Solo las tablas que toca este flujo (otras usan tipos Postgres como JSONB
    # que SQLite no compila).
    from shared.models.instrumento_procesado import InstrumentoProcesado
    from shared.models.usuario import Usuario

    Base.metadata.create_all(
        engine,
        tables=[
            Usuario.__table__,
            RawData.__table__,
            InstrumentoProcesado.__table__,
        ],
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # ── Sembrar un seed inst_01 + _seed_map.json en un storage/raw temporal ──
    # Para que, si Bug 5 regresara, GET /instrumentos devolviera el título del
    # seed. Con el fix, el upload real resuelve por ruta_json y NO toma el seed.
    from shared.db.core import config as cfg

    raw_dir = tmp_path / "storage" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "inst_01.v1.json").write_text(
        '{"instrument": {"title": "TITULO DEL SEED INST_01"}}', encoding="utf-8"
    )
    # NO escribimos _seed_map.json: así el seed no se mapea a ningún id_crudo.
    # RAW_PATH absoluto -> settings.raw_path_abs apunta al dir temporal.
    monkeypatch.setattr(cfg.settings, "RAW_PATH", str(raw_dir))

    fake_storage = _FakeStorage()
    # El servicio llama get_storage() en runtime; se reemplaza en ambos módulos.
    monkeypatch.setattr("app.storage.get_storage", lambda: fake_storage)
    monkeypatch.setattr(
        "app.services.standardization_service.get_storage", lambda: fake_storage
    )
    monkeypatch.setattr("app.services.upload_service.get_storage", lambda: fake_storage)

    def _get_db_override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = _get_db_override
    main.app.dependency_overrides[get_current_user] = lambda: _UsuarioFalso()

    with TestClient(main.app) as c:
        # Un usuario real debe existir para la FK de raw_data.id_owner.
        db = TestSession()
        from shared.models.usuario import Usuario

        db.add(
            Usuario(
                usuario_id=1,
                nombre="Admin",
                email="admin@test.local",
                password_hash="x",
                rol="administrador",
            )
        )
        db.commit()
        db.close()
        yield c

    main.app.dependency_overrides.clear()


def test_flujo_upload_preview_estandarizar(client):
    # ── Upload ───────────────────────────────────────────────────────────────
    resp = client.post(
        "/instrumentos/upload",
        files={"archivo": ("encuesta.csv", io.BytesIO(CSV_CONTENIDO), "text/csv")},
        data={"tipo_instrumento": "encuesta"},
    )
    assert resp.status_code == 201, resp.text
    id_crudo = resp.json()["id_crudo"]

    # ── Preview ───────────────────────────────────────────────────────────────
    prev = client.post(f"/instrumentos/{id_crudo}/estandarizar/preview")
    assert prev.status_code == 200, prev.text
    cuerpo = prev.json()
    assert cuerpo["n_respondentes_detectados"] == 4
    textos = {p["text"]: p for p in cuerpo["preguntas"]}
    assert textos["edad"]["es_demografica"] is True
    assert textos["claridad"]["type"] == "likert"

    # ── Estandarizar con los tipos confirmados ────────────────────────────────
    payload = {
        "preguntas": [
            {"question_id": "q1", "text": "edad", "type": "numerica_continua",
             "es_demografica": True},
            {"question_id": "q2", "text": "claridad", "type": "likert",
             "scale_min": 1, "scale_max": 5},
            {"question_id": "q3", "text": "comentario", "type": "abierta"},
        ]
    }
    est = client.post(f"/instrumentos/{id_crudo}/estandarizar", json=payload)
    assert est.status_code == 200, est.text
    datos = est.json()
    assert datos["estado"] == "estandarizado"
    assert datos["ruta_json"].startswith("storage/")
    # El JSON de dominio excluye la demográfica de las preguntas.
    questions = datos["json_instrumento"]["instrument"]["sections"][0]["questions"]
    assert [q["question_id"] for q in questions] == ["q2", "q3"]

    # ── GET /instrumentos NO devuelve el título del seed (Bug 5) ──────────────
    listado = client.get("/instrumentos")
    assert listado.status_code == 200, listado.text
    titulos = [i["titulo"] for i in listado.json()]
    assert "TITULO DEL SEED INST_01" not in titulos
    # El título degrada al nombre de archivo del upload real.
    assert "encuesta.csv" in titulos


# ── Regresión del fix: resolución por question_id ─────────────────────────────

# Headers que normalizan a la MISMA clave (duplicados/sucios): antes del fix el
# match por nombre fallaba porque `_mapa_headers` desambigua con sufijo '__2' en
# la clave pero no en el `text` del preview.
CSV_HEADERS_DUPLICADOS = (
    "Organizacion y  item1,Organizacion_y__item1,comentario\n"
    "4,2,me gusta\n"
    "1,5,regular\n"
    "5,3,excelente\n"
).encode("utf-8")


def test_estandarizar_resuelve_por_question_id_con_headers_duplicados(client):
    """Headers que colisionan al normalizar: el mapeo por question_id funciona.

    Antes del fix esto devolvía 422 porque el `text` crudo del preview no
    igualaba la clave desambiguada ('..._item1__2').
    """
    resp = client.post(
        "/instrumentos/upload",
        files={"archivo": ("dup.csv", io.BytesIO(CSV_HEADERS_DUPLICADOS), "text/csv")},
        data={"tipo_instrumento": "encuesta"},
    )
    assert resp.status_code == 201, resp.text
    id_crudo = resp.json()["id_crudo"]

    prev = client.post(f"/instrumentos/{id_crudo}/estandarizar/preview")
    assert prev.status_code == 200, prev.text
    preguntas_preview = prev.json()["preguntas"]
    # Los tres question_id del preview deben ser q1, q2, q3 (estables por columna).
    assert [p["question_id"] for p in preguntas_preview] == ["q1", "q2", "q3"]

    # Reenviar CADA pregunta del preview tal cual (incluyendo el question_id).
    payload = {
        "preguntas": [
            {
                "question_id": p["question_id"],
                "text": p["text"],
                "type": p["type"],
                "options": p.get("options"),
                "scale_min": p.get("scale_min"),
                "scale_max": p.get("scale_max"),
                "es_demografica": p.get("es_demografica", False),
            }
            for p in preguntas_preview
        ]
    }
    est = client.post(f"/instrumentos/{id_crudo}/estandarizar", json=payload)
    assert est.status_code == 200, est.text
    datos = est.json()
    assert datos["estado"] == "estandarizado"
    questions = datos["json_instrumento"]["instrument"]["sections"][0]["questions"]
    # Ninguna es demográfica: las tres columnas quedan como preguntas.
    assert [q["question_id"] for q in questions] == ["q1", "q2", "q3"]


def test_estandarizar_question_id_fuera_de_rango_devuelve_422(client):
    """Un question_id que parsea pero cae fuera de rango -> 422 con id y text."""
    resp = client.post(
        "/instrumentos/upload",
        files={"archivo": ("encuesta.csv", io.BytesIO(CSV_CONTENIDO), "text/csv")},
        data={"tipo_instrumento": "encuesta"},
    )
    assert resp.status_code == 201, resp.text
    id_crudo = resp.json()["id_crudo"]

    payload = {
        "preguntas": [
            {"question_id": "q99", "text": "edad", "type": "numerica_continua",
             "es_demografica": True},
        ]
    }
    est = client.post(f"/instrumentos/{id_crudo}/estandarizar", json=payload)
    assert est.status_code == 422, est.text
    detalle = est.json()["detail"]
    assert "q99" in detalle
    assert "edad" in detalle


def test_estandarizar_fallback_por_nombre_sin_question_id(client):
    """Sin question_id parseable, el fallback por nombre único resuelve (200)."""
    resp = client.post(
        "/instrumentos/upload",
        files={"archivo": ("encuesta.csv", io.BytesIO(CSV_CONTENIDO), "text/csv")},
        data={"tipo_instrumento": "encuesta"},
    )
    assert resp.status_code == 201, resp.text
    id_crudo = resp.json()["id_crudo"]

    # question_id vacío (no parsea) -> fallback por nombre normalizado del header.
    payload = {
        "preguntas": [
            {"question_id": "", "text": "edad", "type": "numerica_continua",
             "es_demografica": True},
            {"question_id": "", "text": "claridad", "type": "likert",
             "scale_min": 1, "scale_max": 5},
            {"question_id": "", "text": "comentario", "type": "abierta"},
        ]
    }
    est = client.post(f"/instrumentos/{id_crudo}/estandarizar", json=payload)
    assert est.status_code == 200, est.text
    assert est.json()["estado"] == "estandarizado"
