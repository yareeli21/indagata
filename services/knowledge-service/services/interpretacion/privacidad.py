"""Detección de columnas con datos personales (nombre, correo, matrícula…).

Regla: coincidencia por PALABRA COMPLETA del encabezado normalizado (sin acentos,
minúsculas, con `_ . - / ( ) ¿ ?` convertidos en espacios). Así «ID» o «Nombre
completo» se detectan, pero «Idioma», «Identidad de género» o «Ideas» no.
"""
from __future__ import annotations

from services.interpretacion.config import normalizar, palabras, reglas


def es_dato_personal(encabezado: str) -> bool:
    texto = palabras(encabezado)
    return any(f" {normalizar(p)} " in texto for p in reglas().get("datos_personales", []))
