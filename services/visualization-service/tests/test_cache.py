"""Caché de respuestas del chat: una consulta idéntica no vuelve a llamar a Ollama."""
from __future__ import annotations

import json

import pytest

from shared.models.rag_log import RagLog
from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

import docs_ejemplo
from conftest import token
from services import enrutador

ANA = token(2)
PREGUNTA = "¿Qué porcentaje del turno vespertino está de acuerdo con p4?"


def _publicar(db, storage, id_crudo: int, doc: dict, version: int = 1) -> None:  # noqa: ANN001
    key = f"documento/{id_crudo}/{version}__v{version}_documento_final.json"
    storage.archivos[key] = (json.dumps(doc).encode("utf-8"), "documento.json")
    db.add(VersionConocimiento(id_crudo=id_crudo, version=version, estado="vigente", perfil={}, ruta_documento=key))
    db.commit()


@pytest.fixture()
def acervo(db, storage, chroma, monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_CACHE_HORAS", 24)
    enrutador._cache_docs.clear()
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    _publicar(db, storage, 1, docs_ejemplo.encuesta())
    chroma.crear("instrumentos")
    return db


def _chat(cliente, pregunta: str = PREGUNTA, **extra) -> dict:  # noqa: ANN001
    r = cliente.post("/rag/chat", json={"pregunta": pregunta, "stream": False, **extra}, headers=ANA)
    assert r.status_code == 200, r.text
    return r.json()


def test_la_misma_pregunta_se_responde_sin_llamar_a_ollama(cliente, acervo, ollama):
    primera = _chat(cliente)
    assert len(ollama["prompts"]) == 1 and not primera["enCache"]
    # Mayúsculas, acentos y signos distintos: es la misma consulta.
    segunda = _chat(cliente, "¿que porcentaje del turno vespertino esta de acuerdo con p4")
    assert len(ollama["prompts"]) == 1 and segunda["enCache"]
    assert segunda["respuesta"] == primera["respuesta"] and segunda["fuentes"] == primera["fuentes"]
    assert segunda["consultaId"] != primera["consultaId"]

    # Las métricas de la reutilizada son las de la original (no se vuelve a juzgar).
    original = acervo.get(RagLog, primera["consultaId"])
    original.metricas = {"estado": "listo", "fidelidad": 0.9, "relevancia": 0.8, "precision_contexto": 1.0}
    acervo.commit()
    m = cliente.get(f"/rag/consultas/{segunda['consultaId']}/metricas", headers=ANA).json()
    assert m["estado"] == "listo" and m["fidelidad"] == 0.9 and m["consultaId"] == segunda["consultaId"]
    assert acervo.get(RagLog, segunda["consultaId"]).motivo == f"cache:{primera['consultaId']}"


def test_sse_reutilizada_avisa_en_cache(cliente, acervo, ollama):
    _chat(cliente)
    texto = cliente.post("/rag/chat", json={"pregunta": PREGUNTA, "stream": True}, headers=ANA).text
    bloque = next(b for b in texto.split("\n\n") if b.startswith("event: fuentes"))
    assert json.loads(bloque.split("data: ", 1)[1])["enCache"] is True and len(ollama["prompts"]) == 1


def test_otro_alcance_otra_version_o_sin_cache_vuelve_a_generar(cliente, acervo, storage, ollama, monkeypatch):
    from shared.db.core.config import settings

    _chat(cliente)
    _chat(cliente, instrumentoIds=["1"])  # otro alcance (explícito)
    assert len(ollama["prompts"]) == 2

    # Una versión nueva publicada cambia la huella: nunca se sirve una respuesta vieja.
    acervo.query(VersionConocimiento).update({"estado": "reemplazado"})
    acervo.commit()
    _publicar(acervo, storage, 1, docs_ejemplo.encuesta(), version=2)
    _chat(cliente)
    assert len(ollama["prompts"]) == 3

    monkeypatch.setattr(settings, "RAG_CACHE_HORAS", 0)
    _chat(cliente)
    assert len(ollama["prompts"]) == 4


def test_no_se_reutiliza_una_respuesta_degradada(cliente, acervo, monkeypatch):
    from services import ollama_client

    llamadas = []

    async def caido(prompt, modelo, sistema=None, **kwargs):  # noqa: ANN001
        llamadas.append(prompt)
        return ollama_client.MENSAJE_DEGRADADO, True

    monkeypatch.setattr(ollama_client, "generar_no_stream", caido)
    _chat(cliente)
    _chat(cliente)
    assert sum("RESULTADO CALCULADO" in p for p in llamadas) == 2  # (las demás son del juez de métricas)
