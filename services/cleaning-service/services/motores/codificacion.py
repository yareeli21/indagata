"""Acentos rotos (mojibake): texto UTF-8 que algún programa leyó como Latin-1 o CP1252 y volvió a guardar.

«SÃ­» → «Sí», «educaciÃ³n» → «educación», «â€”» → «—». Pasa al pegar una celda o un turno desde otro
programa, aunque el resto del archivo esté bien; por eso se repara cada secuencia por separado y no el
archivo completo.

Solo se toca una secuencia si forma un carácter UTF-8 válido de dos a cuatro bytes («Ã» seguido de «­»,
«©», «³»…). El texto en español bien escrito no forma esas secuencias, así que no se cambia nada más.
"""
from __future__ import annotations

import re

# Byte de continuación de UTF-8 (0x80–0xBF) visto como Latin-1 o como CP1252 (0x80–0x9F son «€», «“», «—»…).
_CONT = "\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™"
_SECUENCIA = re.compile(rf"[Â-ß][{_CONT}]|[à-ï][{_CONT}]{{2}}|[ð-ô][{_CONT}]{{3}}")


def _a_bytes(texto: str) -> bytes:
    salida = bytearray()
    for c in texto:
        salida += bytes([ord(c)]) if ord(c) < 256 else c.encode("cp1252")
    return bytes(salida)


def _reparar_secuencia(m: re.Match[str]) -> str:
    try:
        return _a_bytes(m.group(0)).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return m.group(0)


def reparar(texto: str) -> tuple[str, int]:
    """(texto con los acentos reparados, cuántas secuencias se repararon)."""
    if not texto or not _SECUENCIA.search(texto):
        return texto, 0
    n = 0

    def contar(m: re.Match[str]) -> str:
        nonlocal n
        nuevo = _reparar_secuencia(m)
        n += nuevo != m.group(0)
        return nuevo

    return _SECUENCIA.sub(contar, texto), n


def reparar_filas(filas: list[list[str]]) -> tuple[list[list[str]], list[tuple[int, int, str, str]]]:
    """Repara cada celda; devuelve las filas y los casos (fila, columna, antes, después)."""
    casos: list[tuple[int, int, str, str]] = []
    salida = []
    for i, fila in enumerate(filas):
        nueva = []
        for j, celda in enumerate(fila):
            reparada, n = reparar(celda)
            if n:
                casos.append((i, j, celda, reparada))
            nueva.append(reparada)
        salida.append(nueva)
    return salida, casos
