# api/services/carga_artifacts.py
"""
Generación de ARTEFACTOS de carga a partir de las decisiones aprobadas.

Extraído de services_carga.py para separar responsabilidades. Aquí vive la
producción de archivos/datos derivados:
  - _generar_dataset_limpio: aplica las transformaciones aceptadas -> CSV limpio.
  - _generar_sav: genera el .SAV (SPSS) con su diccionario.
  - _materializar_enriquecimiento: crea MetadatosEnriquecidos + KpiInferido aceptados.
  - _generar_json_consolidado: arma el JSON consolidado (insumo del RAG) + envoltorio común.
  - _mapear_knowledge_entrevista / _envoltorio_entrevista / _añadir_envoltorio_comun.

Los bloques del SIS se consumen por su superficie pública (survey_intelligence.host_toolkit),
con imports diferidos dentro de cada función para no acoplar el import-time del host.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.models_instrumentos import (
    EtlPropuesta,
    InstrumentoProcesado,
    KPI,
    KpiInferido,
    MetadatosEnriquecidos,
)
from api.services.carga_sis_mapping import (
    _load_interview_analysis,
    _load_respondent_profiles,
    _load_results_findings,
)
from api.services.services_compartidos import ArchivoService

logger = logging.getLogger(__name__)


def _generar_dataset_limpio(db: Session, instrumento: InstrumentoProcesado) -> str | None:
    """
    Aplica las transformaciones de limpieza ACEPTADAS sobre los datos de la encuesta
    y escribe un CSV limpio en storage/clean/{id}_clean.csv (reversible, inspeccionable).

    Solo aplica a encuestas (datos tabulares). Devuelve la ruta relativa o None.

    Usa el apply_engine del SIS (bloque de Lego) sin acoplar la lógica de transforms.
    """
    if instrumento.tipo_instrumento != "encuesta" or not instrumento.ruta_archivo:
        return None

    import csv
    import io

    from survey_intelligence.host_toolkit import (
        TransformDecision,
        apply_decisions,
        normalize_name,
        read_csv,
        read_xlsx,
        unique_names,
    )

    # Reconstruir el RawTable desde el archivo original.
    ruta_abs = ArchivoService.ruta_absoluta(instrumento.ruta_archivo)
    ext = ruta_abs.suffix.lower()
    data = ruta_abs.read_bytes()
    raw = read_xlsx(data) if ext in {".xlsx", ".xls"} else read_csv(data)

    # Nombres normalizados por posición (mismo criterio que el Canonical builder).
    names = unique_names([normalize_name(h) for h in raw.headers])

    # Recolectar las transformaciones ACEPTADAS de tipo 'transformacion'.
    aceptadas = (
        db.query(EtlPropuesta)
        .filter(
            EtlPropuesta.instrumento_id == instrumento.instrumento_id,
            EtlPropuesta.tipo == "transformacion",
            EtlPropuesta.estado_decision == "aceptada",
        )
        .all()
    )
    decisiones: list[TransformDecision] = []
    for p in aceptadas:
        try:
            payload = json.loads(p.valor_propuesto or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        tid = payload.get("transform_id")
        if not tid:
            continue
        params = {k: v for k, v in payload.items() if k != "transform_id"}
        decisiones.append(TransformDecision(transform_id=tid, params=params, proposal_id=str(p.propuesta_id)))

    if not decisiones:
        return None  # nada aceptado que aplicar

    result = apply_decisions(raw, names, decisiones)
    clean = result.raw_table

    # Escribir el CSV limpio.
    clean_dir = settings.clean_path_abs
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_path = clean_dir / f"{instrumento.instrumento_id}_clean.csv"

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(clean.headers)
    writer.writerows(clean.rows)
    clean_path.write_text(buffer.getvalue(), encoding="utf-8")

    logging.info(
        f"Dataset limpio generado: {clean_path.name} "
        f"({clean.n_columns} columnas, {clean.n_rows} filas)"
    )
    return str(clean_path.relative_to(settings.PROJECT_ROOT))


def _generar_sav(instrumento: InstrumentoProcesado) -> str | None:
    """
    Genera el archivo .SAV (IBM SPSS) para ENCUESTAS, con etiquetas de variable,
    etiquetas de valor y niveles de medición del diccionario SPSS del SIS.

    Usa el dataset limpio (storage/clean) si existe; si no, el archivo original.
    Devuelve la ruta relativa del .SAV o None.
    """
    if instrumento.tipo_instrumento != "encuesta" or not instrumento.ruta_archivo:
        return None

    from survey_intelligence.host_toolkit import (
        IngestionResult,
        SavWriteError,
        build_canonical,
        build_spss_dictionary,
        detect_platform,
        profile,
        read_csv,
        read_xlsx,
        write_sav,
    )

    # Preferir el dataset limpio (storage/clean); si no, el original.
    clean_path = settings.clean_path_abs / f"{instrumento.instrumento_id}_clean.csv"
    if clean_path.exists():
        data = clean_path.read_bytes()
        raw = read_csv(data)
    else:
        ruta_abs = ArchivoService.ruta_absoluta(instrumento.ruta_archivo)
        ext = ruta_abs.suffix.lower()
        data = ruta_abs.read_bytes()
        raw = read_xlsx(data) if ext in {".xlsx", ".xls"} else read_csv(data)

    # Reconstruir Canonical + diccionario SPSS (determinístico).
    platform = detect_platform(raw.headers)
    ingestion = IngestionResult(raw_table=raw, platform=platform)
    canonical = profile(
        build_canonical(ingestion, instrumento.nombre, None), raw
    )
    spss_by_id = {s.variable_id: s for s in build_spss_dictionary(canonical)}
    names = [v.normalized_name for v in canonical.variables]
    vids = [v.variable_id for v in canonical.variables]

    sav_dir = settings.sav_path_abs
    sav_dir.mkdir(parents=True, exist_ok=True)
    sav_path = sav_dir / f"{instrumento.instrumento_id}.sav"

    try:
        write_sav(sav_path, raw, names, spss_by_id, vids)
    except SavWriteError as e:
        logging.error(f"No se pudo generar .SAV para instrumento {instrumento.instrumento_id}: {e}")
        return None

    logging.info(f".SAV generado: {sav_path.name}")
    return str(sav_path.relative_to(settings.PROJECT_ROOT))


def _materializar_enriquecimiento(db: Session, instrumento: InstrumentoProcesado) -> None:
    """
    Crea MetadatosEnriquecidos (dict JSONB) y KpiInferido a partir de las propuestas
    de enriquecimiento ACEPTADAS.
    """
    aceptadas = (
        db.query(EtlPropuesta)
        .filter(
            EtlPropuesta.instrumento_id == instrumento.instrumento_id,
            EtlPropuesta.estado_decision == "aceptada",
            EtlPropuesta.tipo.in_({"metadato_enriquecido", "kpi_sugerido"}),
        )
        .all()
    )

    metadatos_dict: dict[str, Any] = {}
    for propuesta in aceptadas:
        if propuesta.tipo == "metadato_enriquecido":
            try:
                campo = json.loads(propuesta.valor_propuesto or "{}")
            except (json.JSONDecodeError, TypeError):
                campo = {}
            vid = campo.get("variable_id", f"meta_{propuesta.propuesta_id}")
            metadatos_dict[vid] = campo
        elif propuesta.tipo == "kpi_sugerido":
            try:
                kpi_data = json.loads(propuesta.valor_propuesto or "{}")
            except (json.JSONDecodeError, TypeError):
                kpi_data = {}
            if kpi_data.get("kpi_id"):
                db.add(KpiInferido(
                    instrumento_id=instrumento.instrumento_id,
                    kpi_id=kpi_data["kpi_id"],
                    tipo_relacion=kpi_data.get("tipo_relacion", "inferido"),
                    evidencia_textual=propuesta.justificacion,
                    score_inferencia=kpi_data.get("score_inferencia", 0.7),
                    origen="propuesta_etl",
                ))

    if metadatos_dict:
        existente = db.query(MetadatosEnriquecidos).filter(
            MetadatosEnriquecidos.instrumento_id == instrumento.instrumento_id
        ).first()
        if existente is None:
            db.add(MetadatosEnriquecidos(
                instrumento_id=instrumento.instrumento_id,
                metadatos=metadatos_dict,
            ))
        else:
            merged = dict(existente.metadatos or {})
            merged.update(metadatos_dict)
            existente.metadatos = merged
            db.add(existente)
    db.flush()


def _generar_json_consolidado(
    db: Session,
    instrumento: InstrumentoProcesado,
) -> Path:
    """
    Genera el JSON consolidado con todos los datos del instrumento y lo guarda en storage/json/.

    Returns:
        Path: Ruta absoluta del archivo JSON generado.

    PROPÓSITO: este JSON es el insumo para los CHUNKS del RAG futuro, por lo que es
    PURAMENTE SEMÁNTICO. NO contiene métricas, técnicas de limpieza, texto crudo,
    estados ni fechas de proceso (eso vive en el Canonical y en la BD, no aquí).
    """
    from survey_intelligence import SCHEMA_VERSION

    json_data: dict[str, Any] = {
        "instrumento_id": instrumento.instrumento_id,
        "titulo": instrumento.nombre,
        "tipo_instrumento": instrumento.tipo_instrumento,
        "schema_version": SCHEMA_VERSION,
        "generado_en": datetime.now(timezone.utc).isoformat(),
    }

    # ── Metadatos Dublin Core (contexto del instrumento; sí es semántico) ──────
    if instrumento.metadatos_dc:
        dc = instrumento.metadatos_dc
        dc_date_str = dc.dc_date if isinstance(dc.dc_date, str) else (
            dc.dc_date.isoformat() if dc.dc_date else None
        )
        json_data["metadata_dc"] = {
            "dc_title": dc.dc_title,
            "dc_creator": dc.dc_creator,
            "dc_subject": json.loads(dc.dc_subject) if dc.dc_subject else [],
            "dc_description": dc.dc_description,
            "dc_publisher": dc.dc_publisher,
            "dc_date": dc_date_str,
            "dc_type": dc.dc_type,
            "dc_format": dc.dc_format,
            "dc_language": dc.dc_language,
            "dc_coverage": dc.dc_coverage,
            "dc_rights": dc.dc_rights,
            "dc_source": dc.dc_source,
            "dc_relation": dc.dc_relation,
        }
    else:
        json_data["metadata_dc"] = None

    # ── Unidades semánticas: una por metadato enriquecido aceptado -> chunk ────
    # metadatos_enriquecidos guarda {variable_id: {construct, semantic_role, tags,
    # analytical_sufficiency, ...}}. Cada entrada es una unidad semántica embebible.
    unidades: list[dict[str, Any]] = []
    proposito_inferido: str | None = None
    if instrumento.metadatos_enriquecidos and instrumento.metadatos_enriquecidos.metadatos:
        for vid, campo in instrumento.metadatos_enriquecidos.metadatos.items():
            if not isinstance(campo, dict):
                continue
            constructo = campo.get("construct") or campo.get("constructo")
            unidades.append({
                "variable_id": campo.get("variable_id", vid),
                "constructo": constructo,
                "rol_semantico": campo.get("semantic_role"),
                "tags": campo.get("tags", []),
                "suficiencia": campo.get("analytical_sufficiency"),
                # texto embebible: el constructo es lo que da sentido al chunk.
                "texto": constructo or vid,
            })
    json_data["resumen"] = {"proposito_inferido": proposito_inferido}
    json_data["unidades_semanticas"] = unidades

    # ── KPIs inferidos (semántico: qué mide el instrumento) ────────────────────
    kpis_list = []
    for kpi_inferido in instrumento.kpis_inferidos:
        kpi_row = db.query(KPI).filter(KPI.kpi_id == kpi_inferido.kpi_id).first()
        kpis_list.append({
            "kpi_id": kpi_inferido.kpi_id,
            "nombre": kpi_row.nombrekpi if kpi_row else f"KPI {kpi_inferido.kpi_id}",
            "tipo_relacion": kpi_inferido.tipo_relacion,
            "score_inferencia": float(kpi_inferido.score_inferencia) if kpi_inferido.score_inferencia else None,
            "evidencia_textual": kpi_inferido.evidencia_textual,
        })
    json_data["kpis"] = kpis_list

    # ── Hallazgos analíticos (S8b): qué respondió la población y qué significa ──
    # En v2 esta sección NO se emite: es idéntica a `por_pregunta` (evita duplicar datos).
    hallazgos = _load_results_findings(instrumento.instrumento_id)

    # ── Perspectivas v2 (encuestas reagrupadas por pregunta) ────────────────────
    # Si hay perfiles de respondente cacheados, el análisis fue v2: se exponen las
    # dos perspectivas del diseño. Si no (v1), se emite hallazgos_analiticos (compat).
    perfiles = _load_respondent_profiles(instrumento.instrumento_id)
    es_v2 = perfiles is not None
    if es_v2:
        # por_pregunta: los hallazgos v2 ya vienen por pregunta (question_id en variable_id).
        # Es la ÚNICA sección por-pregunta en v2 (reemplaza a hallazgos_analiticos).
        json_data["por_pregunta"] = [
            {
                "question_id": h.get("variable_id"),
                "pregunta": h.get("pregunta"),
                "tipo": h.get("tipo"),
                "metricas": h.get("metrics"),
                "distribucion": h.get("distribution"),
                "interpretacion": h.get("interpretation"),
                "patrones": h.get("insights", []),
                "evidencia_numerica": h.get("numeric_evidence"),
                "texto_semantico": h.get("semantic_text"),
            }
            for h in hallazgos if isinstance(h, dict)
        ]
        # por_respondente: perfiles deterministas (sin LLM) ya cacheados.
        json_data["por_respondente"] = perfiles
    else:
        # v1 (compatibilidad): se conserva el campo histórico.
        json_data["hallazgos_analiticos"] = hallazgos

    # ── Conocimiento de ENTREVISTA (si aplica) ─────────────────────────────────
    # Para instrumentos 'entrevista', el SIS produjo un InterviewAnalysis (cacheado
    # en analyze). Se expone como knowledge de entrevista, sin afectar a encuestas.
    interview = _load_interview_analysis(instrumento.instrumento_id)
    if interview is not None:
        json_data["knowledge_entrevista"] = _mapear_knowledge_entrevista(interview)

    # ── Envoltorio común (aditivo, compatible hacia atrás) ─────────────────────
    _añadir_envoltorio_comun(
        json_data, unidades, kpis_list, hallazgos, proposito_inferido, interview
    )
    # En v2, las unidades de chunking del RAG son las nuevas perspectivas.
    if es_v2:
        json_data["rag_hints"] = {
            "chunk_units": ["por_pregunta[]", "por_respondente[]"],
            "embeddable_fields": ["texto_semantico", "interpretacion", "resumen"],
            "indexable_metadata": ["instrument_type", "question_id", "tipo", "respondent_id"],
        }
        # traceability en encuestas v2 solo repite ids que ya están en por_pregunta/kpis.
        # Se omite para evitar ruido y reducir el tamaño del JSON.
        json_data.pop("traceability", None)

    # NOTA: intencionalmente NO se incluyen 'transformaciones_aceptadas', 'texto_extraido',
    # 'estado', ni fechas de proceso: son administrativos, no insumo del RAG.

    # Guardar JSON en storage/json/
    json_dir = settings.PROJECT_ROOT / "storage" / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    json_path = json_dir / f"{instrumento.instrumento_id}.json"
    json_path.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logging.info(f"JSON consolidado (semántico) generado: {json_path}")
    return json_path


def _mapear_knowledge_entrevista(interview: dict[str, Any]) -> dict[str, Any]:
    """
    Mapea el InterviewAnalysis cacheado (dict) al bloque `knowledge` de entrevista
    del consolidado, según el diseño (participantes, turnos, temas, hallazgos,
    patrones, citas, resúmenes). No inventa: reusa lo que el SIS produjo.
    """
    return {
        "participantes": interview.get("participants", []),
        "n_personas": interview.get("n_personas", 0),
        "turnos": interview.get("turns", []),
        "temas": interview.get("themes", []),
        "hallazgos": interview.get("findings", []),
        "patrones": interview.get("patterns", []),
        "citas_relevantes": interview.get("quotes", []),
        "resumen_por_participante": interview.get("participant_summaries", []),
        "resumen_general": interview.get("general_summary"),
    }


def _envoltorio_entrevista(json_data: dict[str, Any], interview: dict[str, Any]) -> None:
    """
    Construye summary_humano / traceability / rag_hints para ENTREVISTAS a partir
    del InterviewAnalysis (participantes, turnos, temas, hallazgos, patrones, citas).
    """
    participantes = interview.get("participants", []) or []
    turnos = interview.get("turns", []) or []
    temas = interview.get("themes", []) or []
    hallazgos_e = interview.get("findings", []) or []
    patrones_e = interview.get("patterns", []) or []
    citas = interview.get("quotes", []) or []
    n_personas = interview.get("n_personas", len(participantes))

    json_data["summary_humano"] = {
        "que_se_analizo": (
            f"Entrevista con {n_personas} participante(s) y {len(turnos)} turnos de diálogo."
        ),
        "que_se_encontro": interview.get("general_summary") or (
            f"{len(temas)} temas, {len(hallazgos_e)} hallazgos, {len(patrones_e)} patrones."
        ),
        "patrones": [str(p.get("descripcion", "")) for p in patrones_e if isinstance(p, dict)][:10],
        "evidencia_destacada": [str(c.get("text", "")) for c in citas if isinstance(c, dict)][:10],
    }

    # Trazabilidad: temas, hallazgos y citas apuntan a turnos/participantes.
    unidades_traza: list[dict[str, Any]] = []
    for t in temas:
        if isinstance(t, dict):
            unidades_traza.append({
                "unidad_id": t.get("theme_id"),
                "tipo": "tema",
                "refs": {"turn_ids": t.get("turn_ids", []), "participant_ids": t.get("participant_ids", [])},
            })
    for h in hallazgos_e:
        if isinstance(h, dict):
            unidades_traza.append({
                "unidad_id": h.get("finding_id"),
                "tipo": "hallazgo",
                "refs": {"turn_ids": h.get("evidence_turn_ids", []), "participant_ids": h.get("participant_ids", [])},
            })
    for c in citas:
        if isinstance(c, dict):
            unidades_traza.append({
                "unidad_id": c.get("quote_id"),
                "tipo": "cita",
                "refs": {"turno_id": c.get("turn_id"), "participante_id": c.get("speaker_id")},
            })
    json_data["traceability"] = {"unidades": unidades_traza}

    json_data["rag_hints"] = {
        "chunk_units": [
            "knowledge_entrevista.hallazgos[]",
            "knowledge_entrevista.temas[]",
            "knowledge_entrevista.citas_relevantes[]",
        ],
        "embeddable_fields": ["enunciado", "descripcion", "text", "resumen"],
        "indexable_metadata": ["instrument_type", "theme_id", "participante_id"],
    }


def _añadir_envoltorio_comun(
    json_data: dict[str, Any],
    unidades: list[dict[str, Any]],
    kpis_list: list[dict[str, Any]],
    hallazgos: list[dict[str, Any]],
    proposito_inferido: str | None,
    interview: dict[str, Any] | None = None,
) -> None:
    """
    Enriquece `json_data` (in place) con el envoltorio común aditivo para el RAG.

    Todos los campos son NUEVOS y OPCIONALES: no modifican ni eliminan las claves
    ya existentes del consolidado, por lo que es compatible hacia atrás. Se derivan
    de datos ya calculados (unidades semánticas, KPIs, hallazgos), sin LLM adicional.

    Añade:
      - instrument_type: espejo de tipo_instrumento (consumo uniforme del RAG).
      - summary_humano: resumen legible (qué se analizó / encontró / patrones / evidencia).
      - traceability: unidades trazables a su fuente (variable / kpi / hallazgo).
      - rag_hints: unidades de chunking y campos embebibles/indexables sugeridos.
    """
    json_data["instrument_type"] = json_data.get("tipo_instrumento")

    # Rama ENTREVISTA: el envoltorio se deriva del conocimiento de entrevista.
    if interview is not None:
        _envoltorio_entrevista(json_data, interview)
        return

    n_unidades = len(unidades)
    n_kpis = len(kpis_list)
    n_hallazgos = len(hallazgos)

    patrones: list[str] = []
    evidencia_destacada: list[str] = []
    for h in hallazgos:
        if not isinstance(h, dict):
            continue
        inss = h.get("insights") or []
        if isinstance(inss, list):
            patrones.extend(str(i) for i in inss[:1])  # 1 insight por hallazgo, como patrón
        ev = h.get("numeric_evidence") or h.get("semantic_text")
        if ev:
            evidencia_destacada.append(str(ev))

    json_data["summary_humano"] = {
        "que_se_analizo": (
            proposito_inferido
            or f"Instrumento tipo '{json_data.get('tipo_instrumento')}' "
            f"con {n_unidades} unidades semánticas."
        ),
        "que_se_encontro": (
            f"{n_hallazgos} hallazgos analíticos, {n_kpis} KPIs inferidos, "
            f"{n_unidades} variables enriquecidas."
        ),
        "patrones": patrones[:10],
        "evidencia_destacada": evidencia_destacada[:10],
    }

    # Trazabilidad: cada unidad/hallazgo/kpi apunta a su fuente.
    unidades_trazables: list[dict[str, Any]] = []
    for u in unidades:
        unidades_trazables.append({
            "unidad_id": u.get("variable_id"),
            "tipo": "variable",
            "refs": {"variable_id": u.get("variable_id")},
        })
    for h in hallazgos:
        if isinstance(h, dict) and h.get("variable_id"):
            unidades_trazables.append({
                "unidad_id": f"hallazgo_{h.get('variable_id')}",
                "tipo": "hallazgo",
                "refs": {"variable_id": h.get("variable_id")},
            })
    for k in kpis_list:
        unidades_trazables.append({
            "unidad_id": f"kpi_{k.get('kpi_id')}",
            "tipo": "kpi",
            "refs": {"kpi_id": k.get("kpi_id")},
        })
    json_data["traceability"] = {"unidades": unidades_trazables}

    json_data["rag_hints"] = {
        "chunk_units": ["hallazgos_analiticos[]", "unidades_semanticas[]", "kpis[]"],
        "embeddable_fields": ["texto", "semantic_text", "interpretation", "constructo"],
        "indexable_metadata": ["instrument_type", "variable_id", "kpi_id"],
    }
