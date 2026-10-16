"""Tipos de reactivo y clave de respuestas propuesta (pruebas sin clave).

Tipos de reactivo CALIFICABLES (tienen respuesta correcta; cuentan en aciertos y KR-20):
  - opcion_multiple:  letras (por defecto A, B, C, D; ver `opciones_validas`).
  - verdadero_falso:  V / F (también «Verdadero» / «Falso»).
  - puntos:           respuesta ya calificada con un entero 0..máx (p. ej. respuesta corta
                      de 0 a 2 puntos). Acierto = obtener el puntaje máximo; el parcial
                      queda en la respuesta. Regla: hay algún 0 entre las respuestas.

Tipos NO calificables (autoinforme o respuesta abierta: se conservan e interpretan, pero
no tienen respuesta correcta ni cuentan en aciertos, puntaje ni KR-20):
  - escala:     enteros 1..máx sin ningún 0 (p. ej. 1 a 5).
  - si_no:      Sí / No.
  - numerica:   número libre (p. ej. el resultado de un cálculo). Sin clave no se puede calificar.

Clave propuesta (cuando la prueba no trae clave): para cada reactivo de opción múltiple
o V/F se propone la respuesta MÁS ELEGIDA POR LOS ALUMNOS DE MEJOR DESEMPEÑO:
  - si hay una columna de puntaje global (score, puntaje, calificación, nota), el grupo de
    referencia es el 27 % con mayor puntaje;
  - si no, se parte de la respuesta más frecuente de cada reactivo, se toma el 27 % de
    alumnos que más coincide con ella y se recalcula (dos vueltas).
La propuesta NUNCA se aplica sola: el investigador la confirma o corrige en la fase asistida.
Riesgo conocido: en un reactivo tan difícil que la mayoría de los mejores falla, la
propuesta sale equivocada; por eso se muestra la proporción con que se eligió.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from services.configuracion import normalizar_texto

OPCION_MULTIPLE = "opcion_multiple"
VERDADERO_FALSO = "verdadero_falso"
PUNTOS = "puntos"
ESCALA = "escala"
SI_NO = "si_no"
NUMERICA = "numerica"
CALIFICABLES = frozenset({OPCION_MULTIPLE, VERDADERO_FALSO, PUNTOS})
_SI = {"SI", "SÍ", "S"}
_NO = {"NO", "N"}

_VF = {"V": "V", "F": "F", "VERDADERO": "V", "FALSO": "F", "CIERTO": "V"}
# Encabezados que delatan un reactivo (para no confundir edad o semestre con puntos).
_REACTIVO = re.compile(r"(^|[_\s.\-])(q|p|item|ítem|reactivo|pregunta|preg)[_\s.\-]?\d+$|^\d+$", re.IGNORECASE)
_PUNTAJE_GLOBAL = re.compile(r"(score|puntaje|puntuaci[oó]n|calificaci[oó]n|nota|total)", re.IGNORECASE)
_MAX_PUNTOS = 10
_MIN_COBERTURA = 0.9
_GRUPO = 0.27


def normalizar_vf(valor: str) -> str | None:
    return _VF.get(normalizar_texto(valor).upper())


def normalizar_si_no(valor: str) -> str | None:
    v = normalizar_texto(valor).upper()
    return "Sí" if v in {"SI", "S"} else ("No" if v in _NO else None)


def tipo_de_respuesta_correcta(respuesta: str, opciones: set[str]) -> tuple[str, int | None] | None:
    """Tipo de reactivo según la respuesta correcta de una clave (None si no es válida)."""
    r = respuesta.strip().upper()
    if r in opciones:
        return OPCION_MULTIPLE, None
    if normalizar_vf(r):
        return VERDADERO_FALSO, None
    if r.isdigit() and 0 < int(r) <= _MAX_PUNTOS:
        return PUNTOS, int(r)
    return None


@dataclass
class Detectado:
    """Un reactivo detectado sin clave."""

    nombre: str
    columna: int
    tipo: str
    puntos_max: int | None = None
    propuesta: str = ""  # respuesta correcta propuesta (o el puntaje máximo, en puntos)
    confianza: float = 0.0  # proporción del grupo de referencia que eligió la propuesta
    alternativas: list[tuple[str, float]] = field(default_factory=list)  # (opción, proporción) en el grupo


def _tipo_columna(encabezado: str, valores: list[str], opciones: set[str]) -> tuple[str, int | None] | None:
    presentes = [v.strip().upper() for v in valores if v.strip() and v.strip().upper() != "NR"]
    if len(presentes) < 3:
        return None
    letras = sum(1 for v in presentes if v in opciones)
    if letras >= _MIN_COBERTURA * len(presentes) and len(set(presentes) & opciones) >= 2:
        return OPCION_MULTIPLE, None
    vf = sum(1 for v in presentes if v in _VF)  # solo V/F/Verdadero/Falso: no True/False (contexto)
    if vf >= _MIN_COBERTURA * len(presentes) and len({_VF[v] for v in presentes if v in _VF}) == 2:
        return VERDADERO_FALSO, None
    if not _REACTIVO.search(encabezado.strip()):
        return None  # los tipos que siguen se confunden con datos del alumno (edad, semestre…)
    enteros = [int(v) for v in presentes if v.isdigit()]
    if len(enteros) >= _MIN_COBERTURA * len(presentes) and enteros and max(enteros) <= _MAX_PUNTOS:
        # Con algún 0, es una respuesta calificada (0..máx); sin 0, una escala de autoinforme (1..máx).
        return (PUNTOS if min(enteros) == 0 else ESCALA), max(enteros)
    if sum(1 for v in presentes if normalizar_si_no(v)) >= _MIN_COBERTURA * len(presentes):
        return SI_NO, None
    if sum(1 for v in presentes if _es_numero(v)) >= _MIN_COBERTURA * len(presentes):
        return NUMERICA, None
    return None


def detectar(encabezados: list[str], filas: list[list[str]], excluidas: set[int], opciones: set[str]) -> tuple[list[Detectado], int | None]:
    """Reactivos de una hoja de respuestas sin clave, y la columna de puntaje global (si hay)."""
    detectados: list[Detectado] = []
    puntaje_col: int | None = None
    for j, h in enumerate(encabezados):
        if j in excluidas or not h:
            continue
        valores = [f[j] if j < len(f) else "" for f in filas]
        tipo = _tipo_columna(h, valores, opciones)
        if tipo:
            detectados.append(Detectado(h, j, tipo[0], tipo[1]))
        elif puntaje_col is None and _PUNTAJE_GLOBAL.search(normalizar_texto(h)):
            numeros = [v for v in valores if _es_numero(v)]
            if len(numeros) >= _MIN_COBERTURA * max(1, sum(1 for v in valores if v.strip())):
                puntaje_col = j
    return detectados, puntaje_col


def _es_numero(v: str) -> bool:
    try:
        float(v.replace(",", "."))
        return True
    except ValueError:
        return False


def _normal(valor: str, tipo: str) -> str:
    v = valor.strip().upper()
    return (normalizar_vf(v) or "") if tipo == VERDADERO_FALSO else v


def proponer(detectados: list[Detectado], filas: list[list[str]], puntaje_col: int | None, opciones: set[str]) -> str:
    """Llena `propuesta`, `confianza` y `alternativas` (en sitio). Devuelve cómo se eligió el grupo."""
    elegibles = [d for d in detectados if d.tipo in (OPCION_MULTIPLE, VERDADERO_FALSO)]
    for d in detectados:
        if d.tipo == PUNTOS:
            d.propuesta, d.confianza = str(d.puntos_max), 1.0
        elif d.tipo not in CALIFICABLES:
            d.propuesta, d.confianza = "", 0.0  # sin respuesta correcta
    if not elegibles or not filas:
        return "sin_reactivos_de_opcion"

    def validos(d: Detectado) -> set[str]:
        return opciones if d.tipo == OPCION_MULTIPLE else {"V", "F"}

    def moda(d: Detectado, indices: list[int]) -> tuple[str, float, list[tuple[str, float]]]:
        conteo = Counter(v for i in indices if (v := _normal(filas[i][d.columna] if d.columna < len(filas[i]) else "", d.tipo)) in validos(d))
        total = sum(conteo.values())
        if not total:
            return "", 0.0, []
        orden = conteo.most_common()
        return orden[0][0], round(orden[0][1] / total, 4), [(o, round(c / total, 4)) for o, c in orden]

    todos = list(range(len(filas)))
    tam = max(1, round(_GRUPO * len(filas)))
    if puntaje_col is not None:
        def puntaje(i: int) -> float:
            try:
                return float(filas[i][puntaje_col].replace(",", "."))
            except (ValueError, IndexError):
                return float("-inf")

        grupo = sorted(todos, key=puntaje, reverse=True)[:tam]
        criterio = "puntaje_global"
    else:
        clave = {d.nombre: moda(d, todos)[0] for d in elegibles}
        grupo = todos
        for _ in range(2):
            def coincidencias(i: int) -> int:
                return sum(1 for d in elegibles if _normal(filas[i][d.columna] if d.columna < len(filas[i]) else "", d.tipo) == clave[d.nombre])

            grupo = sorted(todos, key=coincidencias, reverse=True)[:tam]
            clave = {d.nombre: moda(d, grupo)[0] for d in elegibles}
        criterio = "acuerdo_entre_alumnos"
    for d in elegibles:
        d.propuesta, d.confianza, d.alternativas = moda(d, grupo)
    return criterio
