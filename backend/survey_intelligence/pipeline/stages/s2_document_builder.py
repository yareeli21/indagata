# survey_intelligence/pipeline/stages/s2_document_builder.py
"""
Etapa S2 (vía documento) — Canonical builder para instrumentos narrativos.

Para entrevistas y pruebas estandarizadas (no tabulares). Estrategia LIGERA: segmenta
el texto plano en "variables documentales" (secciones/párrafos significativos) y produce
el MISMO CanonicalSurveyModel que la vía encuesta, para que S4..S9 apliquen sin cambios.

No detecta escalas ni matrices (los documentos narrativos no las tienen). Cada segmento
es una variable de tipo free_text.
"""
from __future__ import annotations

import hashlib
import json
import re

from survey_intelligence.contracts.canonical import (
    CanonicalQuestion,
    CanonicalSurveyModel,
    CanonicalVariable,
    Dimensions,
    SourceInfo,
)
from survey_intelligence.contracts.enums import ColumnClass, DataType
from survey_intelligence.engine.profiling.name_normalizer import normalize_name, unique_names

# Un segmento es un bloque separado por líneas en blanco, o una línea que parece
# pregunta (termina en '?' o empieza con número/viñeta).
_QUESTION_LINE = re.compile(r"(\?\s*$)|(^\s*\d+[\.\)]\s+)|(^\s*[-*]\s+)")

# Longitud mínima de un segmento para considerarlo significativo.
_MIN_SEGMENT_CHARS = 15


def _segment_text(text: str) -> list[str]:
    """Segmenta el texto en bloques significativos (párrafos / preguntas)."""
    # Normaliza saltos y separa por líneas en blanco.
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    segments: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Si el bloque tiene varias preguntas por línea, sepáralas.
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        buffer: list[str] = []
        for ln in lines:
            buffer.append(ln)
            if _QUESTION_LINE.search(ln):
                seg = " ".join(buffer).strip()
                if len(seg) >= _MIN_SEGMENT_CHARS:
                    segments.append(seg)
                buffer = []
        if buffer:
            seg = " ".join(buffer).strip()
            if len(seg) >= _MIN_SEGMENT_CHARS:
                segments.append(seg)
    return segments


def _canonical_id(segments: list[str]) -> str:
    payload = json.dumps({"segments": segments}, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_document_canonical(
    text: str, file_name: str, dc_type: str
) -> CanonicalSurveyModel:
    """
    Construye un Canonical documental a partir de texto plano.

    Args:
        text:      texto extraído del PDF/DOCX (lo provee el host).
        file_name: nombre del archivo original.
        dc_type:   tipo de instrumento (entrevista | prueba_estandarizada).
    """
    segments = _segment_text(text)

    base_names = [normalize_name(s) for s in segments]
    names = unique_names(base_names) if base_names else []

    variables: list[CanonicalVariable] = []
    questions: list[CanonicalQuestion] = []
    for pos, seg in enumerate(segments):
        vid = f"v_{pos + 1:03d}"
        variables.append(CanonicalVariable(
            variable_id=vid,
            raw_header=seg[:200],  # encabezado = inicio del segmento
            normalized_name=names[pos],
            position=pos + 1,
            column_class=ColumnClass.FREE_TEXT,
            inferred_data_type=DataType.FREE_TEXT,
        ))
        questions.append(CanonicalQuestion(
            question_id=f"q_{pos + 1:03d}",
            variable_ids=[vid],
            text=seg,
            length_chars=len(seg),
            length_words=len(seg.split()),
        ))

    return CanonicalSurveyModel(
        canonical_id=_canonical_id(segments),
        source=SourceInfo(platform_guess=f"documento:{dc_type}", file_name=file_name),
        dimensions=Dimensions(n_rows=0, n_columns=len(segments)),
        variables=variables,
        questions=questions,
    )
