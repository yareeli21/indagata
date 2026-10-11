"""Integración ligera de POST /rag/index sobre el inst_1 real (FEAT-002).

Mockea embeddings (vectores dummy) y Chroma (captura ids/documents/metadatas sin
servidor). El artefacto JSON se inyecta leyendo el real de storage/raw/; el .txt
original se resuelve por el fallback de disco (BD forzada a no disponible), para
no depender de PostgreSQL ni de Chroma/Ollama vivos.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import chroma_client, embeddings, original_txt, sources
from app.routers import rag

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _cargar_inst_1() -> dict | None:
    patron = str(_REPO_ROOT / "storage" / "raw" / "*inst_1.estandarizado.v1.json")
    archivos = glob.glob(patron)
    if not archivos:
        return None
    with open(archivos[0], encoding="utf-8") as fh:
        return json.load(fh)


class _ColeccionFake:
    """Captura lo que se le hace upsert para poder afirmar sobre ello."""

    def __init__(self) -> None:
        self.ids: list[str] = []
        self.documents: list[str] = []
        self.metadatas: list[dict] = []

    def upsert(self, ids, embeddings, documents, metadatas):  # noqa: A002
        self.ids = ids
        self.documents = documents
        self.metadatas = metadatas


class _ClienteFake:
    def __init__(self, coleccion: _ColeccionFake) -> None:
        self._col = coleccion

    def delete_collection(self, name):  # pragma: no cover - no reindexa aquí
        pass

    def get_or_create_collection(self, name, metadata=None):
        return self._col


@pytest.fixture
def cliente_y_coleccion(monkeypatch):
    artefacto = _cargar_inst_1()
    if artefacto is None:
        pytest.skip("No se encontró el JSON real de inst_1 en storage/raw/.")

    # Resolver el artefacto directamente (sin storage-service ni BD).
    async def _resolver(_id):
        return artefacto

    monkeypatch.setattr(sources, "resolver_artefacto", _resolver)
    # Forzar fallback de disco para el .txt (sin BD).
    monkeypatch.setattr(original_txt, "_ruta_relativa_desde_bd", lambda _id: None)

    # Mock de embeddings: un vector dummy por texto.
    monkeypatch.setattr(
        embeddings, "embed_texts", lambda textos: [[0.0, 1.0, 2.0] for _ in textos]
    )

    coleccion = _ColeccionFake()
    cliente = _ClienteFake(coleccion)
    monkeypatch.setattr(chroma_client, "get_client", lambda: cliente)
    monkeypatch.setattr(
        chroma_client,
        "get_or_create_collection",
        lambda nombre, client=None: coleccion,
    )

    app = FastAPI()
    app.include_router(rag.router)
    return TestClient(app), coleccion


def test_index_inst_1_prosa_y_metadata(cliente_y_coleccion):
    cliente, coleccion = cliente_y_coleccion

    resp = cliente.post(
        "/rag/index",
        json={"investigacionId": "inv-demo", "instrumentoIds": ["1"]},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()

    # Contrato de IndexResponse intacto.
    assert set(cuerpo.keys()) == {"coleccion", "total_chunks", "instrumentos", "mensaje"}
    assert cuerpo["total_chunks"] == len(coleccion.ids)
    assert cuerpo["instrumentos"][0]["estado"] == "indexado"
    inst = cuerpo["instrumentos"][0]
    assert set(inst.keys()) == {"instrumentoId", "chunks", "estado", "motivo"}

    documentos = coleccion.documents
    assert documentos

    # Prosa con medias/porcentajes y nombres de dimensión reales (no mojibake).
    todo = "\n".join(documentos)
    assert "/5" in todo
    assert "%" in todo
    assert "respondentes" in todo
    assert "\u251c" not in todo  # ├ del mojibake crudo
    assert "\ufffd" not in todo  # replacement char
    assert "nan" not in todo
    # El título real del .txt (IEAE) debe aparecer, no el nombre del CSV.
    assert "IEAE" in todo
    assert "enc_01_respondido.csv" not in todo

    # Cada metadata trae las claves existentes MÁS clase_chunk y dimension.
    requeridas = {
        "instrumentoId",
        "titulo",
        "tipo",
        "investigador",
        "kpis",
        "investigacionId",
        "chunk_index",
        "clase_chunk",
        "dimension",
    }
    for meta in coleccion.metadatas:
        assert requeridas.issubset(meta.keys())
        assert meta["clase_chunk"] in ("estructura", "hallazgos", "grupo_desempeno")
        assert isinstance(meta["kpis"], str)  # serializado a JSON string
        assert meta["titulo"] != "enc_01_respondido.csv"

    # chunk_index secuencial y único sobre la lista aplanada.
    indices = [m["chunk_index"] for m in coleccion.metadatas]
    assert indices == list(range(len(indices)))
    assert len(set(coleccion.ids)) == len(coleccion.ids)
    # ids con el formato investigacionId:instrumentoId:n
    assert coleccion.ids[0] == "inv-demo:1:0"

    # Hay chunks de las tres clases (estructura, hallazgos, grupo_desempeno).
    clases = {m["clase_chunk"] for m in coleccion.metadatas}
    assert clases == {"estructura", "hallazgos", "grupo_desempeno"}

    # Aparecen chunks interpretativos (mejora 2) y al menos uno de grupo (mejora 3).
    assert any(
        palabra in todo for palabra in ("nivel", "fortaleza", "área de mejora")
    )
    assert any(m["clase_chunk"] == "grupo_desempeno" for m in coleccion.metadatas)
