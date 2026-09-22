# api/services/carga_sis_mapping.py
"""
Mapeo del resultado del SIS al dominio del host + caché e idempotencia.

Extraído de services_carga.py para separar responsabilidades: aquí vive la
traducción SurveyIntelligenceResult -> filas de BD (EtlPropuesta, KpiInferido,
ImprovementOpportunity), el cacheo en disco de artefactos intermedios (Canonical,
hallazgos analíticos, análisis de entrevista) y la aplicación de decisiones de
aprobación. No define endpoints ni orquesta el wizard (eso vive en los servicios).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.models_instrumentos import (
    EtlPropuesta,
    ImprovementOpportunity,
    InstrumentoProcesado,
    KPI,
    KpiInferido,
    MetadatosEnriquecidos,
)
from api.schemas.schemas_carga import AprobacionRequest

logger = logging.getLogger(__name__)


def _sis_serializar(valor: Any) -> str | None:
    """Serializa dict/list a JSON string; deja str/None intactos."""
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def _borrar_analisis_previo(db: Session, instrumento_id: int) -> None:
    """
    Borra propuestas, KPIs inferidos, metadatos enriquecidos y oportunidades de mejora
    de un análisis anterior. Hace el reanálisis idempotente (no duplica propuestas).
    """
    db.query(EtlPropuesta).filter(
        EtlPropuesta.instrumento_id == instrumento_id
    ).delete(synchronize_session=False)
    db.query(KpiInferido).filter(
        KpiInferido.instrumento_id == instrumento_id,
        KpiInferido.origen == "propuesta_etl",
    ).delete(synchronize_session=False)
    db.query(MetadatosEnriquecidos).filter(
        MetadatosEnriquecidos.instrumento_id == instrumento_id
    ).delete(synchronize_session=False)
    db.query(ImprovementOpportunity).filter(
        ImprovementOpportunity.instrumento_id == instrumento_id
    ).delete(synchronize_session=False)
    # Borrar los cachés (hallazgos analíticos, análisis de entrevista, perfiles v2) del análisis previo.
    for prev in (
        _results_findings_path(instrumento_id),
        _interview_analysis_path(instrumento_id),
        _respondent_profiles_path(instrumento_id),
    ):
        if prev.exists():
            try:
                prev.unlink()
            except OSError:
                pass
    db.flush()


def _log_propuestas_consola(db: Session, instrumento_id: int) -> None:
    """Imprime las propuestas en consola para inspección durante el desarrollo."""
    propuestas = (
        db.query(EtlPropuesta)
        .filter(EtlPropuesta.instrumento_id == instrumento_id)
        .order_by(EtlPropuesta.propuesta_id)
        .all()
    )
    print("\n" + "=" * 70)
    print(f"  PROPUESTAS DEL SIS — instrumento {instrumento_id} ({len(propuestas)})")
    print("=" * 70)
    for p in propuestas:
        print(f"  [{p.propuesta_id}] ({p.tipo}) {p.descripcion}")
        print(f"       acción: {p.accion_sugerida}")
        if p.valor_propuesto:
            print(f"       valor:  {p.valor_propuesto}")
    print("=" * 70 + "\n")


def _cache_canonical_if_survey(instrumento: InstrumentoProcesado, result: Any) -> None:
    """Guarda el Canonical del SIS como caché JSON para encuestas (salta S1-S3 al reingestar)."""
    if instrumento.tipo_instrumento != "encuesta" or result.canonical_survey_model is None:
        return
    try:
        cache_dir = settings.data_path_abs
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Nombre por instrumento (el hash real lo maneja el módulo de extracción para docs).
        cache_path = cache_dir / f"inst_{instrumento.instrumento_id}.canonical.json"
        cache_path.write_text(
            result.canonical_survey_model.model_dump_json(indent=2), encoding="utf-8"
        )
        instrumento.ruta_texto_limpio = str(cache_path.relative_to(settings.PROJECT_ROOT))
    except Exception as e:  # noqa: BLE001
        logging.warning(f"No se pudo cachear el Canonical: {e}")


def _results_findings_path(instrumento_id: int) -> Path:
    """Ruta del archivo con los hallazgos analíticos (insumo del JSON consolidado)."""
    return settings.data_path_abs / f"inst_{instrumento_id}.results.json"


def _cache_results_findings(instrumento_id: int, result: Any) -> None:
    """
    Persiste los hallazgos analíticos (S8b) generados en analyze, para que el JSON
    consolidado (generado luego en approve_enrichment) los incorpore.
    """
    findings = getattr(result, "results_findings", None)
    if not findings:
        return
    try:
        settings.data_path_abs.mkdir(parents=True, exist_ok=True)
        payload = [f.model_dump() for f in findings]
        _results_findings_path(instrumento_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logging.warning(f"No se pudieron cachear los hallazgos analíticos: {e}")


def _load_results_findings(instrumento_id: int) -> list[dict]:
    """Lee los hallazgos analíticos cacheados (o [] si no existen)."""
    path = _results_findings_path(instrumento_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _interview_analysis_path(instrumento_id: int) -> Path:
    """Ruta del archivo con el análisis de entrevista (insumo del JSON consolidado)."""
    return settings.data_path_abs / f"inst_{instrumento_id}.interview.json"


def _cache_interview_analysis(instrumento_id: int, result: Any) -> None:
    """
    Persiste el InterviewAnalysis (S10) generado en analyze, para que el JSON
    consolidado (generado luego en approve_enrichment) lo incorpore. Solo aplica a
    entrevistas; en encuestas result.interview_analysis es None y no se escribe nada.
    """
    analysis = getattr(result, "interview_analysis", None)
    if analysis is None:
        return
    try:
        settings.data_path_abs.mkdir(parents=True, exist_ok=True)
        _interview_analysis_path(instrumento_id).write_text(
            analysis.model_dump_json(indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logging.warning(f"No se pudo cachear el análisis de entrevista: {e}")


def _load_interview_analysis(instrumento_id: int) -> dict | None:
    """Lee el análisis de entrevista cacheado (o None si no existe)."""
    path = _interview_analysis_path(instrumento_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _respondent_profiles_path(instrumento_id: int) -> Path:
    """Ruta del caché de perfiles de respondente (rediseño v2, encuestas)."""
    return settings.data_path_abs / f"inst_{instrumento_id}.respondents.json"


def _is_v2_result(result: Any) -> bool:
    """True si el resultado del SIS es v2 (canónico reagrupado por preguntas)."""
    canonical = getattr(result, "canonical_survey_model", None)
    if canonical is None:
        return False
    return bool(getattr(canonical, "respondents_index", None))


def _cache_respondent_profiles(instrumento_id: int, result: Any) -> None:
    """
    Genera (DETERMINISTA, sin LLM) y cachea los perfiles de respondente cuando el
    resultado es v2. En v1 no aplica y no se escribe nada.
    """
    if not _is_v2_result(result):
        return
    try:
        from survey_intelligence.pipeline.stages.respondent_profiler import (
            build_respondent_profiles,
        )
        perfiles = build_respondent_profiles(result.canonical_survey_model)
        settings.data_path_abs.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump() for p in perfiles]
        _respondent_profiles_path(instrumento_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logging.warning(f"No se pudieron cachear los perfiles de respondente: {e}")


def _load_respondent_profiles(instrumento_id: int) -> list[dict] | None:
    """Lee los perfiles de respondente cacheados (o None si no existen = no es v2)."""
    path = _respondent_profiles_path(instrumento_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _persistir_propuestas_sis(
    db: Session, instrumento: InstrumentoProcesado, result: Any
) -> tuple[int, int, int]:
    """
    Mapea el SurveyIntelligenceResult a filas EtlPropuesta.

    - proposals (transformaciones)         -> tipo 'transformacion'
    - enriched.variables (semántica)       -> tipo 'metadato_enriquecido'
    - kpi_inferences                       -> tipo 'kpi_sugerido'

    Returns:
        (n_transformaciones, n_metadatos, n_kpis).
    """
    n_transf = n_meta = n_kpis = 0

    # 1) Transformaciones (limpieza).
    for p in result.proposals:
        db.add(EtlPropuesta(
            instrumento_id=instrumento.instrumento_id,
            tipo="transformacion",
            descripcion=_sis_serializar(p.descripcion),
            accion_sugerida=_sis_serializar(p.accion_sugerida),
            justificacion=_sis_serializar(p.justificacion),
            impacto_esperado=_sis_serializar(p.impacto_esperado),
            valor_original=_sis_serializar(p.valor_original),
            valor_propuesto=_sis_serializar(p.valor_propuesto),
            estado_decision="pendiente",
        ))
        n_transf += 1

    # 2) Metadatos enriquecidos (cara semántica de cada variable interpretable).
    enriched = result.enriched_survey_model
    if enriched is not None:
        for ev in enriched.variables_enriched:
            se = ev.semantic_enrichment
            if se is None or not se.construct_:
                continue
            payload = {
                "variable_id": ev.variable_id,
                "construct": se.construct_,
                "semantic_role": se.semantic_role,
                "tags": se.semantic_tags,
            }
            if se.analytical_sufficiency:
                payload["analytical_sufficiency"] = se.analytical_sufficiency.level.value
            db.add(EtlPropuesta(
                instrumento_id=instrumento.instrumento_id,
                tipo="metadato_enriquecido",
                descripcion=f"Enriquecimiento semántico de {ev.variable_id}: {se.construct_}",
                accion_sugerida="Agregar metadato semántico para chunking/RAG.",
                justificacion=se.analytical_sufficiency.reason if se.analytical_sufficiency else "Constructo inferido.",
                impacto_esperado="Chunks más ricos para búsqueda semántica futura.",
                valor_original=None,
                valor_propuesto=json.dumps(payload, ensure_ascii=False),
                estado_decision="pendiente",
            ))
            n_meta += 1

    # 3) KPIs inferidos (matching contra el catálogo del host).
    for kpi in result.kpi_inferences:
        kpi_row = db.query(KPI).filter(KPI.nombrekpi == kpi.nombre_sugerido).first()
        if kpi_row is None:
            continue  # solo KPIs del catálogo
        payload = {
            "kpi_id": kpi_row.kpi_id,
            "tipo_relacion": kpi.tipo_relacion or "inferido",
            "score_inferencia": kpi.score_relevancia,
        }
        db.add(EtlPropuesta(
            instrumento_id=instrumento.instrumento_id,
            tipo="kpi_sugerido",
            descripcion=f"KPI relevante: {kpi.nombre_sugerido}",
            accion_sugerida=f"Asociar el KPI '{kpi.nombre_sugerido}' al instrumento.",
            justificacion=kpi.evidencia_textual or "Inferido por el SIS.",
            impacto_esperado="Habilita analítica basada en indicadores.",
            valor_original=None,
            valor_propuesto=json.dumps(payload, ensure_ascii=False),
            estado_decision="pendiente",
        ))
        n_kpis += 1

    db.flush()
    return n_transf, n_meta, n_kpis


def _persistir_improvements(
    db: Session, instrumento: InstrumentoProcesado, result: Any
) -> int:
    """Guarda las oportunidades de mejora emitidas por el SIS (status=proposed)."""
    n = 0
    for opp in result.improvement_opportunities:
        rule = None
        if opp.proposed_rule is not None:
            rule = {
                "rule_id_candidate": opp.proposed_rule.rule_id_candidate,
                "when": opp.proposed_rule.when,
                "then": opp.proposed_rule.then,
            }
        db.add(ImprovementOpportunity(
            instrumento_id=instrumento.instrumento_id,
            sis_opportunity_id=opp.opportunity_id,
            scope=opp.scope.value if hasattr(opp.scope, "value") else str(opp.scope),
            titulo=opp.title,
            descripcion=opp.description,
            evidencia=list(opp.evidence),
            proposed_rule=rule,
            confianza=opp.confidence,
            generado_por=opp.generated_by,
            estado="proposed",
        ))
        n += 1
    db.flush()
    return n


def _aplicar_decisiones(
    db: Session,
    instrumento: InstrumentoProcesado,
    request: AprobacionRequest,
    tipos: set[str],
) -> tuple[int, int]:
    """
    Aplica decisiones (aceptada/rechazada) sobre las propuestas pendientes de los
    'tipos' indicados. Lanza 400 si queda alguna de esos tipos sin decidir.

    Returns:
        (n_aceptadas, n_rechazadas) de este camino.
    """
    ahora = datetime.now(timezone.utc)

    # Todas las propuestas del instrumento (para validar pertenencia al camino).
    todas = {
        p.propuesta_id: p
        for p in db.query(EtlPropuesta)
        .filter(EtlPropuesta.instrumento_id == instrumento.instrumento_id)
        .all()
    }
    # Propuestas que SÍ pertenecen a este camino (por tipo).
    del_camino = {pid: p for pid, p in todas.items() if p.tipo in tipos}

    decisiones = {d.propuesta_id: d.decision for d in request.decisiones}

    # Validación estricta: ninguna decisión debe apuntar a una propuesta de OTRO camino.
    ajenas = [
        pid for pid in decisiones
        if pid in todas and todas[pid].tipo not in tipos
    ]
    if ajenas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Las propuestas {ajenas} no pertenecen a este paso "
                f"(tipos válidos aquí: {sorted(tipos)}). Envíalas en el otro paso de aprobación."
            ),
        )
    # Validación: ids inexistentes.
    inexistentes = [pid for pid in decisiones if pid not in todas]
    if inexistentes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"propuesta_id inexistentes para este instrumento: {inexistentes}.",
        )

    for pid, propuesta in del_camino.items():
        if propuesta.estado_decision != "pendiente":
            continue
        decision = decisiones.get(pid)
        if decision is None:
            continue
        propuesta.estado_decision = decision
        propuesta.fecha_decision = ahora
        db.add(propuesta)
    db.flush()

    pendientes = [pid for pid, p in del_camino.items() if p.estado_decision == "pendiente"]
    if pendientes:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faltan decisiones para propuesta_id de este paso: {pendientes}.",
        )

    n_ace = sum(1 for p in del_camino.values() if p.estado_decision == "aceptada")
    n_rec = sum(1 for p in del_camino.values() if p.estado_decision == "rechazada")
    return n_ace, n_rec
