"""Asociación de KPIs desde el perfil semántico: fórmula, evidencia, justificación,
decisiones (aceptados y rechazados) y que la colección `kpis` solo se lee.

Embeddings falsos y deterministas (bolsa de palabras con hash), sin modelo real.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
import zlib
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICIO))
sys.path.insert(1, str(_SERVICIO.parents[1]))
os.environ.update({"SECRET_KEY": "clave-de-pruebas", "AUTH_DEV_MODE": "false"})

import numpy as np  # noqa: E402
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
from shared.models.kpi import KPI  # noqa: E402
from shared.models.kpi_inferido import KPIInferido  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.usuario import Usuario  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

DocumentoVectorizado.__table__.c.chunk_metadata.server_default = None

from app.vectorization.perfil import asociacion, justificacion, unidades  # noqa: E402

_DIM = 512


def _tokens(texto: str) -> list[str]:
    t = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-z]+", t) if len(w) > 3]


def embed_falso(textos: list[str]) -> list[list[float]]:
    salida = []
    for texto in textos:
        v = np.zeros(_DIM)
        for w in _tokens(texto):
            v[zlib.crc32(w.encode()) % _DIM] += 1.0
        n = np.linalg.norm(v)
        salida.append((v / n if n else v).tolist())
    return salida


KPIS = {
    1: ("Satisfacción estudiantil", "satisfaccion estudiantes carrera profesores docencia experiencia academica"),
    2: ("Tasa de empleabilidad", "empleo egresados trabajo mercado laboral contratacion"),
    3: ("Uso de biblioteca", "biblioteca servicios universitarios prestamos libros consulta"),
    4: ("Selectividad de admisiones", "admisiones aspirantes aceptados seleccion ingreso"),
}


class ColeccionFalsa:
    """Doble de la colección `kpis`: solo admite lecturas (falla si se escribe)."""

    def __init__(self) -> None:
        textos = [t for _, t in KPIS.values()]
        self._vectores = embed_falso(textos)
        self.lecturas = 0

    def get(self, include=None):  # noqa: ANN001
        self.lecturas += 1
        return {"ids": [str(k) for k in KPIS], "metadatas": [{"kpi_id": k, "nombre": n} for k, (n, _) in KPIS.items()],
                "embeddings": self._vectores}

    def upsert(self, *a, **k):  # pragma: no cover
        raise AssertionError("La colección kpis no se debe modificar")

    add = delete = upsert


PERFIL = {
    "esquema_version": "1.0", "instrumento_id": "INS-0007", "tipo": "encuesta",
    "titulo": "Experiencia estudiantil", "objetivo": "Conocer la satisfaccion de los estudiantes con su carrera y sus profesores.",
    "temas": ["satisfaccion", "docencia"], "palabras_clave": ["experiencia academica"], "nivel_educativo": "Licenciatura",
    "poblacion": "Estudiantes", "contexto": "Institución: Universidad Ejemplo",
    "secciones": [
        {"id": "INS-0007-s1", "nombre": "Experiencia", "preguntas": [
            {"id": "INS-0007-p01", "texto": "Satisfaccion con los profesores de la carrera"},
            {"id": "INS-0007-p02", "texto": "Satisfaccion con la experiencia academica de los estudiantes"},
            {"id": "INS-0007-p03", "texto": "¿Qué servicios universitarios usas?", "opciones": ["Biblioteca", "Cafetería"]},
        ]},
        {"id": "INS-0007-s2", "nombre": "Reactivos", "preguntas": [{"id": "INS-0007-r01", "texto": "Reactivo P1"}]},
    ],
    "kpis_asociados": [],
}


# ── Funciones puras ────────────────────────────────────────────────────────────


def test_unidades_legibles_sin_json_ni_reactivos_vacios():
    general = unidades.texto_general(PERFIL)
    assert general.splitlines()[0] == "Instrumento: Experiencia estudiantil"
    assert "Tipo: Encuesta" in general and "{" not in general
    us = unidades.unidades_pregunta(PERFIL)
    assert [u.pregunta_id for u in us] == ["INS-0007-p01", "INS-0007-p02", "INS-0007-p03"]  # «Reactivo P1» no
    assert us[2].unidad == "Sección: Experiencia\nPregunta: ¿Qué servicios universitarios usas?\nOpciones: Biblioteca, Cafetería"


def test_formula_con_vectores_controlados():
    e = np.eye(4).tolist()
    kpis = [(10, e[0]), (20, e[1]), (30, e[2])]
    general = (np.array(e[0]) + 0.5 * np.array(e[2])).tolist()
    preguntas = [("p1", e[0]), ("p2", e[0]), ("p3", (np.array(e[0]) + np.array(e[1])).tolist())]
    w = asociacion.Pesos(umbral_score=0.0)
    props = {p.kpi_id: p for p in asociacion.asociar(general, preguntas, kpis, w)}
    k10 = props[10]
    # g = 1/√1.25 ≈ 0.894; s = (1, 1, 0.707) → p = 0.902; las 3 ≥ 0.35 → c = 1
    assert k10.g == pytest.approx(0.8944, abs=1e-3) and k10.p == pytest.approx(0.9024, abs=1e-3) and k10.c == 1
    assert k10.score == pytest.approx(0.45 * 0.8944 + 0.45 * 0.9024 + 0.10, abs=1e-3)
    assert [x.pregunta_id for x in k10.evidencia] == ["p1", "p2", "p3"]
    assert k10.score > props[20].score > 0 and list(props)[0] == 10
    # KPI 20: solo p3 (0.707) lo respalda → c = 1/3; g = 0.
    assert props[20].g == 0 and props[20].c == pytest.approx(1 / 3, abs=1e-3)


def test_sin_preguntas_el_score_es_la_similitud_general():
    e = np.eye(3).tolist()
    props = asociacion.asociar(e[1], [], [(1, e[0]), (2, e[1])], asociacion.Pesos())
    assert [(p.kpi_id, p.score, p.evidencia) for p in props] == [(2, 1.0, [])]


def test_evidencia_debil_muestra_las_dos_mas_cercanas_sin_cobertura():
    v = lambda *x: (np.array(x) / np.linalg.norm(x)).tolist()  # noqa: E731
    props = asociacion.asociar(v(1, 0, 0), [("a", v(0.3, 1, 0)), ("b", v(0.2, 0, 1)), ("c", v(0, 1, 1))],
                               [(1, v(1, 0, 0))], asociacion.Pesos(umbral_score=0.0))
    assert props[0].c == 0 and [e.pregunta_id for e in props[0].evidencia] == ["a", "b"]


def test_justificacion_llm_y_respaldo_con_plantilla():
    ficha = {"nombre": "Uso de biblioteca", "definicion": "…", "que_mide": "Mide el uso…"}
    texto, origen = justificacion.justificar(ficha, "obj", ["¿Usas la biblioteca?"], usar_llm=True,
                                             generar=lambda _: {"justificacion": "La pregunta sobre servicios mide directamente el uso de la biblioteca."})
    assert origen == "llm" and texto.startswith("La pregunta")
    texto, _ = justificacion.justificar(ficha, "obj", [], usar_llm=True,
                                        generar=lambda _: {"justificacion": "Mide el &quot;uso&quot; de la biblioteca en las preguntas."})
    assert texto == 'Mide el "uso" de la biblioteca en las preguntas.'  # sin entidades HTML
    texto, origen = justificacion.justificar(ficha, "obj", ["¿Usas la biblioteca?", "¿Cuántos libros?"], usar_llm=True, generar=lambda _: None)
    assert origen == "plantilla"
    assert texto == "Se relaciona con «Uso de biblioteca» porque las preguntas «¿Usas la biblioteca?» y «¿Cuántos libros?» abordan aspectos que este indicador mide."
    assert justificacion.justificar(ficha, "", [], usar_llm=True, generar=lambda _: {"justificacion": "corto"})[1] == "plantilla"
    assert justificacion.origen_final("llm", True) == "llm_revisada"
    assert justificacion.origen_final("plantilla", True) == "plantilla_revisada"
    assert justificacion.origen_final("llm", False) == "llm"


# ── API ────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def db():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(motor, "connect")
    def _adjuntar(dbapi_conn, _):  # noqa: ANN001
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    Base.metadata.create_all(motor)
    sesion = sessionmaker(bind=motor, autoflush=False, future=True)()
    sesion.add_all([
        Usuario(usuario_id=1, nombre="Admin", email="a@x.com", password_hash="x", rol="administrador"),
        Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"),
        Usuario(usuario_id=3, nombre="Luis", email="l@x.com", password_hash="x", rol="investigador"),
    ])
    for k, (nombre, texto) in KPIS.items():
        sesion.add(KPI(kpi_id=k, nombre=nombre, texto_contexto_rag_vectorial=f"El KPI {nombre}: {texto}",
                       descripcion_ampliada_educativa=f"Mide {texto}", tipo_objetivo_estrategico="Aumentar / Mejorar"))
    raw = RawData(id_crudo=7, id_owner=2, tipo_instrumento="encuesta", nombre_archivo="e.csv", raw_archivo="raw/_/e.csv")
    sesion.add(raw)
    sesion.flush()
    sesion.add(InstrumentoProcesado(id_instrumento=70, id_crudo=7, estado="estandarizado"))
    sesion.add(VersionConocimiento(id_crudo=7, version=1, estado="perfil_aprobado", perfil=PERFIL, decisiones_kpi=[], avisos=[]))
    sesion.commit()
    yield sesion
    sesion.close()


@pytest.fixture()
def coleccion():
    return ColeccionFalsa()


@pytest.fixture()
def cliente(db, coleccion, monkeypatch):
    from app.vectorization.core import chroma_client, embeddings, llm_client

    monkeypatch.setattr(embeddings, "embed_texts", embed_falso)
    monkeypatch.setattr(chroma_client, "get_or_create_collection", lambda *a, **k: coleccion)
    monkeypatch.setattr(llm_client, "generar_json", lambda prompt, **k: None)  # LLM caído → plantilla
    from shared.db.core.config import settings

    # Con bolsa de palabras las similitudes son más bajas que con el modelo real.
    monkeypatch.setattr(settings, "KPI_SEARCH_MIN_SCORE", 0.05)
    from main import app

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _h(uid: int, rol: str = "investigador") -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(uid, rol)}"}


ANA = _h(2)


def test_propuestas_con_evidencia_y_justificacion(cliente, coleccion):
    r = cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 7}, headers=ANA)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["version"] == 1 and datos["n_preguntas"] == 3 and datos["formula"]["peso_general"] == 0.45
    primero = datos["kpis"][0]
    assert primero["nombre"] == "Satisfacción estudiantil" and primero["kpi_ref"] == "KPI-01"
    assert {e["pregunta_id"] for e in primero["evidencia"]} >= {"INS-0007-p01", "INS-0007-p02"}
    assert primero["evidencia"][0]["texto"].startswith("Satisfaccion")
    assert primero["definicion"].startswith("El KPI Satisfacción") and primero["que_mide"].startswith("Mide")
    assert primero["justificacion_origen"] == "plantilla" and "«Satisfacción estudiantil»" in primero["justificacion"]
    assert set(primero["componentes"]) == {"g", "p", "c"}
    biblioteca = next(k for k in datos["kpis"] if k["kpi_id"] == 3)
    assert biblioteca["evidencia"][0]["pregunta_id"] == "INS-0007-p03"
    assert coleccion.lecturas == 1  # solo se leyó; nunca se escribió


def test_confirmar_guarda_aceptados_y_rechazados(cliente, db):
    props = cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 7}, headers=ANA).json()["kpis"]
    acept, rech = props[0], props[1]
    cuerpo = {"id_crudo": 7, "version": 1, "decisiones": [
        {"kpi_id": acept["kpi_id"], "aceptado": True, "score": acept["score"], "componentes": acept["componentes"],
         "evidencia": [{"pregunta_id": e["pregunta_id"], "similitud": e["similitud"]} for e in acept["evidencia"]],
         "justificacion": "Mi justificación revisada.", "justificacion_origen": acept["justificacion_origen"], "editada": True},
        {"kpi_id": rech["kpi_id"], "aceptado": False, "score": rech["score"], "justificacion": rech["justificacion"]},
    ]}
    r = cliente.post("/vectorizacion/perfil/confirmar", json=cuerpo, headers=ANA)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["estado"] == "kpis_confirmados" and datos["n_rechazados"] == 1
    asociado = datos["kpis_asociados"][0]
    assert asociado["kpi_id"] == "KPI-01" and asociado["aceptado_por"] == "Ana"
    assert asociado["justificacion_origen"] == "plantilla_revisada" and asociado["justificacion"] == "Mi justificación revisada."

    db.expire_all()
    fila = db.query(VersionConocimiento).filter_by(id_crudo=7, version=1).one()
    assert fila.estado == "kpis_confirmados" and fila.fecha_kpis is not None
    assert [d["decision"] for d in fila.decisiones_kpi] == ["aceptado", "rechazado"]  # los rechazados quedan registrados…
    assert [k["kpi_id"] for k in fila.perfil["kpis_asociados"]] == ["KPI-01"]  # …pero no entran al perfil
    inferidos = db.query(KPIInferido).filter_by(id_procesado=70).all()
    assert [(i.kpi_id, i.razon) for i in inferidos] == [(1, "Mi justificación revisada.")]

    # Reconfirmar rechazando el que antes se aceptó lo quita de kpi_inferido.
    cuerpo["decisiones"] = [dict(cuerpo["decisiones"][0], aceptado=False)]
    assert cliente.post("/vectorizacion/perfil/confirmar", json=cuerpo, headers=ANA).status_code == 200
    db.expire_all()
    assert db.query(KPIInferido).filter_by(id_procesado=70).count() == 0


def test_confirmar_valida_version_kpis_y_evidencia(cliente):
    base = {"id_crudo": 7, "version": 1, "decisiones": [{"kpi_id": 1, "aceptado": True, "score": 0.5}]}
    assert cliente.post("/vectorizacion/perfil/confirmar", json=dict(base, version=2), headers=ANA).status_code == 409
    malo = dict(base, decisiones=[{"kpi_id": 99, "aceptado": True, "score": 0.5}])
    assert cliente.post("/vectorizacion/perfil/confirmar", json=malo, headers=ANA).status_code == 422
    ajena = dict(base, decisiones=[{"kpi_id": 1, "aceptado": True, "score": 0.5, "evidencia": [{"pregunta_id": "INS-0099-p01", "similitud": 0.4}]}])
    assert cliente.post("/vectorizacion/perfil/confirmar", json=ajena, headers=ANA).status_code == 422


def test_autenticacion_y_autoria(cliente):
    assert cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 7}).status_code == 401
    assert cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 7}, headers=_h(3)).status_code == 403
    assert cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 7}, headers=_h(1, "administrador")).status_code == 200
    assert cliente.post("/vectorizacion/perfil/propuestas", json={"id_crudo": 8}, headers=ANA).status_code == 404
