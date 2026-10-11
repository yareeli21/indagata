"""Estructura del .txt original + mapeo question_id -> dimensión (diseño §5, §8, §15.1).

Responsable de (a) localizar y leer el `.txt` original del instrumento, (b)
parsearlo en secciones/ítems redactados y el título legible, y (c) exponer el
mapeo `question_id -> (dimensión, texto_redactado)`.

El método primario de mapeo es POSICIONAL contra el `.txt` (§5.4 m1) con el
chequeo de consistencia monotónico OBLIGATORIO de §15.1; el fallback es por
prefijo normalizado del nombre de columna del JSON (§5.4 m2), reparando el
mojibake real (cp850 <-> utf-8; cp1252 como primer intento).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

# Límite blando de tamaño del .txt (2 MB) para no cargar binarios enormes (§8).
_LIMITE_BYTES = 2 * 1024 * 1024

_RE_TITULO = re.compile(r"^\s*INSTRUMENTO:\s*(.+?)\s*$")
_RE_SECCION = re.compile(r"^-{2,}\s*(.+?)\s*-{2,}$")
_RE_ITEM = re.compile(r"^\s*(\d+)\.\s+(.+)$")
_RE_SUFIJO_ITEM = re.compile(r"_item\d+$")
_RE_NUM_ITEM = re.compile(r"_item(\d+)$")


@dataclass(frozen=True)
class SeccionOriginal:
    titulo: str  # p.ej. "Organización Y Planificación" (title-case del header)
    items: list[str] = field(default_factory=list)  # textos redactados en orden


@dataclass(frozen=True)
class EstructuraOriginal:
    titulo_instrumento: str | None  # de la cabecera "INSTRUMENTO:" del .txt
    secciones: list[SeccionOriginal] = field(default_factory=list)


# ── Localización del .txt (§5.1, §5.1.1, §8) ────────────────────────────────
def ruta_original(instrumento_id: str) -> Path | None:
    """Resuelve la ruta al .txt original: vía BD (2 convenciones), luego disco.

    `id_crudo = int(str(instrumento_id).removeprefix("upload_"))`; acepta "1" y
    "upload_1". Si no parsea, se omite la BD y se va directo al fallback disco.
    """
    rel = _ruta_relativa_desde_bd(instrumento_id)
    if rel:
        candidatos = [
            settings.raw_path_abs.parent / rel,  # storage/ + "raw/..." (upload, primario)
            settings.PROJECT_ROOT / rel,  # PROJECT_ROOT + "storage/raw/..." (seed)
        ]
        ruta = next((c for c in candidatos if c.is_file()), None)
        if ruta is not None:
            return ruta

    return _fallback_por_nombre(instrumento_id)


def _ruta_relativa_desde_bd(instrumento_id: str) -> str | None:
    """Lee `raw_data.raw_archivo_original` por `id_crudo` reusando el patrón de
    `sources._resolver_desde_bd` (import diferido, degradar en silencio)."""
    try:
        id_crudo = int(str(instrumento_id).removeprefix("upload_"))
    except (TypeError, ValueError):
        return None
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from shared.models.raw_data import RawData
    except Exception as exc:  # pragma: no cover - sin BD/driver disponible
        logger.debug("BD no disponible para resolución del .txt: %s", exc)
        return None
    try:
        engine = create_engine(settings.DATABASE_URL)
        with Session(engine) as sesion:
            rel = sesion.scalar(
                select(RawData.raw_archivo_original).where(
                    RawData.id_crudo == id_crudo
                )
            )
    except Exception as exc:  # pragma: no cover - Postgres caído
        logger.debug("No se pudo consultar la BD para el .txt: %s", exc)
        return None
    return rel if isinstance(rel, str) and rel.strip() else None


def _fallback_por_nombre(instrumento_id: str) -> Path | None:
    """Fallback sin BD / NULL (§5.1.1): glob por nombre base en raw_path_abs.

    Deriva el nombre base del `instrument.title` del tipo "enc_01_respondido.csv"
    -> "enc_01" -> glob("*enc_01_original.txt"); el más reciente por mtime.
    """
    base = _nombre_base(instrumento_id)
    if not base:
        return None
    directorio = settings.raw_path_abs
    try:
        candidatos = [p for p in directorio.glob(f"*{base}_original.txt") if p.is_file()]
    except OSError:  # pragma: no cover - directorio inexistente
        return None
    if not candidatos:
        return None
    return max(candidatos, key=lambda p: p.stat().st_mtime)


def _nombre_base(instrumento_id: str) -> str:
    """Deriva "enc_01" de un id como "enc_01" o "enc_01_respondido.csv"."""
    cadena = str(instrumento_id).strip()
    if not cadena:
        return ""
    cadena = re.sub(r"\.[^.]+$", "", cadena)  # quitar extensión si la hay
    cadena = re.sub(r"_respondido$", "", cadena)
    return cadena


# ── Lectura del .txt (§8) ───────────────────────────────────────────────────
def leer_texto_original(instrumento_id: str) -> str | None:
    """Lee el .txt original en utf-8 ESTRICTO; `None` si falta/ilegible/vacío.

    Nunca usa `errors="replace"` (para no inyectar \\ufffd en prosa citable).
    """
    ruta = ruta_original(instrumento_id)
    if ruta is None:
        return None
    try:
        if ruta.stat().st_size > _LIMITE_BYTES:
            logger.warning("El .txt %s supera el límite de 2 MB; se omite.", ruta)
            return None
        texto = ruta.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        logger.warning("No se pudo leer el .txt original %s: %s", ruta, exc)
        return None
    return texto if texto.strip() else None


# ── Parseo (§5.3) ───────────────────────────────────────────────────────────
def parsear_estructura(texto: str) -> EstructuraOriginal:
    """Parsea título + secciones + ítems del .txt original (§5.3)."""
    titulo_instrumento: str | None = None
    secciones: list[SeccionOriginal] = []
    seccion_actual: SeccionOriginal | None = None

    for linea in (texto or "").splitlines():
        if titulo_instrumento is None:
            m_tit = _RE_TITULO.match(linea)
            if m_tit:
                titulo_instrumento = m_tit.group(1).strip()
                continue

        m_sec = _RE_SECCION.match(linea)
        if m_sec:
            seccion_actual = SeccionOriginal(titulo=m_sec.group(1).strip().title(), items=[])
            secciones.append(seccion_actual)
            continue

        m_item = _RE_ITEM.match(linea)
        if m_item and seccion_actual is not None:
            seccion_actual.items.append(m_item.group(2).strip())

    return EstructuraOriginal(titulo_instrumento=titulo_instrumento, secciones=secciones)


# ── Mapeo question_id -> dimensión (§5.4, §15.1) ────────────────────────────
def construir_mapa_dimension(
    estructura: EstructuraOriginal, questions_likert: list[dict]
) -> dict[str, tuple[str, str]]:
    """Mapea `question_id -> (dimensión, texto_redactado)`.

    Método primario POSICIONAL contra el `.txt` (§5.4 m1). INVARIANTE: asume que
    el orden de los ítems likert del JSON (q13..q33) coincide con el orden de
    lectura de los ítems del `.txt`. El método NO detecta reordenamientos del
    mismo tamaño salvo por el chequeo monotónico barato de §15.1.

    Devuelve `{}` (el llamador usa el fallback por prefijo) cuando:
      - el chequeo monotónico por grupo de prefijo falla (orden no monotónico), o
      - `len(plano) != len(questions_likert)` (conteo desigual), o
      - no hay `.txt` (`plano` vacío).
    Ambas condiciones (conteo y monotonicidad) deben cumplirse para posicional.
    """
    plano = [
        (sec.titulo, item)
        for sec in estructura.secciones
        for item in sec.items
    ]

    # Chequeo de consistencia barato (§15.1), O(n), no requiere el .txt.
    if not _secuencia_monotonica(questions_likert):
        logger.info("mapeo por prefijo (motivo=orden_no_monotonico)")
        logger.warning(
            "orden de items no monotonico; se usa agrupacion por prefijo"
        )
        return {}

    if not plano:
        logger.info("mapeo por prefijo (motivo=sin_txt)")
        return {}

    if len(plano) != len(questions_likert):
        logger.info("mapeo por prefijo (motivo=conteo_desigual)")
        return {}

    mapa: dict[str, tuple[str, str]] = {}
    for q, (titulo_dim, texto_item) in zip(questions_likert, plano):
        qid = str(q.get("question_id", "")) if isinstance(q, dict) else ""
        if qid:
            mapa[qid] = (titulo_dim, texto_item)
    logger.info("mapeo posicional (len=%d)", len(mapa))
    return mapa


def _secuencia_monotonica(questions_likert: list[dict]) -> bool:
    """Chequeo monotónico de §15.1 por grupo de prefijo de aparición contigua.

    Agrupa por prefijo normalizado (hasta `_item`) preservando el orden de
    aparición; dentro de cada grupo contiguo, los números `_item\\d+` deben ser
    1..k crecientes. La colisión `Habilidades_par` (dos grupos 1..3) se valida
    por grupo contiguo, no por prefijo global.
    """
    grupos: list[list[int]] = []
    prefijo_actual: str | None = None
    for q in questions_likert:
        nombre = str(q.get("text", "")) if isinstance(q, dict) else ""
        prefijo = _RE_SUFIJO_ITEM.sub("", nombre)
        m = _RE_NUM_ITEM.search(nombre)
        if m is None:
            # Sin sufijo _itemN no se puede validar: tratarlo como su propio grupo.
            grupos.append([])
            prefijo_actual = None
            continue
        numero = int(m.group(1))
        if prefijo != prefijo_actual:
            grupos.append([numero])
            prefijo_actual = prefijo
        else:
            grupos[-1].append(numero)

    for secuencia in grupos:
        if not secuencia:
            continue
        esperado = list(range(1, len(secuencia) + 1))
        if secuencia != esperado:
            return False
    return True


# ── Fallback por prefijo con reparación de mojibake (§5.4 m2, §4.3, §14-F10) ──
def mapa_por_prefijo(questions_likert: list[dict]) -> dict[str, tuple[str, str]]:
    """Fallback degradado: agrupa por prefijo reparado del nombre de columna.

    Etiqueta de dimensión = "Dimensión <Prefijo Reparado> (agrupación aproximada)";
    etiqueta por ítem = "<prefijo> ítem <n>". Emite WARNING cuando dos
    question_id caen en el mismo prefijo colisionado.
    """
    mapa: dict[str, tuple[str, str]] = {}
    vistos: dict[str, set[str]] = {}
    for q in questions_likert:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id", ""))
        if not qid:
            continue
        nombre = str(q.get("text", ""))
        prefijo = _reparar_mojibake(_RE_SUFIJO_ITEM.sub("", nombre))
        m = _RE_NUM_ITEM.search(nombre)
        numero = m.group(1) if m else "?"

        clave = prefijo.lower()
        vistos.setdefault(clave, set()).add(qid)

        etiqueta_dim = f"Dimensión {prefijo} (agrupación aproximada)"
        etiqueta_item = f"{prefijo} ítem {numero}"
        mapa[qid] = (etiqueta_dim, etiqueta_item)

    for clave, qids in vistos.items():
        if len(qids) > 1:
            logger.warning(
                "colisión de prefijo truncado: la dimensión %r fusiona ítems de "
                "secciones distintas (%s)",
                clave,
                ", ".join(sorted(qids)),
            )
    return mapa


def _reparar_mojibake(nombre: str) -> str:
    """Repara mojibake de nombres de columna del JSON (§5.4 m2, §14-F10).

    Intenta cp1252->utf-8 y, si lanza UnicodeError, cp850->utf-8; si ambas
    fallan deja el original normalizado (NFKD). El mojibake real es cp850<->utf-8
    (cp1252 lanza UnicodeEncodeError sobre glifos como "├│").
    """
    for enc in ("cp1252", "cp850"):
        try:
            return nombre.encode(enc).decode("utf-8")
        except UnicodeError:
            continue
    return unicodedata.normalize("NFKD", nombre)
