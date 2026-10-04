"""Helper único DB + JSON -> InstrumentoDTO (diseño §2.3/§2.4/§2.5).

`mapear_instrumento(raw, procesado, instrumento_json)` combina las columnas
reales de `raw_data` / `instrumento_procesado` con el JSON del instrumento
(esquema real `storage/raw/inst_XX.v1.json`, §2.3) aplicando **lectura
defensiva**: cualquier clave ausente o de tipo inesperado cae a su default sin
abortar, de modo que `GET /instrumentos` SIEMPRE devuelve un DTO válido.

Lo reutilizan los routers de listado/consulta (§6) y, conceptualmente, el
servicio RAG (`sources.py`, §4.2). `extraer_kpis(json)` se exporta aparte para
el catálogo de KPIs.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.schemas.instrumentos import (
    EstadoInstrumentoDTO,
    InstrumentoDTO,
    NivelEducativoDTO,
    TipoInstrumentoDTO,
)

logger = logging.getLogger(__name__)

# ── Mapeos canónicos (diseño §2.4 / §2.5) ────────────────────────────────────
_TIPO_MAP: dict[str, TipoInstrumentoDTO] = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_TIPO_DEFAULT: TipoInstrumentoDTO = "Encuesta"

_ESTADO_MAP: dict[str, EstadoInstrumentoDTO] = {
    "recibido": "Borrador",
    "limpieza_en_proceso": "Borrador",
    "limpio": "Borrador",
    "metadatos_registrados": "En revisión",
    "estandarizado": "Estandarizado",
    "vectorizado": "Estandarizado",
    "error": "Borrador",
}
_ESTADO_DEFAULT: EstadoInstrumentoDTO = "Borrador"

# Substrings que, presentes en los textos de cobertura/población, elevan el
# nivel a "Posgrado" (§2.3a). Default: "Licenciatura".
_NIVEL_POSGRADO = ("posgrado", "maestr", "doctor", "especialidad")


def _como_dict(valor: Any) -> dict[str, Any]:
    """Devuelve `valor` si es dict, si no `{}` (lectura defensiva)."""
    return valor if isinstance(valor, dict) else {}


def _como_lista(valor: Any) -> list[Any]:
    """Devuelve `valor` si es lista, si no `[]` (lectura defensiva)."""
    return valor if isinstance(valor, list) else []


def _texto(valor: Any) -> str:
    """Normaliza a str recortado; `None`/no-str -> ''."""
    return valor.strip() if isinstance(valor, str) else ""


def mapear_tipo(tipo_instrumento_raw: str | None) -> TipoInstrumentoDTO:
    """Mapea `raw_data.tipo_instrumento` al literal del frontend (§2.4)."""
    clave = (tipo_instrumento_raw or "").strip().lower()
    tipo = _TIPO_MAP.get(clave)
    if tipo is None:
        logger.warning(
            "tipo_instrumento desconocido %r; se mapea a %r.",
            tipo_instrumento_raw,
            _TIPO_DEFAULT,
        )
        return _TIPO_DEFAULT
    return tipo


def mapear_estado(estado_raw: str | None) -> EstadoInstrumentoDTO:
    """Mapea `instrumento_procesado.estado` al literal del frontend (§2.5)."""
    return _ESTADO_MAP.get((estado_raw or "").strip().lower(), _ESTADO_DEFAULT)


def _derivar_nivel(instrumento_json: dict[str, Any] | None) -> NivelEducativoDTO:
    """Heurística de nivel por substring sobre cobertura/población (§2.3a)."""
    json = _como_dict(instrumento_json)
    metadata = _como_dict(json.get("metadata"))
    dublin_core = _como_dict(metadata.get("dublin_core"))
    survey = _como_dict(metadata.get("survey_specific"))

    textos = " ".join(
        (
            _texto(dublin_core.get("dc:coverage")),
            _texto(survey.get("poblacion_objetivo")),
        )
    ).lower()

    if any(clave in textos for clave in _NIVEL_POSGRADO):
        logger.debug("nivel=Posgrado por heurística sobre %r", textos)
        return "Posgrado"
    return "Licenciatura"


def extraer_kpis(instrumento_json: dict[str, Any] | None) -> list[str]:
    """KPIs del instrumento = `design_reference.kpi_hints` (lista de str)."""
    json = _como_dict(instrumento_json)
    design = _como_dict(json.get("design_reference"))
    return [str(k) for k in _como_lista(design.get("kpi_hints")) if _texto(k)]


def _extraer_titulo(
    instrumento: dict[str, Any],
    dublin_core: dict[str, Any],
    nombre_archivo: str,
) -> str:
    """instrument.title -> dc:title -> nombre_archivo (§2.3)."""
    return (
        _texto(instrumento.get("title"))
        or _texto(dublin_core.get("dc:title"))
        or nombre_archivo
    )


def _extraer_anio(dublin_core: dict[str, Any], fecha_carga: datetime | None) -> int:
    """Año de dc:date -> año de fecha_carga -> año actual (§2.3)."""
    dc_date = _texto(dublin_core.get("dc:date"))
    if dc_date:
        try:
            return date.fromisoformat(dc_date[:10]).year
        except ValueError:
            logger.debug("dc:date no parseable: %r", dc_date)
    if isinstance(fecha_carga, datetime):
        return fecha_carga.year
    return date.today().year


def _extraer_reactivos(instrumento: dict[str, Any]) -> int:
    """Σ len(section['questions']) sobre instrument.sections (§2.3)."""
    total = 0
    for seccion in _como_lista(instrumento.get("sections")):
        total += len(_como_lista(_como_dict(seccion).get("questions")))
    return total


def _extraer_descripcion(
    instrumento: dict[str, Any], dublin_core: dict[str, Any]
) -> str:
    """dc:description -> instrument.objective (§2.3)."""
    return _texto(dublin_core.get("dc:description")) or _texto(
        instrumento.get("objective")
    )


def _extraer_etiquetas(
    survey: dict[str, Any], dublin_core: dict[str, Any]
) -> list[str]:
    """survey_specific.palabras_clave -> dc:subject split por ',' (§2.3)."""
    palabras = [str(p).strip() for p in _como_lista(survey.get("palabras_clave"))]
    palabras = [p for p in palabras if p]
    if palabras:
        return palabras
    subject = _texto(dublin_core.get("dc:subject"))
    if subject:
        return [parte.strip() for parte in subject.split(",") if parte.strip()]
    return []


def mapear_instrumento(
    raw: Any,
    procesado: Any,
    instrumento_json: dict[str, Any] | None,
) -> InstrumentoDTO:
    """Combina DB + JSON en un `InstrumentoDTO` con defaults de degradación.

    Args:
        raw:              fila `RawData` (o namespace con los mismos atributos).
        procesado:        fila `InstrumentoProcesado` o None.
        instrumento_json: dict del JSON del instrumento (§2.3) o None.

    Returns:
        InstrumentoDTO siempre válido (nunca aborta por datos faltantes).
    """
    json = _como_dict(instrumento_json)
    instrumento = _como_dict(json.get("instrument"))
    metadata = _como_dict(json.get("metadata"))
    dublin_core = _como_dict(metadata.get("dublin_core"))
    survey = _como_dict(metadata.get("survey_specific"))

    nombre_archivo = _texto(getattr(raw, "nombre_archivo", "")) or "instrumento"
    fecha_carga = getattr(raw, "fecha_carga", None)
    id_owner = getattr(raw, "id_owner", None)

    estado_raw = getattr(procesado, "estado", None) if procesado is not None else None
    id_instrumento = (
        getattr(procesado, "id_instrumento", None) if procesado is not None else None
    )

    fecha_iso = (
        fecha_carga.date().isoformat()
        if isinstance(fecha_carga, datetime)
        else date.today().isoformat()
    )

    return InstrumentoDTO(
        id=str(getattr(raw, "id_crudo", "")),
        titulo=_extraer_titulo(instrumento, dublin_core, nombre_archivo),
        tipo=mapear_tipo(getattr(raw, "tipo_instrumento", None)),
        nivel=_derivar_nivel(json),
        autorId=str(id_owner) if id_owner is not None else "",
        anio=_extraer_anio(dublin_core, fecha_carga),
        fecha=fecha_iso,
        kpis=extraer_kpis(json),
        reactivos=_extraer_reactivos(instrumento),
        estado=mapear_estado(estado_raw),
        descripcion=_extraer_descripcion(instrumento, dublin_core),
        etiquetas=_extraer_etiquetas(survey, dublin_core),
        idProcesado=str(id_instrumento) if id_instrumento is not None else None,
    )
