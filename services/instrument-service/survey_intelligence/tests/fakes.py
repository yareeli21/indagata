# survey_intelligence/tests/fakes.py
"""
Dobles de prueba (fakes) para los puertos del SIS.

Permiten tests deterministas sin infraestructura: IDs secuenciales, reloj fijo,
LLM con respuestas predefinidas, retriever RAG controlable.
"""
from __future__ import annotations

from datetime import datetime, timezone


class SequentialIds:
    """IdGeneratorPort determinista: prefijo + contador."""

    def __init__(self) -> None:
        self._n = 0

    def new_id(self, prefix: str = "") -> str:
        self._n += 1
        return f"{prefix}{self._n}"


class FixedClock:
    """ClockPort fijo para timestamps reproducibles."""

    def __init__(self, moment: datetime | None = None) -> None:
        self._moment = moment or datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._moment


class ScriptedLLM:
    """
    LLMPort con respuestas predefinidas.

    Se le pasa una lista de respuestas; devuelve una por llamada, en orden.
    Registra los prompts recibidos para inspección.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def complete_json(self, *, system_prompt: str, user_prompt: str,
                      temperature: float = 0.1, timeout_s: float = 300.0) -> str:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        if not self._responses:
            raise RuntimeError("ScriptedLLM sin respuestas restantes")
        return self._responses.pop(0)


class FailingLLM:
    """LLMPort que siempre falla, para probar degradación graciosa."""

    def complete_json(self, *, system_prompt: str, user_prompt: str,
                      temperature: float = 0.1, timeout_s: float = 300.0) -> str:
        raise RuntimeError("LLM no disponible (simulado)")


