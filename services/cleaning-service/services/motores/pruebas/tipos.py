"""Tipos de reactivo de una prueba estandarizada, detectados por sus valores.

Indagata NO califica las pruebas: no recibe clave de respuestas ni decide qué respuesta es
correcta. Solo reconoce qué clase de respuesta trae cada columna para validarla y describirla:
  - opcion_multiple:  letras (por defecto A, B, C, D; ver `opciones_validas`).
  - verdadero_falso:  V / F (también «Verdadero» / «Falso»).
  - puntos:           enteros 0..máx con algún 0 (p. ej. una respuesta corta ya puntuada de 0 a 2).
  - escala:           enteros 1..máx sin ningún 0 (p. ej. autoinforme de 1 a 5).
  - si_no:            Sí / No.
  - numerica:         número libre (p. ej. el resultado de un cálculo).
Los tres últimos (y puntos) solo se reconocen si el encabezado parece un reactivo (P3, item_4…),
para no confundirlos con datos del alumno como la edad o el semestre.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from services.configuracion import normalizar_texto

OPCION_MULTIPLE = "opcion_multiple"
VERDADERO_FALSO = "verdadero_falso"
PUNTOS = "puntos"
ESCALA = "escala"
SI_NO = "si_no"
NUMERICA = "numerica"
# Tipos cuyas respuestas son números (se describen también con su media).
NUMERICOS = frozenset({PUNTOS, ESCALA, NUMERICA})
_NO = {"NO", "N"}

_VF = {"V": "V", "F": "F", "VERDADERO": "V", "FALSO": "F", "CIERTO": "V"}
# Encabezados que delatan un reactivo (para no confundir edad o semestre con puntos).
_REACTIVO = re.compile(r"(^|[_\s.\-])(q|p|item|ítem|reactivo|pregunta|preg)[_\s.\-]?\d+$|^\d+$", re.IGNORECASE)
_PUNTAJE_GLOBAL = re.compile(r"(score|puntaje|puntuaci[oó]n|calificaci[oó]n|nota|total)", re.IGNORECASE)
_MAX_PUNTOS = 10
_MIN_COBERTURA = 0.9
_MIN_COBERTURA_REACTIVO = 0.6


# Letras de otro alfabeto que se ven iguales a las latinas (cirílico, griego); las de ancho completo («Ｃ») se
# resuelven con NFKC.
_HOMOGLIFOS = str.maketrans({
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X",
    "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Χ": "X", "Ϲ": "C",
})
# Una letra con signos alrededor: «B)», «(C)», «c.», «D-», «[A]».
_LETRA_CON_SIGNOS = re.compile(r"^[(\[]?\s*([A-Za-z])\s*[)\].:\-]?$")
_MISMA_LETRA = re.compile(r"^([A-Za-z])\1+$")
VALIDAS_VF = frozenset({"V", "F"})


def normalizar_respuesta(valor: str, validas: set[str], tokens_nr: set[str]) -> tuple[str, str | None]:
    """(respuesta escrita como la esperan las reglas, regla aplicada o None). Solo cambia la forma, nunca el sentido.

      - «N/R», «Sin respuesta», «-» → "" (no respondida); `tokens_nr` viene de `limpieza.yaml`.
      - «А» cirílica o «Ｃ» de ancho completo → «A», «C».
      - «B)», «(C)», «c.» → la letra, solo si es una opción válida.
      - «AA» → «A» (la misma opción marcada dos veces; «AB» sigue siendo respuesta múltiple).
    """
    v = valor.strip()
    if not v or v.upper() == "NR":
        return valor, None
    if normalizar_texto(v) in tokens_nr:
        return "", "no_respondida_escrita"
    letras = {x.upper() for x in validas} | VALIDAS_VF
    sin_homoglifos = unicodedata.normalize("NFKC", v).translate(_HOMOGLIFOS)
    regla = "letra_parecida" if sin_homoglifos != v and len(sin_homoglifos) <= 3 else None
    w = sin_homoglifos if regla else v
    if (m := _LETRA_CON_SIGNOS.match(w)) and m.group(1) != w and m.group(1).upper() in letras:
        return m.group(1), regla or "letra_con_signos"
    if (m := _MISMA_LETRA.match(w)) and m.group(1).upper() in letras:
        return m.group(1), regla or "misma_letra_repetida"
    return (w, regla) if regla and w.upper() in letras else (valor, None)


def normalizar_vf(valor: str) -> str | None:
    return _VF.get(normalizar_texto(valor).upper())


def normalizar_si_no(valor: str) -> str | None:
    v = normalizar_texto(valor).upper()
    return "Sí" if v in {"SI", "S"} else ("No" if v in _NO else None)


@dataclass
class Detectado:
    """Un reactivo detectado en la hoja de respuestas."""

    nombre: str
    columna: int
    tipo: str
    puntos_max: int | None = None


def _tipo_columna(encabezado: str, valores: list[str], opciones: set[str], ilegibles: set[str]) -> tuple[str, int | None] | None:
    presentes = [v.strip().upper() for v in valores if v.strip() and v.strip().upper() != "NR"]
    if len(presentes) < 3:
        return None
    # En una columna con nombre de reactivo (P3, item_2…) se toleran respuestas sucias: las
    # ilegibles y las de varias letras («AB», «A,C») no cuentan, y basta el 60 % de letras válidas.
    nombre_reactivo = bool(_REACTIVO.search(encabezado.strip()))
    combinadas = [v for v in presentes if _varias_letras(v, opciones)]
    limpias = [v for v in presentes if v not in combinadas and not any(c in v for c in ilegibles)] if nombre_reactivo else presentes
    cobertura = _MIN_COBERTURA_REACTIVO if nombre_reactivo else _MIN_COBERTURA
    distintas = {v for v in limpias if v in opciones} | {ch for v in combinadas for ch in v if ch in opciones}
    letras = sum(1 for v in limpias if v in opciones)
    if limpias and letras >= cobertura * len(limpias) and len(distintas) >= (1 if nombre_reactivo else 2):
        return OPCION_MULTIPLE, None
    vf = sum(1 for v in limpias if v in _VF)  # solo V/F/Verdadero/Falso: no True/False (contexto)
    if limpias and vf >= cobertura * len(limpias) and (nombre_reactivo or len({_VF[v] for v in limpias if v in _VF}) == 2):
        return VERDADERO_FALSO, None
    if not _REACTIVO.search(encabezado.strip()):
        return None  # los tipos que siguen se confunden con datos del alumno (edad, semestre…)
    enteros = [int(v) for v in presentes if v.isdigit()]
    if len(enteros) >= _MIN_COBERTURA * len(presentes) and enteros and max(enteros) <= _MAX_PUNTOS:
        # Con algún 0, es una respuesta puntuada (0..máx); sin 0, una escala de autoinforme (1..máx).
        return (PUNTOS if min(enteros) == 0 else ESCALA), max(enteros)
    if sum(1 for v in presentes if normalizar_si_no(v)) >= _MIN_COBERTURA * len(presentes):
        return SI_NO, None
    if sum(1 for v in presentes if es_numero(v)) >= _MIN_COBERTURA * len(presentes):
        return NUMERICA, None
    return None


def _varias_letras(valor: str, opciones: set[str]) -> bool:
    """«AB», «A,C»: varias opciones marcadas en una sola respuesta (misma regla que `motor.clasificar`)."""
    partes = [p for p in re.split(r"[\s,;/|+-]+", valor) if p]
    if len(partes) == 1 and len(partes[0]) > 1 and all(ch in opciones for ch in partes[0]):
        return True
    return len(partes) > 1 and all(p in opciones for p in partes)


def parece_reactivo(encabezado: str) -> bool:
    """¿El encabezado tiene nombre de reactivo (P3, item_4, pru_03_Competenci_q10…)?"""
    return bool(_REACTIVO.search(encabezado.strip()))


def detectar(
    encabezados: list[str], filas: list[list[str]], excluidas: set[int], opciones: set[str], ilegibles: set[str] = frozenset(),
    tokens_nr: set[str] = frozenset(),
) -> tuple[list[Detectado], int | None]:
    """Reactivos de la hoja de respuestas, y la columna de puntaje global (si hay; se trata como contexto)."""
    detectados: list[Detectado] = []
    puntaje_col: int | None = None
    for j, h in enumerate(encabezados):
        if j in excluidas or not h:
            continue
        valores = [normalizar_respuesta(f[j], opciones, tokens_nr)[0] if j < len(f) else "" for f in filas]
        tipo = _tipo_columna(h, valores, opciones, ilegibles)
        if tipo:
            detectados.append(Detectado(h, j, tipo[0], tipo[1]))
        elif puntaje_col is None and _PUNTAJE_GLOBAL.search(normalizar_texto(h)):
            numeros = [v for v in valores if es_numero(v)]
            if len(numeros) >= _MIN_COBERTURA * max(1, sum(1 for v in valores if v.strip())):
                puntaje_col = j
    return detectados, puntaje_col


def es_numero(v: str) -> bool:
    try:
        float(v.replace(",", "."))
        return True
    except ValueError:
        return False
