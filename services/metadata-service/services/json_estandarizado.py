"""JSON estandarizado del instrumento (lo que se ingiere al RAG).

Mantiene la forma del JSON v1 de la demo (`storage/raw/inst_XX.v1.json`) para
que los consumidores existentes lo lean sin cambios:
  - analysis-service lee `metadata.dublin_core["dc:*"]` y `metadata.survey_specific`
    (que aquí guarda los metadatos del tipo, sea encuesta, entrevista o prueba);
  - instrument-service lee `instrument.title/sections`, `design_reference.kpi_hints`
    y `metadata.survey_specific.palabras_clave`;
  - storage-service lo trocea por pregunta para Chroma.

Las respuestas individuales NO se incluyen (viven en el archivo crudo/limpio);
sí las estadísticas por reactivo, útiles para consultas cuantitativas en el RAG.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.analizador import Analisis, Pregunta

SCHEMA_VERSION = "2.0"


def _secciones(preguntas: list[Pregunta]) -> list[dict[str, Any]]:
    orden: list[str] = []
    por_seccion: dict[str, list[Pregunta]] = {}
    for p in preguntas:
        if p.seccion not in por_seccion:
            orden.append(p.seccion)
            por_seccion[p.seccion] = []
        por_seccion[p.seccion].append(p)
    return [
        {
            "section_id": f"s{i}",
            "name": nombre,
            "questions": [
                {"question_id": p.id, "text": p.texto, "type": p.tipo, "options": p.opciones}
                for p in por_seccion[nombre]
            ],
        }
        for i, nombre in enumerate(orden, start=1)
    ]


def _iso(fecha: datetime | None) -> str | None:
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.isoformat()


def construir(
    raw: Any,
    procesado: Any,
    dc: dict[str, Any],
    especificos: dict[str, Any],
    analisis: Analisis,
    *,
    aprobado_por: str | None,
    fecha_aprobado: datetime | None,
    kpis: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    objetivo = (
        especificos.get("objetivo")
        or especificos.get("objetivo_de_evaluacion")
        or analisis.hallazgos.get("objetivo")
        or ""
    )
    dimensiones = especificos.get("dimensiones") or analisis.dimensiones
    kpi_hints = list(analisis.kpi_hints)
    for k in kpis or []:
        if k.get("nombre_kpi") and k["nombre_kpi"] not in kpi_hints:
            kpi_hints.append(k["nombre_kpi"])

    estadisticas = {p.id: p.estadisticas for p in analisis.preguntas if p.estadisticas}
    data: dict[str, Any] = {
        "instrument_id": str(raw.id_crudo),
        "schema_version": SCHEMA_VERSION,
        "tipo_instrumento": raw.tipo_instrumento,
        "instrument": {
            "title": dc.get("dc_title") or analisis.titulo,
            "objective": objetivo,
            "dimensions_explored": list(dimensiones or []),
            "sections": _secciones(analisis.preguntas),
            "contenido": analisis.texto if analisis.familia == "documento" else "",
        },
        "metadata": {
            "tipo_instrumento": raw.tipo_instrumento,
            "dublin_core": {f"dc:{clave[3:]}": (valor or "") for clave, valor in dc.items()},
            "survey_specific": {clave: valor for clave, valor in especificos.items() if valor not in (None, "", [], {})},
        },
        "design_reference": {"kpi_hints": kpi_hints},
        "statistics": {
            "per_question": estadisticas,
            "global": {
                "n_registros": analisis.n_registros,
                "n_duplicados": analisis.n_duplicados,
                "pct_vacios": analisis.pct_vacios,
                "n_reactivos": len(analisis.preguntas),
            },
        },
        "approval": {
            "aprobado": fecha_aprobado is not None,
            "aprobado_por": aprobado_por,
            "fecha_aprobado": _iso(fecha_aprobado),
        },
        "source_files": {
            "respondido": raw.raw_archivo,
            "original": raw.raw_archivo_original,
            "limpio": getattr(procesado, "ruta_de_archivo_limpio", None),
            "nombre_archivo": raw.nombre_archivo,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if analisis.limpieza:
        # Trazabilidad: qué versión de la limpieza (cleaning-service) originó estos datos.
        data["cleaning"] = analisis.limpieza
        data["source_files"]["limpio"] = analisis.limpieza.get("archivo_limpio") or data["source_files"]["limpio"]
        # Fiabilidad calculada en la limpieza: alfa de Cronbach por bloque (encuestas) o KR-20 (pruebas).
        fiabilidad = (analisis.limpieza.get("estadistica") or {}).get("fiabilidad")
        if fiabilidad:
            data["statistics"]["reliability"] = fiabilidad
    if kpis is not None:
        data["inferred_kpis"] = kpis
    return data


def texto_instrumento(data: dict[str, Any]) -> str:
    """Versión Markdown del instrumento (solo preguntas, sin respuestas).

    Es la entrada «instrumento original» que el analysis-service usa para
    proponer KPIs por similitud semántica.
    """
    instrumento = data.get("instrument") or {}
    lineas = [f"# {instrumento.get('title') or 'Instrumento'}"]
    if instrumento.get("objective"):
        lineas += ["", str(instrumento["objective"])]
    for seccion in instrumento.get("sections") or []:
        lineas += ["", f"## {seccion.get('name') or 'Reactivos'}"]
        for n, pregunta in enumerate(seccion.get("questions") or [], start=1):
            lineas.append(f"{n}. {pregunta.get('text', '')}")
            for opcion in (pregunta.get("options") or [])[:15]:
                lineas.append(f"   - {opcion}")
    if instrumento.get("contenido"):
        lineas += ["", str(instrumento["contenido"])[:20000]]
    return "\n".join(lineas).strip()
