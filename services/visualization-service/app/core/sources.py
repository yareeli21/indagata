"""Obtención de contenido y metadata de instrumentos para el RAG (diseño §4.2).

`resolver_artefacto(instrumentoId)` localiza el JSON del instrumento (clave =
`str(id_crudo)`, §2.1) en este orden (§2.8 (b)):

  1. storage-service: GET {STORAGE_SERVICE_URL}/almacenamiento/artefacto/analysis/<id>
     y, si falta, .../metadata/<id>. La base se lee con
     `os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004")` — NUNCA
     vía `settings` (AppSettings NO define STORAGE_SERVICE_URL; con
     `extra="ignore"` pydantic lo descartaría y daría AttributeError).
  2. `instrumento_procesado.ruta_json` si hay BD disponible vía `shared`.
  3. Fallback a `storage/raw/inst_<NN>.v*.json`: traduce `id_crudo -> inst_XX`
     por `_seed_map.json` o por el mapeo directo `N -> inst_{N:02d}`, y abre la
     última versión (`glob`), bajo `settings.raw_path_abs`.

`extraer_texto(json)` concatena título + objetivo + dimensiones + preguntas con
sus opciones (fallback a `dc:description`). `extraer_metadata(json, id)` devuelve
`{instrumentoId, titulo, tipo (mapeado §2.4), investigador, kpis}`.

NOTA (Chroma): `kpis` es una lista, pero la metadata de Chroma solo acepta
escalares; el router serializa `kpis` a string JSON al hacer upsert (§4.6) y lo
deserializa al construir `FuenteChatOut`. Aquí `kpis` se devuelve como lista.
"""
from __future__ import annotations

import json as jsonlib
import logging
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core import agregacion, original_txt
from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_SEED_MAP_NOMBRE = "_seed_map.json"
_STORAGE_DEFAULT = "http://storage-service:8004"

# ── Mapeo canónico de tipo backend -> frontend (§2.4) ────────────────────────
_TIPO_MAP: dict[str, str] = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_TIPO_DEFAULT = "Encuesta"


def _como_dict(valor: Any) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def _como_lista(valor: Any) -> list[Any]:
    return valor if isinstance(valor, list) else []


def _texto(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


# ── (1) storage-service ───────────────────────────────────────────────────────
async def _resolver_desde_storage(instrumento_id: str) -> dict[str, Any] | None:
    """GET analysis/<id> y, si falta, metadata/<id> del storage-service."""
    base = os.getenv("STORAGE_SERVICE_URL", _STORAGE_DEFAULT).rstrip("/")
    for tipo in ("analysis", "metadata"):
        url = f"{base}/almacenamiento/artefacto/{tipo}/{instrumento_id}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as cliente:
                resp = await cliente.get(url)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("storage-service no disponible (%s): %s", url, exc)
            return None
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            logger.warning("storage-service respondió %s en %s", resp.status_code, url)
            continue
        try:
            detalle = resp.json()
        except ValueError:
            continue
        contenido = _como_dict(detalle).get("contenido")
        if isinstance(contenido, dict) and contenido:
            return contenido
    return None


# ── (2) BD: instrumento_procesado.ruta_json ────────────────────────────────────
def _resolver_desde_bd(instrumento_id: str) -> dict[str, Any] | None:
    """Lee `instrumento_procesado.ruta_json` por `id_crudo` si hay BD."""
    try:
        id_crudo = int(instrumento_id)
    except (TypeError, ValueError):
        return None
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from shared.models.instrumento_procesado import InstrumentoProcesado
    except Exception as exc:  # pragma: no cover - sin BD/driver disponible
        logger.debug("BD no disponible para resolución: %s", exc)
        return None
    try:
        engine = create_engine(settings.DATABASE_URL)
        with Session(engine) as sesion:
            procesado = sesion.scalar(
                select(InstrumentoProcesado).where(
                    InstrumentoProcesado.id_crudo == id_crudo
                )
            )
            ruta_json = getattr(procesado, "ruta_json", None) if procesado else None
    except Exception as exc:  # pragma: no cover - Postgres caído
        logger.debug("No se pudo consultar la BD: %s", exc)
        return None
    if not ruta_json:
        return None
    ruta = Path(ruta_json)
    if not ruta.is_absolute():
        ruta = settings.PROJECT_ROOT / ruta_json
    return _leer_json(ruta) if ruta.is_file() else None


# ── (3) Fallback a storage/raw ─────────────────────────────────────────────────
def _leer_json(ruta: Path) -> dict[str, Any] | None:
    try:
        with ruta.open("r", encoding="utf-8") as fh:
            data = jsonlib.load(fh)
    except (OSError, jsonlib.JSONDecodeError) as exc:
        logger.warning("No se pudo leer el JSON %s: %s", ruta, exc)
        return None
    return data if isinstance(data, dict) else None


def _cargar_seed_map() -> dict[str, int]:
    ruta = settings.raw_path_abs / _SEED_MAP_NOMBRE
    data = _leer_json(ruta) if ruta.is_file() else None
    if not data:
        return {}
    mapa: dict[str, int] = {}
    for clave, valor in data.items():
        try:
            mapa[str(clave)] = int(valor)
        except (TypeError, ValueError):
            continue
    return mapa


def _slug_por_id_crudo(id_crudo: int) -> str | None:
    seed_map = _cargar_seed_map()
    for inst, cid in seed_map.items():
        if cid == id_crudo:
            return inst
    if id_crudo >= 1:
        return f"inst_{id_crudo:02d}"
    return None


def _resolver_fallback_raw(instrumento_id: str) -> dict[str, Any] | None:
    try:
        id_crudo = int(instrumento_id)
    except (TypeError, ValueError):
        return None
    slug = _slug_por_id_crudo(id_crudo)
    if slug is None:
        return None
    candidatos = sorted(settings.raw_path_abs.glob(f"{slug}.v*.json"))
    if not candidatos:
        logger.debug("Sin artefacto en storage/raw para %s", slug)
        return None
    return _leer_json(candidatos[-1])


async def resolver_artefacto(instrumento_id: str) -> dict[str, Any] | None:
    """Resuelve el JSON del instrumento en el orden §2.8 (b).

    Devuelve el `dict` del JSON o `None` si ninguna fuente lo resuelve.
    """
    desde_storage = await _resolver_desde_storage(instrumento_id)
    if desde_storage is not None:
        return desde_storage
    desde_bd = _resolver_desde_bd(instrumento_id)
    if desde_bd is not None:
        return desde_bd
    return _resolver_fallback_raw(instrumento_id)


# ── Extracción de texto y metadata ─────────────────────────────────────────────
def extraer_texto(instrumento_json: dict[str, Any] | None) -> str:
    """Texto a indexar: título + objetivo + dimensiones + preguntas/opciones.

    Fallback si `instrument` falta: `metadata.dublin_core["dc:description"]`.
    """
    data = _como_dict(instrumento_json)
    instrumento = _como_dict(data.get("instrument"))

    partes: list[str] = []
    titulo = _texto(instrumento.get("title"))
    if titulo:
        partes.append(titulo)
    objetivo = _texto(instrumento.get("objective"))
    if objetivo:
        partes.append(objetivo)

    dimensiones = [_texto(d) for d in _como_lista(instrumento.get("dimensions_explored"))]
    dimensiones = [d for d in dimensiones if d]
    if dimensiones:
        partes.append("\n".join(dimensiones))

    for seccion in _como_lista(instrumento.get("sections")):
        for pregunta in _como_lista(_como_dict(seccion).get("questions")):
            pregunta = _como_dict(pregunta)
            bloque: list[str] = []
            texto_q = _texto(pregunta.get("text"))
            if texto_q:
                bloque.append(texto_q)
            opciones = [_texto(o) for o in _como_lista(pregunta.get("options"))]
            opciones = [o for o in opciones if o]
            if opciones:
                bloque.append("\n".join(opciones))
            if bloque:
                partes.append("\n".join(bloque))

    if not partes:
        metadata = _como_dict(data.get("metadata"))
        dublin_core = _como_dict(metadata.get("dublin_core"))
        descripcion = _texto(dublin_core.get("dc:description"))
        if descripcion:
            partes.append(descripcion)

    return "\n\n".join(partes)


def _mapear_tipo(tipo_raw: str | None) -> str:
    clave = (tipo_raw or "").strip().lower()
    tipo = _TIPO_MAP.get(clave)
    if tipo is None:
        if clave:
            logger.warning("tipo desconocido %r; se mapea a %r.", tipo_raw, _TIPO_DEFAULT)
        return _TIPO_DEFAULT
    return tipo


def extraer_kpis(instrumento_json: dict[str, Any] | None) -> list[str]:
    """KPIs = `design_reference.kpi_hints` (lista de str)."""
    data = _como_dict(instrumento_json)
    design = _como_dict(data.get("design_reference"))
    return [str(k) for k in _como_lista(design.get("kpi_hints")) if _texto(k)]


def extraer_metadata(
    instrumento_json: dict[str, Any] | None,
    instrumento_id: str,
    titulo_override: str | None = None,
) -> dict[str, Any]:
    """Metadata del instrumento para Chroma / FuenteChatOut (§4.2).

    Devuelve `{instrumentoId, titulo, tipo (mapeado), investigador, kpis}`.
    `tipo` se infiere de `metadata.dublin_core["dc:type"]` solo de forma
    informativa; el esquema real no trae el tipo canónico de `raw_data`, así que
    si no mapea cae al default "Encuesta" (§2.4). `kpis` es lista (el router la
    serializa a JSON string para la metadata de Chroma).

    Precedencia del título (§15.2, EXACTA): `dc:title` → `titulo_override`
    (cabecera "INSTRUMENTO:" del .txt) → `instrument.title` (nombre del CSV) →
    `f"Instrumento {id}"`. `titulo_override` es opcional y retrocompatible.
    """
    data = _como_dict(instrumento_json)
    instrumento = _como_dict(data.get("instrument"))
    metadata = _como_dict(data.get("metadata"))
    dublin_core = _como_dict(metadata.get("dublin_core"))

    titulo = (
        _texto(dublin_core.get("dc:title"))
        or _texto(titulo_override)
        or _texto(instrumento.get("title"))
        or f"Instrumento {instrumento_id}"
    )
    investigador = _texto(dublin_core.get("dc:creator"))

    return {
        "instrumentoId": instrumento_id,
        "titulo": titulo,
        "tipo": _mapear_tipo(dublin_core.get("dc:type")),
        "investigador": investigador,
        "kpis": extraer_kpis(data),
    }


# ── Construcción de chunks pre-redactados (§6.1, §6.5, §7, §9, §15.2, §15.3) ───
@dataclass(frozen=True)
class ChunkIndexable:
    """Un chunk ya redactado listo para indexar (§6.1)."""

    texto: str
    clase: str  # "estructura" | "hallazgos" | "grupo_desempeno"
    dimension: str  # "" para resumen global / cabecera de estructura


# Tipos de pregunta no agregables como hallazgo (§4.2: `abierta` se omite).
_TIPO_NUMERICO = "numerica_continua"
_TIPO_BINARIO = "binaria"
_TIPO_CATEGORICO = "opcion_multiple"

# Columnas que son ARQUETIPOS/metadatos de los datos sintéticos, no respuestas reales
# del instrumento. No existen en datos reales (p.ej. "perfil"=P1..P8, "profile_id"),
# así que no deben generar chunks: confundirían al LLM y no aportan al diagnóstico.
# Se comparan en forma normalizada (minúsculas, sin acentos, espacios→_) contra el
# `text` y el `question_id` de la pregunta.
_COLUMNAS_ARTEFACTO = frozenset({"perfil", "profile_id", "profile", "arquetipo"})


def _es_columna_artefacto(texto_q: str, qid: str) -> bool:
    """True si la columna es un arquetipo sintético (perfil/profile_id) a excluir."""
    def _norm(v: str) -> str:
        base = unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode("ascii")
        return base.strip().lower().replace(" ", "_")

    return _norm(texto_q) in _COLUMNAS_ARTEFACTO or _norm(qid) in _COLUMNAS_ARTEFACTO


def _preguntas(instrumento: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana todas las preguntas de todas las secciones en orden del JSON."""
    preguntas: list[dict[str, Any]] = []
    for seccion in _como_lista(instrumento.get("sections")):
        for pregunta in _como_lista(_como_dict(seccion).get("questions")):
            preguntas.append(_como_dict(pregunta))
    return preguntas


def _id_crudo_param(instrumento_id: str, artefacto: dict[str, Any]) -> str:
    """Fuente de verdad del id (§15.3-NIT3): el parámetro del router; si no
    parsea a entero, se respalda en `artefacto["instrument_id"]`."""
    try:
        int(str(instrumento_id).removeprefix("upload_"))
        return instrumento_id
    except (TypeError, ValueError):
        respaldo = _texto(artefacto.get("instrument_id"))
        return respaldo or instrumento_id


def _chunk_cabecera(
    data: dict[str, Any], titulo: str
) -> ChunkIndexable | None:
    """Chunk de cabecera de estructura: título real + descripción + constructo."""
    metadata = _como_dict(data.get("metadata"))
    dublin_core = _como_dict(metadata.get("dublin_core"))
    survey = _como_dict(metadata.get("survey_specific"))

    partes = [f"Instrumento: {titulo}."]
    descripcion = _texto(dublin_core.get("dc:description"))
    if descripcion:
        partes.append(descripcion)
    constructo = _texto(survey.get("constructo_principal"))
    if constructo:
        partes.append(f"Constructo principal: {constructo}.")
    return ChunkIndexable(texto=" ".join(partes), clase="estructura", dimension="")


def _chunks_estructura_dimension(
    questions_likert: list[dict[str, Any]], mapa: dict[str, tuple[str, str]]
) -> list[ChunkIndexable]:
    """Un chunk de estructura por dimensión: título + ítems redactados numerados.

    Agrupa las preguntas likert por su dimensión (según el mapa) preservando el
    orden de aparición. En modo degradado el mapa viene del fallback por prefijo
    (etiquetas normalizadas, nunca mojibake crudo).
    """
    orden: list[str] = []
    items_por_dim: dict[str, list[str]] = {}
    for q in questions_likert:
        qid = _texto(q.get("question_id"))
        dim, texto_item = mapa.get(qid, ("", ""))
        if not dim:
            continue
        if dim not in items_por_dim:
            items_por_dim[dim] = []
            orden.append(dim)
        items_por_dim[dim].append(texto_item)

    chunks: list[ChunkIndexable] = []
    for dim in orden:
        lineas = [f"Dimensión «{dim}», ítems evaluados:"]
        for i, texto_item in enumerate(items_por_dim[dim], start=1):
            lineas.append(f"{i}. {texto_item}")
        chunks.append(
            ChunkIndexable(texto="\n".join(lineas), clase="estructura", dimension=dim)
        )
    return chunks


def titulo_override_txt(artefacto: dict[str, Any] | None, instrumento_id: str) -> str | None:
    """Título legible de la cabecera del .txt original, o `None` si no hay .txt.

    Punto único de resolución del `titulo_override` (§15.2 punto 2): lo usan
    tanto `construir_chunks` (cabecera de estructura y metadata interna) como el
    router (metadata de Chroma), para que el título no diverja. Degrada en
    silencio a `None` ante cualquier fallo de I/O.
    """
    data = _como_dict(artefacto)
    id_crudo = _id_crudo_param(instrumento_id, data)
    try:
        texto_original = original_txt.leer_texto_original(id_crudo)
        if not texto_original:
            return None
        return original_txt.parsear_estructura(texto_original).titulo_instrumento
    except Exception as exc:  # noqa: BLE001 - degradación grácil
        logger.warning("No se pudo leer el título del .txt original: %s", exc)
        return None


def construir_chunks(
    artefacto: dict[str, Any] | None, instrumento_id: str
) -> list[ChunkIndexable]:
    """Orquesta `original_txt` + `agregacion` en chunks pre-redactados (§6.1).

    Devuelve `list[ChunkIndexable]` o `[]` si el JSON no trae instrument/preguntas
    (el router degrada entonces al camino `extraer_texto` + `trocear`). Cada
    bloque va envuelto en su propio `try/except` con `logger.warning`: una
    dimensión que falle no tumba el resto (§6.5, §9).
    """
    data = _como_dict(artefacto)
    instrumento = _como_dict(data.get("instrument"))
    preguntas = _preguntas(instrumento)
    if not instrumento or not preguntas:
        return []

    id_crudo = _id_crudo_param(instrumento_id, data)
    questions_likert = [q for q in preguntas if _texto(q.get("type")) == "likert"]
    respondents = _como_lista(data.get("respondents"))

    # .txt original (estructura legible + mapeo question_id -> dimensión).
    estructura = None
    mapa: dict[str, tuple[str, str]] = {}
    try:
        texto_original = original_txt.leer_texto_original(id_crudo)
        if texto_original:
            estructura = original_txt.parsear_estructura(texto_original)
        if estructura is not None:
            mapa = original_txt.construir_mapa_dimension(estructura, questions_likert)
        if not mapa and questions_likert:
            mapa = original_txt.mapa_por_prefijo(questions_likert)
    except Exception as exc:  # noqa: BLE001 - degradación grácil (§6.5)
        logger.warning("No se pudo resolver el .txt original: %s", exc)
        try:
            mapa = original_txt.mapa_por_prefijo(questions_likert)
        except Exception as exc2:  # noqa: BLE001
            logger.warning("Fallback por prefijo también falló: %s", exc2)
            mapa = {}

    titulo_override = estructura.titulo_instrumento if estructura is not None else None
    # Un único punto de verdad del título (§15.2 punto 2).
    titulo = extraer_metadata(data, instrumento_id, titulo_override=titulo_override).get(
        "titulo", ""
    )

    chunks: list[ChunkIndexable] = []

    # (A) Chunks de ESTRUCTURA ────────────────────────────────────────────────
    try:
        cabecera = _chunk_cabecera(data, titulo)
        if cabecera is not None:
            chunks.append(cabecera)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falló el chunk de cabecera: %s", exc)
    try:
        chunks.extend(_chunks_estructura_dimension(questions_likert, mapa))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallaron los chunks de estructura por dimensión: %s", exc)

    # (B) Chunks de HALLAZGOS ──────────────────────────────────────────────────
    if not respondents:
        return chunks

    hallazgos: list[agregacion.HallazgoDimension] = []

    # Likert: un chunk por dimensión (agrupando por el mapa, orden de aparición).
    orden_dim: list[str] = []
    items_por_dim: dict[str, list[tuple[str, str, int, int]]] = {}
    for q in questions_likert:
        qid = _texto(q.get("question_id"))
        dim, texto_item = mapa.get(qid, ("", ""))
        if not dim:
            continue
        smin = q.get("scale_min")
        smax = q.get("scale_max")
        smin = int(smin) if isinstance(smin, (int, float)) else 1
        smax = int(smax) if isinstance(smax, (int, float)) else 5
        if dim not in items_por_dim:
            items_por_dim[dim] = []
            orden_dim.append(dim)
        items_por_dim[dim].append((qid, texto_item, smin, smax))

    for dim in orden_dim:
        try:
            h = agregacion.agregar_likert(items_por_dim[dim], respondents, dim)
            if h is not None:
                hallazgos.append(h)
                chunks.append(
                    ChunkIndexable(
                        texto=agregacion.redactar_hallazgo(h),
                        clase="hallazgos",
                        dimension=dim,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falló la agregación likert de %r: %s", dim, exc)

    # (B.2) Interpretación por dimensión (mejora 2, §5.3, §16.2-§16.5, §16.7).
    hallazgos_likert = [
        h for h in hallazgos if h.tipo == "likert" and h.media is not None
    ]
    try:
        if hallazgos_likert:
            items_plano = [it for its in items_por_dim.values() for it in its]
            smin, smax = agregacion.escala_efectiva(items_plano)
            for h in hallazgos_likert:
                texto = agregacion.redactar_interpretacion_dimension(
                    h, hallazgos_likert, smin, smax
                )
                if texto:
                    chunks.append(
                        ChunkIndexable(
                            texto=texto, clase="hallazgos", dimension=h.dimension
                        )
                    )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falló la interpretación por dimensión: %s", exc)

    # (B.3) Grupos por desempeño (mejora 3, §6.4, §6.5, §16.6).
    try:
        if hallazgos_likert and respondents:
            items_plano = [it for its in items_por_dim.values() for it in its]
            _smin, _smax = agregacion.escala_efectiva(items_plano)
            grupos = agregacion.agrupar_por_desempeno(items_por_dim, respondents)
            for g in grupos:
                chunks.append(
                    ChunkIndexable(
                        texto=agregacion.redactar_grupo(g, _smax),
                        clase="grupo_desempeno",
                        dimension=g.grupo,
                    )
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falló la agrupación por desempeño: %s", exc)

    # Numérica / categórica / binaria: un chunk por pregunta agregable.
    for q in preguntas:
        tipo = _texto(q.get("type"))
        qid = _texto(q.get("question_id"))
        texto_q = _texto(q.get("text")) or qid
        if not qid:
            continue
        # Excluir columnas-artefacto de los datos sintéticos (perfil/profile_id):
        # no existen en datos reales y confundirían al LLM.
        if _es_columna_artefacto(texto_q, qid):
            continue
        try:
            if tipo == _TIPO_NUMERICO:
                h = agregacion.agregar_numerica(qid, texto_q, respondents)
            elif tipo in (_TIPO_CATEGORICO, _TIPO_BINARIO):
                clase_tipo = "binaria" if tipo == _TIPO_BINARIO else "categorica"
                h = agregacion.agregar_categorica(qid, texto_q, clase_tipo, respondents)
            else:
                continue
            if h is not None:
                hallazgos.append(h)
                chunks.append(
                    ChunkIndexable(
                        texto=agregacion.redactar_hallazgo(h),
                        clase="hallazgos",
                        dimension=h.dimension,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falló la agregación de %r (%s): %s", qid, tipo, exc)

    # Resumen global.
    try:
        resumen = agregacion.redactar_resumen_global(hallazgos, len(respondents), titulo)
        if resumen.strip():
            chunks.append(
                ChunkIndexable(texto=resumen, clase="hallazgos", dimension="")
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falló el resumen global: %s", exc)

    return chunks
