# survey_intelligence/pipeline/stages/s2_canonical_builder.py
"""
Etapa S2 — Construcción del Canonical Survey Model.

Convierte el RawTable + detección de plataforma (S1) en el modelo canónico:
  - normaliza nombres de variable (únicos, snake_case).
  - clasifica cada columna: platform_metadata | free_text | question | unknown.
  - parsea preguntas-matriz "tronco [ítem]" / "tronco .subítem" y agrupa ítems
    bajo su pregunta matriz.
  - calcula canonical_id como hash determinístico del contenido normalizado.

Es una de las dos etapas FATALES. 100% determinística: sin LLM. El profiling
estadístico (escalas, nulos, cardinalidad) se añade en S3 (Tarea 5); aquí esos
campos quedan en None.
"""
from __future__ import annotations

import hashlib
import json

from survey_intelligence.contracts.canonical import (
    CanonicalQuestion,
    CanonicalSurveyModel,
    CanonicalVariable,
    Dimensions,
    MatrixGroup,
    QuestionOption,
    QuestionResponse,
    SourceColumn,
    SourceInfo,
)
from survey_intelligence.contracts.enums import ColumnClass, DataType, SourceEncoding
from survey_intelligence.engine.profiling.matrix_parser import parse_matrix
from survey_intelligence.engine.profiling.name_normalizer import (
    normalize_name,
    unique_names,
)
from survey_intelligence.pipeline.stages.s1_ingestion import IngestionResult

# Umbrales para clasificar texto libre por forma (heurística determinística).
_FREE_TEXT_MIN_AVG_CHARS = 40   # longitud promedio de celda no vacía
_FREE_TEXT_MIN_UNIQUE_RATIO = 0.6  # proporción de valores únicos


def _column_values(raw_rows: list[list[str]], col: int) -> list[str]:
    return [row[col] for row in raw_rows if col < len(row)]


def _looks_free_text(values: list[str]) -> bool:
    """Una columna es texto libre si sus celdas no vacías son largas y muy variadas."""
    non_empty = [v for v in values if v.strip()]
    if len(non_empty) < 2:
        return False
    avg_len = sum(len(v) for v in non_empty) / len(non_empty)
    unique_ratio = len(set(non_empty)) / len(non_empty)
    return avg_len >= _FREE_TEXT_MIN_AVG_CHARS and unique_ratio >= _FREE_TEXT_MIN_UNIQUE_RATIO


def _canonical_id(headers: list[str], normalized_names: list[str], n_rows: int) -> str:
    """
    Hash determinístico del contenido estructural normalizado.

    Depende de encabezados normalizados, nombres canónicos y nº de filas: el mismo
    archivo produce el mismo id. No depende del orden de lectura ni de metadatos.
    """
    payload = json.dumps(
        {"headers": headers, "names": normalized_names, "n_rows": n_rows},
        ensure_ascii=False,
        sort_keys=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_canonical(
    ingestion: IngestionResult,
    file_name: str,
    sheet: str | None,
    question_grouping: bool = False,
) -> CanonicalSurveyModel:
    """
    Ensambla el CanonicalSurveyModel a partir del resultado de S1.

    Si `question_grouping=True` (rediseño v2), además de `variables[]` (compatibilidad),
    reagrupa columnas en `questions[]` lógicas con tipo canónico, opciones, trazabilidad
    (`source_columns`) y `respondents_index`. Con `question_grouping=False` (default), el
    comportamiento es EXACTAMENTE el actual (v1): `variables[]` + `questions[]` por matriz/simple.
    """
    raw = ingestion.raw_table
    admin_headers = ingestion.platform.admin_headers
    headers = raw.headers

    base_names = [normalize_name(h) for h in headers]
    names = unique_names(base_names)

    variables: list[CanonicalVariable] = []
    # Mapa stem -> lista de variable_ids (para agrupar la matriz en preguntas).
    matrix_groups: dict[str, list[str]] = {}
    # Preguntas simples: variable_id -> texto.
    simple_questions: list[tuple[str, str]] = []

    for pos, header in enumerate(headers):
        variable_id = f"v_{pos + 1:03d}"
        values = _column_values(raw.rows, pos)

        # Clasificación de columna.
        if header in admin_headers:
            column_class = ColumnClass.PLATFORM_METADATA
            data_type = DataType.UNKNOWN
        elif _looks_free_text(values):
            column_class = ColumnClass.FREE_TEXT
            data_type = DataType.FREE_TEXT
        else:
            column_class = ColumnClass.QUESTION
            data_type = DataType.UNKNOWN  # el tipo fino lo asigna S3

        # Parsing de matriz solo para preguntas.
        matrix_group: MatrixGroup | None = None
        if column_class == ColumnClass.QUESTION:
            parsed = parse_matrix(header)
            if parsed.is_matrix and parsed.stem and parsed.item:
                matrix_group = MatrixGroup(stem=parsed.stem, item=parsed.item)
                matrix_groups.setdefault(parsed.stem, []).append(variable_id)
            else:
                simple_questions.append((variable_id, header))

        variables.append(
            CanonicalVariable(
                variable_id=variable_id,
                raw_header=header,
                normalized_name=names[pos],
                position=pos + 1,
                column_class=column_class,
                inferred_data_type=data_type,
                detected_scale=None,
                matrix_group=matrix_group,
                value_distribution=None,
                profiling_stats=None,
            )
        )

    # Construir preguntas canónicas: una por grupo matriz + una por pregunta simple.
    questions: list[CanonicalQuestion] = []
    q_counter = 0
    header_by_vid = {v.variable_id: v.raw_header for v in variables}
    item_by_vid = {
        v.variable_id: (v.matrix_group.item if v.matrix_group else v.raw_header)
        for v in variables
    }

    for stem, vids in matrix_groups.items():
        q_counter += 1
        # El texto de la pregunta matriz es el tronco; los ítems son las variables.
        questions.append(
            CanonicalQuestion(
                question_id=f"q_{q_counter:03d}",
                variable_ids=vids,
                text=stem,
                length_chars=len(stem),
                length_words=len(stem.split()),
            )
        )

    for vid, text in simple_questions:
        q_counter += 1
        questions.append(
            CanonicalQuestion(
                question_id=f"q_{q_counter:03d}",
                variable_ids=[vid],
                text=text,
                length_chars=len(text),
                length_words=len(text.split()),
            )
        )

    canonical_id = _canonical_id(headers, names, raw.n_rows)

    source = SourceInfo(
        platform_guess=ingestion.platform.platform_guess,
        file_name=file_name,
        sheet=sheet,
    )
    dimensions = Dimensions(n_rows=raw.n_rows, n_columns=raw.n_columns)

    if not question_grouping:
        # Vía v1 (default): comportamiento idéntico al actual.
        return CanonicalSurveyModel(
            canonical_id=canonical_id,
            source=source,
            dimensions=dimensions,
            variables=variables,
            questions=questions,
        )

    # ── Vía v2 (bandera on): reagrupar columnas en preguntas lógicas ─────────
    # variables[] se conserva tal cual (capa de compatibilidad para S3..S9/SAV).
    v2_questions = _build_v2_questions(ingestion, headers, admin_headers, variables)
    respondents_index = [f"R{i + 1}" for i in range(raw.n_rows)]
    # canonical_id v2 incluye la agrupación (estructura distinta → id distinto).
    v2_canonical_id = "sha256:v2:" + canonical_id.split(":", 1)[-1]

    return CanonicalSurveyModel(
        canonical_id=v2_canonical_id,
        source=source,
        dimensions=dimensions,
        variables=variables,
        questions=v2_questions,
        respondents_index=respondents_index,
    )


def _build_v2_questions(
    ingestion: IngestionResult,
    headers: list[str],
    admin_headers: set[str],
    variables: list[CanonicalVariable],
) -> list[CanonicalQuestion]:
    """
    Construye las CanonicalQuestion v2 (pregunta como unidad lógica) reagrupando
    columnas hermanas con los motores question_grouping / question_typing.

    Determinístico y sin LLM. Enlaza cada pregunta con sus columnas de origen
    (source_columns) y con las variables[] de compatibilidad (variable_ids) por posición.
    """
    # Import local para no crear ciclos de import a nivel de módulo.
    from survey_intelligence.engine.question_grouping import group_questions

    raw = ingestion.raw_table
    # variable_id por posición de columna (variables[] va en orden de columnas).
    vid_by_pos = {v.position - 1: v.variable_id for v in variables}

    grouped = group_questions(headers, raw.rows, admin_headers=admin_headers)

    _ENC = {
        "yes_no": SourceEncoding.YES_NO,
        "scale_bracket": SourceEncoding.SCALE_BRACKET,
        "single_cell": SourceEncoding.SINGLE_CELL,
    }

    questions: list[CanonicalQuestion] = []
    for i, g in enumerate(grouped):
        # Etiquetas de opción -> QuestionOption (dominio de respuesta reconstruido).
        options = [
            QuestionOption(option_id=f"o{j + 1}", label=label)
            for j, label in enumerate(g.labels)
        ]
        # Trazabilidad a las columnas del archivo.
        source_columns: list[SourceColumn] = []
        for sc in g.source_columns:
            if sc.rank is not None:
                enc = SourceEncoding.RANK_BRACKET
            elif sc.scale is not None:
                enc = SourceEncoding.DUAL_BRACKET
            elif sc.segment is not None:
                # yes/no si es opción múltiple; escala si es matriz/likert.
                enc = SourceEncoding.YES_NO if g.type.value == "opcion_multiple" else SourceEncoding.SCALE_BRACKET
            else:
                enc = SourceEncoding.SINGLE_CELL
            maps_to: dict = {}
            if sc.segment is not None:
                maps_to = {"label": sc.segment}
            source_columns.append(
                SourceColumn(raw_header=sc.raw_header, position=sc.position, encoding=enc, maps_to=maps_to)
            )
        variable_ids = [
            vid_by_pos[sc.position] for sc in g.source_columns if sc.position in vid_by_pos
        ]
        # Respuestas reconstruidas por respondente (fila del archivo).
        responses = _build_responses(g, options, raw.rows, raw.n_rows)
        questions.append(
            CanonicalQuestion(
                question_id=f"q_{i + 1:03d}",
                variable_ids=variable_ids,
                text=g.stem,
                length_chars=len(g.stem),
                length_words=len(g.stem.split()),
                type=g.type,
                type_confidence=g.confidence,
                type_fallback=g.fallback,
                options=options,
                source_columns=source_columns,
                responses=responses,
                metadata={"reason": g.reason, "is_multi_column": g.is_multi_column},
            )
        )
    return questions


# Tokens que cuentan como "seleccionado" en columnas yes/no (opción múltiple).
_YES = {"yes", "sí", "si", "true", "1", "x", "checked", "seleccionado"}


def _build_responses(grouped, options, rows, n_rows: int) -> list["QuestionResponse"]:
    """
    Reconstruye la respuesta de cada respondente a una pregunta (rediseño v2).

    Determinístico, sin LLM. La forma de `value`/`labels` depende del tipo:
      - opcion_multiple (columnas yes/no): value = [option_id...], labels = [etiquetas...].
      - una sola columna (opción única / likert / numérica / texto / fecha): value = texto de la celda.
      - matriz/multi-columna (no yes/no): value = { label_columna: valor } por columna con dato.
    Filas sin ningún dato en las columnas de la pregunta se omiten (no respondió).
    """
    positions = [sc.position for sc in grouped.source_columns]
    labels_by_pos = {sc.position: sc.segment for sc in grouped.source_columns}
    opt_by_label = {o.label: o.option_id for o in options}
    is_multi_yes_no = grouped.type.value == "opcion_multiple"

    def _cell(row: list[str], pos: int) -> str:
        return row[pos].strip() if pos < len(row) and row[pos] is not None else ""

    responses: list[QuestionResponse] = []
    for i in range(n_rows):
        row = rows[i] if i < len(rows) else []
        rid = f"R{i + 1}"

        if is_multi_yes_no:
            sel_ids: list[str] = []
            sel_labels: list[str] = []
            for pos in positions:
                if _cell(row, pos).lower() in _YES:
                    label = labels_by_pos.get(pos)
                    if label:
                        sel_labels.append(label)
                        oid = opt_by_label.get(label)
                        if oid:
                            sel_ids.append(oid)
            if sel_ids or sel_labels:
                responses.append(QuestionResponse(respondent_id=rid, value=sel_ids, labels=sel_labels))
            continue

        if len(positions) == 1:
            val = _cell(row, positions[0])
            if val:
                responses.append(QuestionResponse(respondent_id=rid, value=val, labels=val))
            continue

        # Multi-columna no yes/no (matriz/likert): dict por columna con dato.
        celda_por_item: dict = {}
        for pos in positions:
            val = _cell(row, pos)
            if val:
                celda_por_item[labels_by_pos.get(pos) or f"col_{pos}"] = val
        if celda_por_item:
            responses.append(QuestionResponse(respondent_id=rid, value=celda_por_item, labels=celda_por_item))

    return responses
