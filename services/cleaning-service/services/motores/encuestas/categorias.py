"""Respuestas de opción que llegan escritas de otra forma (encuestas).

  - Sí / No en otro idioma o abreviado («Yes», «S», «N», «True») en una columna de Sí / No: se escriben como
    las demás, sin decisión. Si la columna mezcla «1» y «0», el investigador decide qué significa cada uno.
  - Opciones poco frecuentes casi iguales a otra opción («Una vez al mse» ≈ «Una vez al mes», «Nuca» ≈
    «Nunca»): se propone cambiarlas por la opción frecuente; el investigador decide.

No se buscan sinónimos («Jamás» por «Nunca»): eso exige entender el significado.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from services.configuracion import normalizar_texto
from services.motores.encuestas import universales
from services.motores.encuestas.likert import numero

_SI = {"si", "s", "yes", "y", "true", "verdadero"}
_NO = {"no", "n", "false", "falso"}
_CODIGOS = {"1", "0"}
_MIN_PRESENTES = 5
# Opciones parecidas.
_SIMILITUD_MINIMA = 0.85
_LARGO_MINIMO = 4
_MAX_OPCIONES = 30
_MAX_PCT_RARA = 0.03  # una opción «rara» aparece como mucho en el 3 % de las respuestas (o 2 veces)
_VECES_MAS_FRECUENTE = 5  # y la opción a la que se parece, al menos 5 veces más


@dataclass
class SiNoCodigos:
    """Columna de Sí / No con «1» y «0» mezclados."""

    columna: str  # id
    etiqueta: str
    filas: list[int]  # índices con «1» o «0»
    forma_si: str
    forma_no: str
    unos: int = 0
    ceros: int = 0
    originales: list[str] = field(default_factory=list)  # «1» o «0» tal cual, en el orden de `filas`


@dataclass
class Parecida:
    """Una opción poco frecuente casi igual a una opción frecuente de la misma columna."""

    columna: str  # id
    etiqueta: str
    clave: str  # valor raro normalizado (para el id del hallazgo)
    valor: str  # tal como aparece
    destino: str  # opción frecuente, con su forma más común
    veces_destino: int
    similitud: float
    filas: list[int] = field(default_factory=list)


def _forma(valores: list[str], clave: str, defecto: str) -> str:
    formas = Counter(v for v in valores if normalizar_texto(v) == clave)
    return formas.most_common(1)[0][0] if formas else defecto


def si_no(tabla: universales.TablaPreparada) -> tuple[dict | None, list[SiNoCodigos]]:
    """Escribe en sitio «Yes», «S», «True»… como el «Sí» de la columna; devuelve la transformación y las columnas
    con «1» / «0» (pendientes de decisión)."""
    total = 0
    casos: list[dict] = []
    codigos: list[SiNoCodigos] = []
    for c in tabla.columnas:
        presentes = [v for v in c.valores if v is not None]
        if len(presentes) < _MIN_PRESENTES:
            continue
        norm = [normalizar_texto(v) for v in presentes]
        base = sum(1 for n in norm if n in ("si", "no"))
        otros = {n for n in norm if n not in ("si", "no")}
        if base < 0.6 * len(norm) or not otros or not otros <= _SI | _NO | _CODIGOS or not {"si", "no"} <= set(norm):
            continue
        forma_si, forma_no = _forma(presentes, "si", "Sí"), _forma(presentes, "no", "No")
        filas_codigo = []
        for i, v in enumerate(c.valores):
            if v is None:
                continue
            n = normalizar_texto(v)
            if n in _CODIGOS:
                filas_codigo.append(i)
                continue
            nuevo = forma_si if n in _SI else forma_no if n in _NO else v
            if nuevo != v:
                total += 1
                if len(casos) < universales.MAX_CASOS:
                    casos.append({"fila": i + 1, "columna": c.etiqueta, "antes": v, "despues": nuevo})
                c.valores[i] = nuevo
        if filas_codigo:
            unos = sum(1 for i in filas_codigo if c.valores[i].strip() == "1")
            codigos.append(SiNoCodigos(c.id, c.etiqueta, filas_codigo, forma_si, forma_no, unos, len(filas_codigo) - unos,
                                       [c.valores[i] for i in filas_codigo]))
    transformacion = (
        {"regla": "si_no_unificado", "detalle": "Sí / No escritos en otro idioma o abreviados («Yes», «S», «True») se escriben "
         "como el resto de la columna.", "afectados": total, "casos": casos}
        if total else None
    )
    return transformacion, codigos


def aplicar_si_no(tabla: universales.TablaPreparada, pendiente: SiNoCodigos, decision: str) -> int:
    """Aplica la decisión sobre «1» / «0»: uno_es_si | uno_es_no | anular | conservar. Devuelve cuántos cambió."""
    if decision == "conservar":
        return 0
    columna = next(c for c in tabla.columnas if c.id == pendiente.columna)
    uno, cero = (pendiente.forma_si, pendiente.forma_no) if decision == "uno_es_si" else (pendiente.forma_no, pendiente.forma_si)
    for i in pendiente.filas:
        columna.valores[i] = None if decision == "anular" else (uno if columna.valores[i].strip() == "1" else cero)
    return len(pendiente.filas)


def _digitos(texto: str) -> str:
    return "".join(ch for ch in texto if ch.isdigit())


def parecidas(tabla: universales.TablaPreparada) -> list[Parecida]:
    """Opciones poco frecuentes que se parecen mucho (≥ 85 %) a una opción mucho más frecuente de su columna."""
    salida: list[Parecida] = []
    for c in tabla.columnas:
        presentes = [v for v in c.valores if v is not None]
        if len(presentes) < 10 or sum(1 for v in presentes if numero(v) is not None) >= 0.5 * len(presentes):
            continue
        if sum(1 for v in presentes if ";" in v) >= 2:
            continue  # selección múltiple: las combinaciones no son opciones
        conteo = Counter(normalizar_texto(v) for v in presentes)
        if len(conteo) > _MAX_OPCIONES:
            continue
        if sum(1 for n in conteo.values() if n >= 3) < 2:
            continue
        max_rara = max(2, _MAX_PCT_RARA * len(presentes))
        for raro, veces in conteo.items():
            frecuentes = [k for k, n in conteo.items() if k != raro and n >= max(3, _VECES_MAS_FRECUENTE * veces)]
            if veces > max_rara or not frecuentes or len(raro) < _LARGO_MINIMO:
                continue
            similitud, destino = max((SequenceMatcher(None, raro, f).ratio(), f) for f in frecuentes)
            # «Grupo 1» y «Grupo 2» se parecen, pero son opciones distintas.
            if similitud < _SIMILITUD_MINIMA or _digitos(raro) != _digitos(destino):
                continue
            filas = [i for i, v in enumerate(c.valores) if v is not None and normalizar_texto(v) == raro]
            salida.append(Parecida(c.id, c.etiqueta, raro, c.valores[filas[0]], _forma(presentes, destino, destino),
                                   conteo[destino], round(similitud, 2), filas))
    return salida
