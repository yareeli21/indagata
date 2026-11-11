"""Freno a las redacciones que se repiten (8 nov: «¿Qué es la escala RAU?» se quedó repitiendo un párrafo)."""
from __future__ import annotations

import asyncio
import json

import httpx

from services import ollama_client

PARRAFO = (
    "La Escala RAU de Rendimiento Académico Universitario mide cómo perciben los estudiantes su desempeño, "
    "su aportación en clase y sus actividades de estudio [Fuente 1]. "
)


def test_texto_normal_no_se_corta():
    texto = "Primera idea sobre el instrumento. " + "Segunda idea distinta con otros datos. " * 2 + PARRAFO
    assert ollama_client.corte_repeticion(texto) is None
    assert ollama_client.sin_repeticion(texto) == texto


def test_parrafo_repetido_se_corta_donde_empieza_la_copia():
    texto = "Respuesta:\n" + PARRAFO * 5
    assert ollama_client.sin_repeticion(texto) == ("Respuesta:\n" + PARRAFO).rstrip()


def test_frase_repetida_entre_frases_distintas_se_corta():
    # El bucle real del 8 nov: alternaba frases casi iguales; la segunda vez que aparece una frase completa, se corta.
    a = "La Escala RAU es un instrumento de evaluación utilizado para medir la participación [Fuente 1]."
    b = "La Escala RAU es una encuesta que se utiliza para evaluar el compromiso académico [Fuente 1]."
    c = "La Escala RAU tiene como objetivo evaluar la participación de los estudiantes en clase."
    texto = f"{a}\n{b}\n{c}\n{a}\n{b}\n{a}"
    assert ollama_client.sin_repeticion(texto) == f"{a}\n{b}\n{c}"
    # Frases cortas repetidas («Sí.», viñetas breves) no cuentan.
    corto = "Opciones:\n- Sí.\n- No.\n- Sí."
    assert ollama_client.sin_repeticion(corto) == corto


def test_tope_de_tokens_solo_en_la_redaccion():
    redaccion = ollama_client._payload("m", "p", stream=True)
    plan = ollama_client._payload("m", "p", stream=False, formato="json")
    assert redaccion["options"]["num_predict"] == ollama_client._MAX_TOKENS_REDACCION
    assert "num_predict" not in plan["options"]


def test_stream_que_se_repite_se_detiene_sin_mostrar_la_copia(monkeypatch):
    pedidas: list[int] = []

    def ollama_en_bucle(request: httpx.Request) -> httpx.Response:
        # Ollama manda un JSON por línea; aquí el modelo nunca termina de repetir el párrafo.
        lineas = [json.dumps({"response": "Respuesta:\n", "done": False})]
        lineas += [json.dumps({"response": PARRAFO, "done": False}) for _ in range(200)]
        pedidas.append(len(lineas))
        return httpx.Response(200, content="\n".join(lineas).encode())

    original = httpx.AsyncClient
    monkeypatch.setattr(
        ollama_client.httpx, "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(ollama_en_bucle), **kw),
    )

    async def juntar() -> str:
        return "".join([t async for t in ollama_client.generar_stream("p", "m")])

    texto = asyncio.run(juntar())
    assert texto == ("Respuesta:\n" + PARRAFO).rstrip()
    assert texto.count("Escala RAU") == 1
