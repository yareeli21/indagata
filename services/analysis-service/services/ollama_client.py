# services/ollama_client.py
"""
Cliente HTTP de bajo nivel para Ollama.

Responsabilidad única: enviar mensajes al endpoint /api/chat de Ollama
y devolver la respuesta en texto plano.

NO contiene lógica de negocio ni construcción de prompts.
La construcción de prompts vive en el SIS (survey_intelligence/) y en sis_adapter.py.
"""
import logging

import httpx

from api.core.config import settings

logger = logging.getLogger(__name__)


def enviar_mensaje_chat(
    system_prompt: str,
    historial: list[dict],
    timeout: float = 300.0,  # 5 minutos por defecto
    options: dict | None = None,
) -> str:
    """
    Envía un system_prompt + historial de conversación a Ollama.

    Args:
        system_prompt: Instrucciones fijas de comportamiento para el modelo.
        historial:     Lista de turnos previos, cada uno con
                       {"role": "user" | "assistant", "content": "..."}.
        timeout:       Timeout en segundos (default: 300s = 5min).

    Returns:
        Texto de la respuesta del asistente (string plano).

    Raises:
        RuntimeError: Si Ollama no responde o devuelve un error HTTP.
    """
    mensajes = [{"role": "system", "content": system_prompt}] + historial

    logger.info(
        "Enviando mensaje a Ollama: modelo=%s, mensajes=%d, timeout=%.1fs",
        settings.OLLAMA_MODEL, len(mensajes), timeout
    )

    payload: dict = {
        "model":    settings.OLLAMA_MODEL,
        "messages": mensajes,
        "stream":   False,
    }
    if options:
        # Opciones de rendimiento (num_predict, num_ctx, temperature, ...).
        payload["options"] = options

    try:
        respuesta = httpx.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=timeout,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()["message"]["content"]
        
        logger.info(
            "✅ Respuesta recibida de Ollama: %d caracteres",
            len(contenido)
        )
        
        return contenido

    except httpx.TimeoutException:
        logger.error(
            "❌ Timeout de Ollama después de %.1fs. Modelo: %s",
            timeout, settings.OLLAMA_MODEL
        )
        raise RuntimeError(
            f"Ollama tardó más de {timeout:.0f}s en responder. "
            f"Verifica que el modelo '{settings.OLLAMA_MODEL}' esté cargado y funcionando. "
            f"Considera usar un modelo más pequeño o aumentar el timeout."
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ Ollama respondió con error HTTP %d: %s",
            e.response.status_code, e.response.text[:500]
        )
        raise RuntimeError(
            f"Ollama respondió con error HTTP {e.response.status_code}: {e.response.text[:500]}"
        )
    except Exception as e:
        logger.error(
            "❌ Error al contactar Ollama en %s: %s",
            settings.OLLAMA_HOST, str(e)
        )
        raise RuntimeError(f"No se pudo contactar a Ollama en {settings.OLLAMA_HOST}: {e}")
