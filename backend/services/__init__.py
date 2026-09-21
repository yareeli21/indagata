# services/__init__.py
"""
Módulo de infraestructura de servicios externos (LLM / SIS).

Estructura:
    sis_adapter.py   — único punto de acople con el SIS (implementa LLMPort sobre Ollama)
    ollama_client.py — cliente HTTP de bajo nivel hacia Ollama
    llm_service.py   — contratos FUTUROS del RAG principal (funciones pendientes)

Uso vigente del análisis de instrumentos (vía SIS):
    from services import sis_adapter
    service = sis_adapter.build_service(db)
    result = service.process(sis_adapter.build_request(...))
"""
from services import llm_service

__all__ = ["llm_service"]
