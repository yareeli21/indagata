# app/core/ollama_client.py
"""
Cliente de Ollama: envía conversaciones al modelo local vía /api/chat.
"""
import httpx

from app.core.config import settings


def enviar_mensaje_chat(system_prompt: str, historial: list[dict]) -> str:
    """
    Envía el system prompt + historial de conversación a Ollama.
    `historial` es una lista de {"role": "user"|"assistant", "content": "..."}.
    Regresa el texto de la respuesta del asistente.
    """
    mensajes = [{"role": "system", "content": system_prompt}] + historial

    try:
        respuesta = httpx.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": mensajes,
                "stream": False,
            },
            timeout=120.0,
        )
        respuesta.raise_for_status()
        return respuesta.json()["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"No se pudo contactar a Ollama: {e}")