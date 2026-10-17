"""Consultas sobre el documento final: viven en `shared/conocimiento/consultas.py`.

Se movieron a `shared` para que el chat (visualization-service) las reutilice tal
cual en su ruta estructurada; este módulo las re-exporta para el código y las
pruebas de knowledge-service.
"""
from shared.conocimiento.consultas import *  # noqa: F401,F403
from shared.conocimiento.consultas import _id, _norm  # noqa: F401  (usadas por las pruebas)
