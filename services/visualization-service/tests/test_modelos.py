"""Catálogo de modelos del chat y modelo de la consulta en curso (26 nov 2026)."""
from __future__ import annotations

import asyncio

from shared.db.core.config import settings

from services import modelos, ollama_client


def test_catalogo_trae_los_cuatro_modelos_con_el_predeterminado_primero():
    cat = modelos.catalogo()
    ids = [m["id"] for m in cat]
    assert cat[0]["predeterminado"] and cat[0]["id"] == settings.OLLAMA_MODEL
    for esperado in ("llama3.1:8b-instruct-q4_K_M", "llama3.2:3b", "qwen2.5:7b-instruct-q4_K_M", "gemma4:12b-it-qat"):
        assert esperado in ids
    assert all(m.get("etiqueta") for m in cat)


def test_el_predeterminado_queda_cargado_y_los_demas_se_descargan():
    _, fijo = modelos.parametros(settings.OLLAMA_MODEL)
    otro = next(m["id"] for m in modelos.catalogo() if not m["predeterminado"])
    opciones, temporal = modelos.parametros(otro)
    assert fijo == -1 and temporal == "10m"
    assert opciones["num_ctx"] == 4096 and opciones["temperature"] == 0.2 and opciones["num_predict"] == 1024
    cuerpo = ollama_client._payload(otro, "p", stream=False)
    assert cuerpo["keep_alive"] == "10m" and cuerpo["options"]["num_predict"] == 1024
    assert "num_predict" not in ollama_client._payload(otro, "p", stream=False, formato="json")["options"]


def test_modelo_pedido_solo_si_esta_en_el_catalogo_e_instalado(monkeypatch):
    async def instalados():
        return {"llama3.2:3b", "glm4:9b"}
    monkeypatch.setattr(ollama_client, "modelos_instalados", instalados)
    assert asyncio.run(ollama_client.modelo_para("llama3.2:3b")) == "llama3.2:3b"
    assert asyncio.run(ollama_client.modelo_para("glm4:9b")) == settings.OLLAMA_MODEL  # instalado, fuera del catálogo
    assert asyncio.run(ollama_client.modelo_para("gemma4:12b-it-qat")) == settings.OLLAMA_MODEL  # no instalado
    assert asyncio.run(ollama_client.modelo_para(None)) == settings.OLLAMA_MODEL


def test_el_modelo_elegido_lo_usan_las_demas_etapas():
    async def consulta():
        modelos.usar("llama3.2:3b")
        return modelos.en_curso()
    assert asyncio.run(consulta()) == "llama3.2:3b"
    assert modelos.en_curso() == settings.OLLAMA_MODEL  # fuera de la consulta, el del servidor


def test_gemma_no_razona_antes_de_responder_y_los_demas_no_llevan_think():
    """26 nov: sin think false, gemma4 gastaba los 1024 tokens en su razonamiento y la respuesta llegaba vacía."""
    assert ollama_client._payload("gemma4:12b-it-qat", "p", stream=False)["think"] is False
    assert "think" not in ollama_client._payload("qwen2.5:7b-instruct-q4_K_M", "p", stream=False)


def test_cargar_modelo_pide_a_ollama_cargarlo_sin_generar(monkeypatch):
    enviados = []

    class Respuesta:
        status_code = 200

    class Cliente:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):  # noqa: A002
            enviados.append(json)
            return Respuesta()

    monkeypatch.setattr(ollama_client.httpx, "AsyncClient", Cliente)
    assert asyncio.run(ollama_client.cargar("llama3.2:3b"))
    assert enviados == [{"model": "llama3.2:3b", "keep_alive": "10m"}]
