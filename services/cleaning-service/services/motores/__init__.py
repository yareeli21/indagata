"""Registro de motores de limpieza por tipo de instrumento y familia de archivo.

Las fases 2–4 registran aquí sus motores (encuestas, entrevistas, pruebas). Un
tipo sin motor responde 501 con un mensaje claro y no crea ninguna ejecución.
"""
from __future__ import annotations

from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, Motor, ResultadoAutomatico, ResultadoFinal

TABULARES = frozenset({".csv", ".xlsx", ".xls"})
DOCUMENTOS = frozenset({".txt", ".pdf", ".docx"})

# (tipo_instrumento, familia) → motor. familia: "tabular" | "documento".
_REGISTRO: dict[tuple[str, str], Motor] = {}

_NOMBRES = {
    "encuesta": "encuestas",
    "entrevista": "entrevistas",
    "prueba_estandarizada": "pruebas estandarizadas",
}


class MotorNoDisponible(Exception):
    """No hay motor de limpieza para este tipo/formato (aún)."""


def familia(extension: str) -> str:
    """Familia de archivo según la extensión ("tabular" o "documento")."""
    ext = extension.lower()
    if ext in TABULARES:
        return "tabular"
    if ext in DOCUMENTOS:
        return "documento"
    raise MotorNoDisponible(f"El formato {extension or '(sin extensión)'} no se puede limpiar.")


def registrar(tipo_instrumento: str, familia_archivo: str, motor: Motor) -> None:
    """Registra (o reemplaza) el motor de un tipo y familia."""
    _REGISTRO[(tipo_instrumento, familia_archivo)] = motor


def obtener(tipo_instrumento: str, extension: str) -> Motor:
    """Motor para el tipo y la extensión del archivo crudo; MotorNoDisponible si no hay."""
    clave = (tipo_instrumento, familia(extension))
    motor = _REGISTRO.get(clave)
    if motor is None:
        nombre = _NOMBRES.get(tipo_instrumento, tipo_instrumento)
        raise MotorNoDisponible(f"La limpieza de {nombre} en formato {extension} aún no está disponible.")
    return motor


__all__ = [
    "DOCUMENTOS",
    "TABULARES",
    "Entrada",
    "ErrorLimpieza",
    "Hallazgo",
    "Motor",
    "MotorNoDisponible",
    "ResultadoAutomatico",
    "ResultadoFinal",
    "familia",
    "obtener",
    "registrar",
]


def _registrar_motores() -> None:
    """Registra los motores disponibles (se importan aquí para evitar ciclos)."""
    from services.motores.encuestas import MotorEncuestas
    from services.motores.entrevistas import MotorEntrevistas
    from services.motores.pruebas import MotorPruebasDocumento, MotorPruebasTabular

    registrar("encuesta", "tabular", MotorEncuestas())
    registrar("entrevista", "documento", MotorEntrevistas())
    registrar("prueba_estandarizada", "tabular", MotorPruebasTabular())
    registrar("prueba_estandarizada", "documento", MotorPruebasDocumento())


_registrar_motores()
