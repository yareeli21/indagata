# survey_intelligence/ports/llm_port.py
"""
LLMPort: contrato de dependencia para el modelo de lenguaje.

El SIS nunca conoce a Ollama directamente. El host provee un adaptador que
implementa este protocolo (p. ej. envolviendo services/ollama_client.py).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMPort(Protocol):
    """Puerto para completar prompts y obtener texto (que se espera sea JSON)."""

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        timeout_s: float = 300.0,
    ) -> str:
        """
        Envía un system_prompt + user_prompt al LLM y devuelve la respuesta cruda.

        El parseo/validación del JSON lo hace el SIS (engine/parsing/robust_json.py),
        no el adaptador. El adaptador solo transporta texto.

        Raises:
            RuntimeError: si el LLM no responde. El SIS lo captura y degrada la etapa.
        """
        ...
