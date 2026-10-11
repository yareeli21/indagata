"""Servicio de estandarización (diseño §1.2–§1.7).

Orquesta la etapa que convierte un instrumento `recibido` en `estandarizado`:

  preview(db, id_crudo)       -> propone tipos de pregunta (no persiste).
  estandarizar(db, id_crudo, preguntas) -> re-deriva respondents con los tipos
                                            confirmados, construye el JSON de
                                            dominio, lo escribe vía storage,
                                            setea ruta_json y estado.

No decide dónde viven los archivos: lee/escribe por el `StoragePort`.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from datetime import datetime, timezone
from pathlib import PurePosixPath

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.constants import FAMILIA_POR_TIPO, ParserFamily, TipoInstrumento
from app.parsing import ParseError, parse_file
from app.parsing.document_parser import DocumentParseError, read_document
from app.parsing.raw_table import RawTable
from app.parsing.tabular_parser import TabularParseError, read_tabular
from app.schemas.estandarizacion import (
    EstandarizarResponse,
    PreguntaConfirmada,
    PreviewResponse,
    TipoPreguntaDetectado,
)
from app.standardization import domain_builder, type_detector
from app.storage import StorageError, get_storage
from shared.db.core.config import settings
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData

logger = logging.getLogger(__name__)


# ── Resolución del instrumento y lectura del archivo respondido ───────────────

def _resolver_raw(db: Session, id_crudo: int) -> RawData:
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrumento no encontrado.",
        )
    return raw


def _familia(tipo_instrumento_raw: str) -> ParserFamily:
    """Familia de parser para el tipo de instrumento (default tabular)."""
    try:
        tipo = TipoInstrumento(tipo_instrumento_raw.strip().lower())
    except ValueError:
        return ParserFamily.TABULAR
    return FAMILIA_POR_TIPO.get(tipo, ParserFamily.TABULAR)


def _extension(ruta: str) -> str:
    """Extensión en minúsculas (con punto) a partir de la ruta almacenada."""
    return PurePosixPath(ruta).suffix.lower()


def _leer_bytes(raw: RawData) -> bytes:
    try:
        return get_storage().leer(raw.raw_archivo)
    except StorageError as exc:
        logger.warning("No se pudo leer el archivo del instrumento %s: %s", raw.id_crudo, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo leer el archivo del instrumento.",
        ) from exc


def _parsear_tabla(datos: bytes, extension: str) -> RawTable:
    try:
        return read_tabular(datos, extension)
    except TabularParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo parsear el instrumento: {exc}",
        ) from exc


def _parsear_documento(datos: bytes, extension: str) -> str:
    try:
        doc = read_document(datos, extension)
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo parsear el instrumento: {exc}",
        ) from exc
    return doc.text


# ── Preview ───────────────────────────────────────────────────────────────────

def preview(db: Session, id_crudo: int) -> PreviewResponse:
    """Propone los tipos de pregunta sin persistir nada."""
    raw = _resolver_raw(db, id_crudo)
    familia = _familia(raw.tipo_instrumento)
    datos = _leer_bytes(raw)
    extension = _extension(raw.raw_archivo)

    if familia is ParserFamily.DOCUMENTO:
        texto = _parsear_documento(datos, extension)
        preguntas = [
            TipoPreguntaDetectado(
                question_id="q1",
                text=texto,
                type=type_detector.TIPO_ABIERTA,
                confianza=type_detector.CONFIANZA_BAJA,
                es_demografica=False,
            )
        ]
        return PreviewResponse(
            id_crudo=id_crudo,
            tipo_instrumento=raw.tipo_instrumento,
            preguntas=preguntas,
            n_respondentes_detectados=0,
            notas=["Documento: una sola pregunta abierta con el texto completo."],
        )

    tabla = _parsear_tabla(datos, extension)
    detectados = type_detector.detectar_tipos(tabla)
    notas: list[str] = []
    preguntas: list[TipoPreguntaDetectado] = []
    for d in detectados:
        notas.extend(d.notas)
        preguntas.append(
            TipoPreguntaDetectado(
                question_id=d.question_id,
                text=d.text,
                type=d.type,
                options=d.options,
                scale_min=d.scale_min,
                scale_max=d.scale_max,
                confianza=d.confianza,
                es_demografica=d.es_demografica,
            )
        )
    return PreviewResponse(
        id_crudo=id_crudo,
        tipo_instrumento=raw.tipo_instrumento,
        preguntas=preguntas,
        n_respondentes_detectados=tabla.n_rows,
        notas=notas,
    )


# ── Estandarizar ───────────────────────────────────────────────────────────────

def _normalizar(valor: str) -> str:
    base = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return base.strip().lower()


def _mapa_headers(tabla: RawTable) -> tuple[dict[str, int], list[str]]:
    """header normalizado -> índice de columna, desambiguando duplicados.

    Returns:
        (mapa, notas). Duplicados reciben sufijo __2, __3, … y se nota.
    """
    mapa: dict[str, int] = {}
    notas: list[str] = []
    vistos: dict[str, int] = {}
    for idx, header in enumerate(tabla.headers):
        clave = _normalizar(header)
        if clave in vistos:
            vistos[clave] += 1
            clave_desamb = f"{clave}__{vistos[clave]}"
            notas.append(
                f"Encabezado duplicado '{header}' desambiguado como '{clave_desamb}'."
            )
            mapa[clave_desamb] = idx
        else:
            vistos[clave] = 1
            mapa[clave] = idx
    return mapa, notas


def _parsear_question_id(question_id: str) -> int | None:
    """Devuelve el índice 1-based codificado en 'q<entero>', o None si no parsea.

    Formato esperado: prefijo 'q' seguido de uno o más dígitos (p. ej. 'q1',
    'q33'). Devuelve el entero N (sin convertir a índice 0-based) o None si el
    valor no respeta ese formato. Un None permite el fallback por nombre.
    """
    if not question_id or question_id[0] != "q":
        return None
    resto = question_id[1:]
    if not resto.isdigit():
        return None
    return int(resto)


def _resolver_preguntas_tabular(
    tabla: RawTable,
    preguntas: list[PreguntaConfirmada],
) -> tuple[list[domain_builder.PreguntaDominio], list[str]]:
    """Mapea cada pregunta confirmada a su columna por `question_id`.

    `question_id` tiene forma 'q{N}', con N = índice 1-based de la columna en
    `tabla.headers` (lo genera `type_detector.detectar_tipos`). La columna se
    deriva como `N - 1`. Si el `question_id` no viene o no parsea, se intenta un
    fallback por nombre normalizado contra `_mapa_headers`.

    Raises:
        HTTPException 422 si una pregunta no puede resolverse a una columna
        válida (id fuera de rango o sin match por id ni por nombre).
    """
    mapa, notas = _mapa_headers(tabla)
    n_cols = len(tabla.headers)
    usados: set[int] = set()
    resueltas: list[domain_builder.PreguntaDominio] = []

    for p in preguntas:
        col: int | None = None
        numero = _parsear_question_id(p.question_id)
        if numero is not None:
            # El question_id parsea: el índice DEBE estar en rango (no es un
            # payload legacy, es un id inválido si cae fuera).
            col = numero - 1
            if not (0 <= col < n_cols):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"La pregunta con question_id '{p.question_id}' "
                        f"(texto: '{p.text}') no corresponde a ninguna columna "
                        f"del instrumento (hay {n_cols} columnas)."
                    ),
                )
        else:
            # question_id ausente o no parseable: fallback por nombre.
            col = mapa.get(_normalizar(p.text))

        if col is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La pregunta con question_id '{p.question_id}' "
                    f"(texto: '{p.text}') no se pudo mapear a ninguna columna del "
                    f"instrumento (ni por question_id ni por nombre)."
                ),
            )
        usados.add(col)
        opciones = p.options
        if p.type in domain_builder._TIPOS_CON_OPCIONES and not opciones:
            opciones = _recalcular_opciones(tabla, col, p.type)
        scale_min, scale_max = p.scale_min, p.scale_max
        if p.type == "likert" and (scale_min is None or scale_max is None):
            scale_min, scale_max = _recalcular_escala(tabla, col)
        resueltas.append(
            domain_builder.PreguntaDominio(
                question_id=p.question_id,
                text=p.text,
                type=p.type,
                es_demografica=p.es_demografica,
                columna=col,
                options=opciones,
                scale_min=scale_min,
                scale_max=scale_max,
            )
        )

    no_referenciados = [
        tabla.headers[i] for i in range(len(tabla.headers)) if i not in usados
    ]
    if no_referenciados:
        notas.append(
            "Columnas no referenciadas por ninguna pregunta (ignoradas): "
            + ", ".join(no_referenciados)
        )
    return resueltas, notas


def _recalcular_opciones(tabla: RawTable, col: int, tipo: str) -> list[str] | None:
    valores = [
        row[col].strip()
        for row in tabla.rows
        if col < len(row) and row[col].strip()
    ]
    if not valores:
        return None
    if tipo == "likert":
        lo, hi = _recalcular_escala(tabla, col)
        if lo is not None and hi is not None:
            return [str(n) for n in range(lo, hi + 1)]
        return None
    return type_detector._opciones_por_frecuencia(valores)


def _recalcular_escala(tabla: RawTable, col: int) -> tuple[int | None, int | None]:
    enteros: list[int] = []
    for row in tabla.rows:
        if col < len(row) and row[col].strip():
            try:
                enteros.append(int(float(row[col].strip())))
            except (TypeError, ValueError):
                return (None, None)
    if not enteros:
        return (None, None)
    return (min(enteros), max(enteros))


def _ruta_relativa_proyecto(ruta_stored: str) -> str:
    """Normaliza StoredRef.ruta a relativa-al-proyecto con prefijo 'storage/'.

    Invariante §1.5: la ruta persistida debe ser resoluble por
    `_resolver_por_ruta_json` (que hace PROJECT_ROOT / ruta_json). Como
    `StoredRef.ruta` tiene forma 'raw/<uuid>__...json' relativa a storage/, se
    antepone el nombre del directorio storage (settings.raw_path_abs.parent.name).
    """
    storage_dir = settings.raw_path_abs.parent.name
    return f"{storage_dir}/{ruta_stored}"


def estandarizar(
    db: Session,
    id_crudo: int,
    preguntas: list[PreguntaConfirmada],
) -> EstandarizarResponse:
    """Persiste el JSON de dominio con los tipos confirmados y avanza el estado."""
    raw = _resolver_raw(db, id_crudo)

    procesado = (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )
    if procesado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrumento no encontrado.",
        )
    if procesado.estado == "vectorizado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El instrumento ya fue vectorizado; no puede reestandarizarse.",
        )

    familia = _familia(raw.tipo_instrumento)
    datos = _leer_bytes(raw)
    extension = _extension(raw.raw_archivo)
    titulo = raw.nombre_archivo

    if familia is ParserFamily.DOCUMENTO:
        texto = _parsear_documento(datos, extension)
        json_dominio = domain_builder.construir_documento(
            id_crudo=id_crudo, titulo=titulo, texto=texto
        )
    else:
        tabla = _parsear_tabla(datos, extension)
        resueltas, _notas = _resolver_preguntas_tabular(tabla, preguntas)
        json_dominio = domain_builder.construir_tabular(
            id_crudo=id_crudo, titulo=titulo, tabla=tabla, preguntas=resueltas
        )

    json_bytes = json.dumps(json_dominio, ensure_ascii=False, indent=2).encode("utf-8")
    nombre = f"inst_{id_crudo}.estandarizado.v1.json"

    almacenamiento = get_storage()
    try:
        stored = almacenamiento.guardar(json_bytes, nombre)
    except StorageError as exc:
        logger.exception("No se pudo guardar el JSON estandarizado (id_crudo=%s).", id_crudo)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el JSON estandarizado.",
        ) from exc

    ruta_json = _ruta_relativa_proyecto(stored.ruta)
    try:
        procesado.ruta_json = ruta_json
        procesado.estado = "estandarizado"
        procesado.fecha_procesamiento = datetime.now(timezone.utc)
        db.commit()
        db.refresh(procesado)
    except SQLAlchemyError as exc:
        db.rollback()
        almacenamiento.eliminar(stored.ruta)
        logger.exception("Error al persistir la estandarización (id_crudo=%s).", id_crudo)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la estandarización. Intenta de nuevo.",
        ) from exc

    logger.info(
        "Instrumento %s estandarizado (id_instrumento=%s, ruta_json=%s).",
        id_crudo,
        procesado.id_instrumento,
        ruta_json,
    )
    return EstandarizarResponse(
        id_crudo=id_crudo,
        id_instrumento=procesado.id_instrumento,
        estado=procesado.estado,
        ruta_json=ruta_json,
        json_instrumento=json_dominio,
        mensaje="Instrumento estandarizado.",
    )
