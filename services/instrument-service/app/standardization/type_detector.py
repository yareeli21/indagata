"""Detección de tipo de pregunta por columna (diseño §1.3, Bug 3).

Para instrumentos TABULARES (encuesta) cada columna de datos se clasifica sobre
sus valores no vacíos. El vocabulario estandarizado de tipos es cerrado:

    binaria | opcion_multiple | likert | numerica_continua | abierta

Orden de evaluación (primera regla que acierta gana): binaria -> likert ->
numerica_continua -> opcion_multiple -> abierta. La detección NO reordena ni
elimina columnas: produce una propuesta por columna preservando el orden de
`RawTable.headers`.

Para DOCUMENTOS no hay columnas: la estandarización arma una sola pregunta
`abierta` directamente (ver `domain_builder`), no pasa por este detector.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from app.parsing.raw_table import RawTable

# ── Vocabulario de tipos estandarizados (frontera única con el endpoint) ──────
TIPO_BINARIA = "binaria"
TIPO_OPCION_MULTIPLE = "opcion_multiple"
TIPO_LIKERT = "likert"
TIPO_NUMERICA_CONTINUA = "numerica_continua"
TIPO_ABIERTA = "abierta"

TIPOS_VALIDOS: frozenset[str] = frozenset(
    {
        TIPO_BINARIA,
        TIPO_OPCION_MULTIPLE,
        TIPO_LIKERT,
        TIPO_NUMERICA_CONTINUA,
        TIPO_ABIERTA,
    }
)

# Confianza informativa para la UI.
CONFIANZA_ALTA = "alta"
CONFIANZA_MEDIA = "media"
CONFIANZA_BAJA = "baja"

# Conjunto cerrado de etiquetas binarias (normalizadas a minúsculas sin acentos).
_VALORES_BINARIOS: frozenset[str] = frozenset(
    {"si", "no", "0", "1", "true", "false", "verdadero", "falso"}
)

# Diccionario corto de columnas demográficas conocidas (normalizadas).
_DEMOGRAFICOS: frozenset[str] = frozenset(
    {
        "edad",
        "genero",
        "carrera",
        "semestre",
        "promedio",
        "empleo",
        "horas_estudio",
        "situacion_economica",
        "apoyo_familiar",
    }
)

# Preferencia del detector para Likert (NO es una cota de validación; §1.3).
_LIKERT_N_MAX = 7


@dataclass(frozen=True)
class TipoPreguntaDetectado:
    """Propuesta de tipo para una columna/pregunta (salida del detector)."""

    question_id: str
    text: str
    type: str
    confianza: str
    es_demografica: bool
    options: list[str] | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    notas: list[str] = field(default_factory=list)


def _normalizar(valor: str) -> str:
    """Minúsculas sin acentos, recortado (para la familia binaria/demográfica)."""
    base = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return base.strip().lower()


def _es_demografica(header: str) -> bool:
    """True si el header (normalizado) coincide con un demográfico conocido."""
    return _normalizar(header).replace(" ", "_") in _DEMOGRAFICOS


def _valores_no_vacios(rows: list[list[str]], col: int) -> list[str]:
    """Celdas no vacías de la columna `col` (ignora filas más cortas)."""
    out: list[str] = []
    for row in rows:
        if col < len(row):
            cell = row[col].strip()
            if cell:
                out.append(cell)
    return out


def _a_entero(valor: str) -> int | None:
    """Parsea un entero exacto (sin parte decimal); None si no aplica."""
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    if f.is_integer():
        return int(f)
    return None


def _a_numero(valor: str) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _detectar_binaria(valores: list[str]) -> bool:
    distintos = {_normalizar(v) for v in valores}
    return bool(distintos) and len(distintos) <= 2 and distintos <= _VALORES_BINARIOS


def _detectar_likert(valores: list[str]) -> tuple[int, int] | None:
    """Likert si TODOS son enteros en un rango contiguo 1..N. Devuelve (min, max)."""
    enteros: list[int] = []
    for v in valores:
        n = _a_entero(v)
        if n is None:
            return None
        enteros.append(n)
    if not enteros:
        return None
    lo, hi = min(enteros), max(enteros)
    if lo != 1:
        return None
    if hi > _LIKERT_N_MAX:
        return None
    # Rango contiguo: cada valor 1..hi presente al menos una vez no se exige,
    # pero sí que todos los valores caigan en 1..hi (ya garantizado por lo/hi).
    return (1, hi)


def _detectar_numerica(valores: list[str]) -> bool:
    return all(_a_numero(v) is not None for v in valores) and bool(valores)


def _detectar_opcion_multiple(valores: list[str]) -> list[str] | None:
    """Conjunto cerrado de etiquetas repetidas; devuelve opciones por frecuencia."""
    n = len(valores)
    if n < 2:
        return None
    frecuencias: dict[str, int] = {}
    orden: list[str] = []
    for v in valores:
        if v not in frecuencias:
            frecuencias[v] = 0
            orden.append(v)
        frecuencias[v] += 1
    distintos = len(frecuencias)
    tope = min(12, int(0.5 * n))
    if distintos < 2 or distintos > tope:
        return None
    # Ordenar por frecuencia descendente, desempatando por orden de aparición.
    return sorted(orden, key=lambda etiqueta: (-frecuencias[etiqueta], orden.index(etiqueta)))


def detectar_tipos(tabla: RawTable) -> list[TipoPreguntaDetectado]:
    """Clasifica cada columna del RawTable preservando el orden de headers.

    Returns:
        Lista de `TipoPreguntaDetectado`, una por columna (question_id q1, q2, …).
    """
    resultado: list[TipoPreguntaDetectado] = []
    for idx, header in enumerate(tabla.headers):
        question_id = f"q{idx + 1}"
        text = header
        es_demo = _es_demografica(header)
        valores = _valores_no_vacios(tabla.rows, idx)

        if not valores:
            resultado.append(
                TipoPreguntaDetectado(
                    question_id=question_id,
                    text=text,
                    type=TIPO_ABIERTA,
                    confianza=CONFIANZA_BAJA,
                    es_demografica=es_demo,
                    notas=[f"Columna '{text}' sin valores: clasificada como abierta."],
                )
            )
            continue

        # Orden de evaluación: binaria -> likert -> numerica_continua -> opcion_multiple -> abierta.
        if _detectar_binaria(valores):
            opciones = _opciones_por_frecuencia(valores)
            resultado.append(
                TipoPreguntaDetectado(
                    question_id=question_id,
                    text=text,
                    type=TIPO_BINARIA,
                    options=opciones,
                    confianza=CONFIANZA_ALTA,
                    es_demografica=es_demo,
                )
            )
            continue

        escala = _detectar_likert(valores)
        if escala is not None:
            lo, hi = escala
            resultado.append(
                TipoPreguntaDetectado(
                    question_id=question_id,
                    text=text,
                    type=TIPO_LIKERT,
                    options=[str(n) for n in range(lo, hi + 1)],
                    scale_min=lo,
                    scale_max=hi,
                    confianza=CONFIANZA_ALTA,
                    es_demografica=es_demo,
                )
            )
            continue

        opciones_mc = _detectar_opcion_multiple(valores)

        if _detectar_numerica(valores):
            resultado.append(
                TipoPreguntaDetectado(
                    question_id=question_id,
                    text=text,
                    type=TIPO_NUMERICA_CONTINUA,
                    confianza=CONFIANZA_MEDIA,
                    es_demografica=es_demo,
                )
            )
            continue

        if opciones_mc is not None:
            resultado.append(
                TipoPreguntaDetectado(
                    question_id=question_id,
                    text=text,
                    type=TIPO_OPCION_MULTIPLE,
                    options=opciones_mc,
                    confianza=CONFIANZA_MEDIA,
                    es_demografica=es_demo,
                )
            )
            continue

        resultado.append(
            TipoPreguntaDetectado(
                question_id=question_id,
                text=text,
                type=TIPO_ABIERTA,
                confianza=CONFIANZA_BAJA,
                es_demografica=es_demo,
            )
        )

    return resultado


def _opciones_por_frecuencia(valores: list[str]) -> list[str]:
    """Etiquetas distintas ordenadas por frecuencia (desc), preservando empate."""
    frecuencias: dict[str, int] = {}
    orden: list[str] = []
    for v in valores:
        if v not in frecuencias:
            frecuencias[v] = 0
            orden.append(v)
        frecuencias[v] += 1
    return sorted(orden, key=lambda etiqueta: (-frecuencias[etiqueta], orden.index(etiqueta)))
