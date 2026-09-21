# survey_intelligence/engine/question_grouping.py
"""
Motor de REAGRUPACIÓN de columnas en preguntas lógicas (rediseño v2).

Reconstruye la estructura lógica del instrumento: columnas hermanas (mismo tronco,
o yes/no de una opción múltiple, o [Rank k], etc.) se agrupan en UNA pregunta.
Una opción nunca se convierte en pregunta; la pregunta padre se preserva.

Funciones PURAS: reciben encabezados + valores por columna (+ columnas administrativas
y plataforma) y devuelven una lista de `GroupedQuestion`. NO tocan contratos Pydantic
ni el pipeline; en Fase 3, S2 v2 traducirá `GroupedQuestion` → CanonicalQuestion.

Ver docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md (reagrupación por preguntas).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from survey_intelligence.contracts.enums import CanonicalQuestionType as QT
from survey_intelligence.engine.profiling.matrix_parser import HeaderParse, parse_header
from survey_intelligence.engine.question_typing import (
    TypeVerdict,
    type_multi_column,
    type_single_column,
)


@dataclass(frozen=True)
class SourceColumnRef:
    """Una columna del archivo que respalda una pregunta (trazabilidad)."""
    raw_header: str
    position: int
    segment: str | None = None   # el ítem/opción entre corchetes, si lo hubo
    rank: int | None = None
    scale: int | None = None


@dataclass(frozen=True)
class GroupedQuestion:
    """Una pregunta lógica reconstruida a partir de 1..N columnas."""
    stem: str
    type: QT
    confidence: float
    fallback: QT | None
    source_columns: list[SourceColumnRef]
    # Etiquetas de opción/ítem detectadas (los textos entre corchetes de las columnas).
    labels: list[str] = field(default_factory=list)
    is_multi_column: bool = False
    reason: str = ""


def _values_of(rows: list[list[str]], col: int) -> list[str]:
    return [row[col] for row in rows if col < len(row)]


def group_questions(
    headers: list[str],
    rows: list[list[str]],
    admin_headers: set[str] | None = None,
) -> list[GroupedQuestion]:
    """
    Agrupa las columnas de una tabla en preguntas lógicas.

    Args:
        headers:       encabezados del archivo (orden original).
        rows:          filas de valores (str por celda).
        admin_headers: encabezados administrativos a excluir (de platform_columns).

    Returns:
        Lista de GroupedQuestion en orden de aparición del primer stem.
    """
    admin = admin_headers or set()

    # 1) Descomponer cada columna (no administrativa) en (stem, segmentos, rank, scale).
    #    Agrupar por stem preservando el orden de primera aparición.
    parsed: list[tuple[int, str, HeaderParse]] = []
    for pos, header in enumerate(headers):
        if header in admin:
            continue
        hp = parse_header(header)
        parsed.append((pos, header, hp))

    grupos: dict[str, list[tuple[int, str, HeaderParse]]] = {}
    orden: list[str] = []
    for pos, header, hp in parsed:
        clave = hp.stem
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append((pos, header, hp))

    # 2) Construir una GroupedQuestion por grupo.
    resultado: list[GroupedQuestion] = []
    for stem in orden:
        cols = grupos[stem]
        multi = len(cols) > 1 or any(c[2].n_brackets > 0 for c in cols)

        source_columns = [
            SourceColumnRef(
                raw_header=header,
                position=pos,
                segment=(hp.segments[0] if hp.segments else None),
                rank=hp.rank,
                scale=hp.scale,
            )
            for (pos, header, hp) in cols
        ]
        labels = [sc.segment for sc in source_columns if sc.segment]

        if len(cols) == 1 and cols[0][2].n_brackets == 0 and cols[0][2].rank is None:
            # Pregunta de una sola columna sin corchetes.
            pos, header, _hp = cols[0]
            verdict: TypeVerdict = type_single_column(header, _values_of(rows, pos))
        else:
            has_rank = any(hp.rank is not None for (_p, _h, hp) in cols)
            has_scale = any(hp.scale is not None for (_p, _h, hp) in cols)
            sibling_values = [_values_of(rows, pos) for (pos, _h, _hp) in cols]
            verdict = type_multi_column(stem, sibling_values, has_rank=has_rank, has_scale_axis=has_scale)

        resultado.append(
            GroupedQuestion(
                stem=stem,
                type=verdict.type,
                confidence=verdict.confidence,
                fallback=verdict.fallback,
                source_columns=source_columns,
                labels=labels,
                is_multi_column=multi,
                reason=verdict.reason,
            )
        )

    return resultado
