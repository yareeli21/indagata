# app/services/services_carga.py
"""
Servicios de CARGA de instrumentos.

Responsabilidad: pasos del wizard de carga (flujo vigente).
  Paso 1  — InstrumentCargaService.upload()
  Paso 2  — InstrumentCargaService.create_metadata()
  Paso 3  — EtlService.analyze()             ← ejecuta el SIS (vía services/sis_adapter.py)
  Paso 4a — EtlService.approve_cleaning()
  Paso 4b — EtlService.approve_enrichment()

REGLA: ningún método de este archivo llama a Ollama directamente.
El análisis vive en el SIS (survey_intelligence/), invocado por services/sis_adapter.py.

ORGANIZACIÓN (tras la división):
  - Este módulo: los dos servicios del wizard (InstrumentCargaService, EtlService).
  - carga_sis_mapping.py: mapeo SIS->BD, caché e idempotencia, aplicación de decisiones.
  - carga_artifacts.py:   generación de dataset limpio, .SAV y JSON consolidado.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.models_instrumentos import (
    EtlPropuesta,
    InstrumentoProcesado,
    MetadatosDC,
    PermisoInstrumento,
    Usuario,
)
from api.schemas.schemas_carga import (
    AnalyzeResponse,
    AprobacionRequest,
    CleaningApprovalResponse,
    EnrichmentApprovalResponse,
    EtlProposalsResponse,
    EtlPropuestaOutput,
    IngestaResponse,
    MetadataInitialData,
    MetadataRequest,
    MetadataResponse,
    UploadRequest,
    UploadResponse,
)
from api.services.services_compartidos import ArchivoService, PermissionService
from api.services.extraction import extraer_texto_con_cache, limpiar_texto

# Helpers de mapeo/caché/decisiones (mapeo del resultado del SIS al dominio del host).
from api.services.carga_sis_mapping import (
    _aplicar_decisiones,
    _borrar_analisis_previo,
    _cache_canonical_if_survey,
    _cache_interview_analysis,
    _cache_respondent_profiles,
    _cache_results_findings,
    _log_propuestas_consola,
    _persistir_improvements,
    _persistir_propuestas_sis,
)
# Helpers de generación de artefactos (dataset limpio, .SAV, JSON consolidado).
from api.services.carga_artifacts import (
    _generar_dataset_limpio,
    _generar_json_consolidado,
    _generar_sav,
    _materializar_enriquecimiento,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# InstrumentCargaService — pasos 1, 2 y 5
# ===========================================================================

class InstrumentCargaService:

    # ── Paso 1: Upload ──────────────────────────────────────────────────────

    @staticmethod
    async def upload(
        db:         Session,
        usuario_id: int,
        datos:      UploadRequest,
        archivo:    UploadFile,
        codebook:   UploadFile | None = None,
    ) -> UploadResponse:
        """
        Valida formato, verifica duplicados por MD5, guarda el archivo en
        storage/raw/ y crea el registro InstrumentoProcesado en estado 'pendiente'.
        También crea el PermisoInstrumento del propietario.

        Para ENCUESTAS, si se adjunta un `codebook`, se guarda y se registra en
        ruta_codebook. El SIS lo resuelve de forma determinística (etapa S5,
        sin RAG). Para otros tipos se ignora.
        """
        nombre_original = archivo.filename or "archivo"
        ArchivoService.validar_formato(
            nombre_original, archivo.content_type, datos.tipo_instrumento
        )

        contenido = await archivo.read()
        hash_md5  = ArchivoService.calcular_hash_md5(contenido)

        # Verificar duplicado dentro de los instrumentos del usuario
        instrumentos_usuario = (
            db.query(InstrumentoProcesado)
            .join(PermisoInstrumento,
                  PermisoInstrumento.instrumento_id == InstrumentoProcesado.instrumento_id)
            .filter(
                PermisoInstrumento.usuario_id == usuario_id,
                InstrumentoProcesado.ruta_archivo.isnot(None),
            )
            .all()
        )
        for inst in instrumentos_usuario:
            if inst.ruta_archivo:
                ruta = ArchivoService.ruta_absoluta(inst.ruta_archivo)
                if ruta.is_file() and ArchivoService.calcular_hash_md5(ruta.read_bytes()) == hash_md5:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Ya existe un instrumento con este archivo.",
                    )

        instrumento = InstrumentoProcesado(
            nombre=nombre_original,
            tipo_instrumento=datos.tipo_instrumento,
            estado="pendiente",
        )
        db.add(instrumento)
        db.flush()

        nombre_archivo = ArchivoService.generar_nombre_unico(instrumento.instrumento_id, nombre_original)
        ruta_abs = ArchivoService.guardar_archivo(contenido, settings.raw_path_abs, nombre_archivo)
        instrumento.ruta_archivo = ArchivoService.ruta_relativa(ruta_abs)

        # Codebook opcional (solo encuestas): diccionario estructurado que el SIS
        # resuelve de forma determinística (S5). Formatos admitidos: .csv o .pdf.
        if codebook is not None and datos.tipo_instrumento == "encuesta":
            cb_nombre_original = codebook.filename or "codebook"
            ArchivoService.validar_formato_codebook(cb_nombre_original)
            cb_contenido = await codebook.read()
            if cb_contenido:
                cb_nombre = ArchivoService.generar_nombre_unico(
                    instrumento.instrumento_id, f"codebook_{cb_nombre_original}"
                )
                cb_abs = ArchivoService.guardar_archivo(cb_contenido, settings.raw_path_abs, cb_nombre)
                instrumento.ruta_codebook = ArchivoService.ruta_relativa(cb_abs)

        db.add(instrumento)

        PermissionService.crear_propietario(db, instrumento.instrumento_id, usuario_id)
        db.commit()
        db.refresh(instrumento)

        return UploadResponse(
            instrumento_id=instrumento.instrumento_id,
            estado=instrumento.estado,   # type: ignore
            mensaje="Archivo subido correctamente. Continúa con el registro de metadatos.",
        )

    # ── Paso 2: Metadatos Dublin Core ───────────────────────────────────────

    @staticmethod
    def get_metadata_initial_data(
        db:             Session,
        usuario_id:     int,
        instrumento_id: int,
    ) -> MetadataInitialData:
        """
        Devuelve datos pre-poblados para inicializar el formulario del Paso 2.
        El frontend los muestra en campos de solo lectura + dc_title editable.
        """
        instrumento = db.get(InstrumentoProcesado, instrumento_id)
        if instrumento is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento no encontrado.")

        if not PermissionService.es_propietario(db, instrumento_id, usuario_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede acceder.")

        usuario = db.get(Usuario, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        # Autocompletar campos
        dc_creator = usuario.usuario
        dc_publisher = settings.APP_NAME
        dc_type = instrumento.tipo_instrumento
        dc_format = Path(instrumento.ruta_archivo).suffix.lstrip(".") if instrumento.ruta_archivo else "desconocido"
        dc_date = instrumento.creado_en.strftime("%Y-%m-%d")
        dc_language = "es"
        dc_title_sugerido = instrumento.nombre

        return MetadataInitialData(
            instrumento_id=instrumento_id,
            dc_creator=dc_creator,
            dc_publisher=dc_publisher,
            dc_type=dc_type,
            dc_format=dc_format,
            dc_date=dc_date,
            dc_language=dc_language,
            dc_title_sugerido=dc_title_sugerido,
        )

    @staticmethod
    def create_metadata(
        db:             Session,
        usuario_id:     int,
        instrumento_id: int,
        request:        MetadataRequest,
    ) -> MetadataResponse:
        """
        Registra los 13 campos Dublin Core.

        AUTOCOMPLETADOS (6 campos):
        - dc_creator → usuario autenticado
        - dc_publisher → configuración institucional (APP_NAME)
        - dc_type → InstrumentoProcesado.tipo_instrumento
        - dc_format → extensión del archivo
        - dc_date → fecha de registro
        - dc_language → "es" por defecto

        CAPTURA MANUAL (7 campos):
        - dc_title, dc_subject, dc_description, dc_coverage, dc_rights, dc_source, dc_relation

        Inmutable: un segundo intento devuelve 409.
        """
        instrumento = db.get(InstrumentoProcesado, instrumento_id)
        if instrumento is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento no encontrado.")

        if not PermissionService.es_propietario(db, instrumento.instrumento_id, usuario_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede registrar metadatos.")

        if db.query(MetadatosDC).filter(MetadatosDC.instrumento_id == instrumento.instrumento_id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Los metadatos ya fueron registrados.")

        usuario = db.get(Usuario, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        # Autocompletar campos
        dc_creator = usuario.usuario
        dc_publisher = settings.APP_NAME
        dc_type = instrumento.tipo_instrumento
        dc_format = Path(instrumento.ruta_archivo).suffix.lstrip(".") if instrumento.ruta_archivo else "desconocido"
        dc_date = instrumento.creado_en.strftime("%Y-%m-%d")
        dc_language = "es"

        metadatos = MetadatosDC(
            instrumento_id=instrumento.instrumento_id,
            dc_title=request.dc_title,
            dc_creator=dc_creator,
            dc_subject=json.dumps(request.dc_subject, ensure_ascii=False),
            dc_description=request.dc_description,
            dc_publisher=dc_publisher,
            dc_date=dc_date,
            dc_type=dc_type,
            dc_format=dc_format,
            dc_language=dc_language,
            dc_coverage=request.dc_coverage,
            dc_rights=request.dc_rights,
            dc_source=request.dc_source,
            dc_relation=request.dc_relation,
        )
        db.add(metadatos)

        instrumento.nombre = request.dc_title
        instrumento.estado = "metadata_registrado"
        instrumento.fecha_procesamiento = datetime.now(timezone.utc)
        db.add(instrumento)
        db.commit()
        db.refresh(instrumento)

        return MetadataResponse(
            instrumento_id=instrumento.instrumento_id,
            estado=instrumento.estado,  # type: ignore
            mensaje="Metadatos registrados correctamente. Puedes iniciar el análisis ETL.",
        )

    # ── Paso 5: Ingesta ─────────────────────────────────────────────────────

    @staticmethod
    def ingest(
        db:             Session,
        usuario_id:     int,
        instrumento_id: int,
    ) -> IngestaResponse:
        """
        Finaliza el pipeline de carga.
        Requiere estado 'etl_aprobado'. Cambia el estado a 'disponible'.

        El JSON consolidado ya fue generado en el paso anterior (approve).
        Este paso simplemente marca el instrumento como disponible para consulta/descarga.
        """
        instrumento = db.get(InstrumentoProcesado, instrumento_id)
        if instrumento is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento no encontrado.")

        if not PermissionService.es_propietario(db, instrumento_id, usuario_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede ejecutar la ingesta.")

        if instrumento.estado != "etl_aprobado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El instrumento debe estar en estado 'etl_aprobado'. "
                    f"Estado actual: '{instrumento.estado}'."
                ),
            )

        # Verificar que el JSON consolidado existe
        if not instrumento.ruta_json:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="JSON consolidado no encontrado. Vuelve a aprobar las propuestas ETL.",
            )

        # NO cambiar estado - el estado final de este módulo es 'etl_aprobado'
        # La vectorización será un módulo futuro que procesará instrumentos en 'etl_aprobado'

        return IngestaResponse(
            instrumento_id=instrumento_id,
            mensaje=(
                "JSON consolidado disponible para descarga. "
                "Estado: 'etl_aprobado'. "
                "La vectorización se implementará en un módulo futuro."
            ),
        )


# ===========================================================================
# EtlService — pasos 3 y 4 (interacción con el SIS)
# ===========================================================================

class EtlService:
    """
    Orquestador del host sobre el Survey Intelligence Service (SIS).

    Flujo nuevo:
      analyze()            -> ejecuta el SIS completo, persiste propuestas.  (etl_pendiente_limpieza)
      get_proposals()      -> idempotente, ver propuestas.
      approve_cleaning()   -> camino 1: transformaciones (drop/normalize).
                              (etl_pendiente_enriquecimiento)
      approve_enrichment() -> camino 2: metadatos enriquecidos + KPIs, genera JSON + .SAV.  (etl_aprobado)

    El SIS se invoca vía services/sis_adapter.py (único punto de acople).
    """

    # ── analyze: ejecuta el SIS completo ─────────────────────────────────────

    @staticmethod
    def analyze(
        db:          Session,
        instrumento: InstrumentoProcesado,
    ) -> "AnalyzeResponse":
        """
        Ejecuta el SIS (S1..S9) en una sola llamada y persiste las propuestas.
        Requiere 'metadata_registrado' (o reintento desde 'etl_pendiente_limpieza').

        GARANTÍAS:
          - Idempotente: al reanalizar, borra propuestas/mejoras previas del
            instrumento (no duplica).
          - Transaccional: si el SIS falla, se hace rollback y el estado NO cambia
            (el instrumento queda como estaba para poder reintentar).
        """
        from services import sis_adapter

        # Permite reintentar si el estado quedó en el primer paso (reanálisis).
        estados_reanalizables = {"metadata_registrado", "etl_pendiente_limpieza"}
        if instrumento.estado not in estados_reanalizables:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El análisis requiere estado 'metadata_registrado' (o reintento en "
                    f"'etl_pendiente_limpieza'). Actual: '{instrumento.estado}'."
                ),
            )

        # 1) Extraer texto para documentos (fuera de la transacción de escritura).
        extracted_text: str | None = None
        ruta_cache_rel: str | None = None
        if instrumento.tipo_instrumento != "encuesta":
            ruta = ArchivoService.ruta_absoluta(instrumento.ruta_archivo)
            texto_crudo, _desde_cache, ruta_cache = extraer_texto_con_cache(ruta)
            extracted_text = limpiar_texto(texto_crudo)
            if ruta_cache:
                ruta_cache_rel = str(ruta_cache.relative_to(settings.PROJECT_ROOT))

        # 2) Ejecutar el SIS (llamadas al LLM). Si lanza, no hemos tocado la BD aún.
        request = sis_adapter.build_request(
            instrumento, request_id=f"inst-{instrumento.instrumento_id}",
            extracted_text=extracted_text,
        )
        service = sis_adapter.build_service(db)
        result = service.process(request)

        status_val = result.status.value if hasattr(result.status, "value") else str(result.status)
        if status_val == "failed":
            # No se cambia el estado: el instrumento sigue reanalizables.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El SIS no pudo procesar el instrumento (archivo ilegible o vacío).",
            )

        # 3) Persistencia atómica: borrar lo previo, insertar lo nuevo, cambiar estado.
        try:
            _borrar_analisis_previo(db, instrumento.instrumento_id)

            if ruta_cache_rel:
                instrumento.ruta_texto_limpio = ruta_cache_rel
            _cache_canonical_if_survey(instrumento, result)
            _cache_results_findings(instrumento.instrumento_id, result)
            _cache_interview_analysis(instrumento.instrumento_id, result)
            _cache_respondent_profiles(instrumento.instrumento_id, result)

            n_transf, n_meta, n_kpis = _persistir_propuestas_sis(db, instrumento, result)
            n_improvements = _persistir_improvements(db, instrumento, result)

            instrumento.estado = "etl_pendiente_limpieza"
            instrumento.fecha_procesamiento = datetime.now(timezone.utc)
            db.add(instrumento)
            db.commit()
        except Exception:
            db.rollback()
            raise

        # 4) Mostrar las propuestas en consola para inspección.
        _log_propuestas_consola(db, instrumento.instrumento_id)

        return AnalyzeResponse(
            instrumento_id=instrumento.instrumento_id,
            estado="etl_pendiente_limpieza",
            status_sis=status_val,
            n_transformaciones=n_transf,
            n_metadatos=n_meta,
            n_kpis=n_kpis,
            n_hallazgos=len(result.results_findings),
            n_improvements=n_improvements,
            degraded=result.diagnostics.degraded,
            mensaje=(
                f"Análisis del SIS completado. {n_transf} propuestas de limpieza, "
                f"{n_meta} metadatos, {n_kpis} KPIs, {len(result.results_findings)} hallazgos, "
                f"{n_improvements} mejoras."
            ),
        )

    # ── Ver propuestas (idempotente) ─────────────────────────────────────────

    @staticmethod
    def get_proposals(
        db:          Session,
        instrumento: InstrumentoProcesado,
    ) -> EtlProposalsResponse:
        """Disponible tras el análisis y en 'etl_aprobado'. Idempotente."""
        estados_ok = {"etl_pendiente_limpieza", "etl_pendiente_enriquecimiento", "etl_aprobado"}
        if instrumento.estado not in estados_ok:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Propuestas disponibles tras el análisis. Actual: '{instrumento.estado}'.",
            )

        propuestas = (
            db.query(EtlPropuesta)
            .filter(EtlPropuesta.instrumento_id == instrumento.instrumento_id)
            .order_by(EtlPropuesta.propuesta_id)
            .all()
        )
        output = [EtlPropuestaOutput.model_validate(p) for p in propuestas]

        return EtlProposalsResponse(
            instrumento_id=instrumento.instrumento_id,
            estado=instrumento.estado,  # type: ignore
            propuestas=output,
            n_pendientes=sum(1 for p in propuestas if p.estado_decision == "pendiente"),
            n_aceptadas=sum(1 for p in propuestas if p.estado_decision == "aceptada"),
            n_rechazadas=sum(1 for p in propuestas if p.estado_decision == "rechazada"),
        )

    # ── Camino 1: aprobar LIMPIEZA (transformaciones) ────────────────────────

    @staticmethod
    def approve_cleaning(
        db:          Session,
        instrumento: InstrumentoProcesado,
        request:     AprobacionRequest,
    ) -> "CleaningApprovalResponse":
        """
        Decide sobre las propuestas 'transformacion' (drop_columns, normalize_scale).
        Requiere 'etl_pendiente_limpieza'. Pasa a 'etl_pendiente_enriquecimiento'.
        """
        if instrumento.estado != "etl_pendiente_limpieza":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estado requerido: 'etl_pendiente_limpieza'. Actual: '{instrumento.estado}'.",
            )

        try:
            n_ace, n_rec = _aplicar_decisiones(db, instrumento, request, tipos={"transformacion"})

            # Ejecutar las transformaciones aceptadas sobre los datos -> dataset limpio.
            ruta_limpio = _generar_dataset_limpio(db, instrumento)

            instrumento.estado = "etl_pendiente_enriquecimiento"
            instrumento.fecha_procesamiento = datetime.now(timezone.utc)
            db.add(instrumento)
            db.commit()
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise

        if ruta_limpio:
            logging.info(f"Dataset limpio disponible en: {ruta_limpio}")

        return CleaningApprovalResponse(
            instrumento_id=instrumento.instrumento_id,
            estado="etl_pendiente_enriquecimiento",
            n_aceptadas=n_ace,
            n_rechazadas=n_rec,
            n_aplicadas=n_ace,
            ruta_dataset_limpio=ruta_limpio,
            mensaje=(
                f"Limpieza decidida. {n_ace} transformaciones aceptadas, {n_rec} rechazadas. "
                + (f"Dataset limpio en {ruta_limpio}. " if ruta_limpio else "")
                + "Continúa con el enriquecimiento."
            ),
        )

    # ── Camino 2: aprobar ENRIQUECIMIENTO (metadatos + KPIs) ──────────────────

    @staticmethod
    def approve_enrichment(
        db:          Session,
        instrumento: InstrumentoProcesado,
        request:     AprobacionRequest,
    ) -> "EnrichmentApprovalResponse":
        """
        Decide sobre 'metadato_enriquecido' y 'kpi_sugerido'. Crea MetadatosEnriquecidos
        y KpiInferido. Genera el JSON consolidado (y .SAV si es encuesta).
        Requiere 'etl_pendiente_enriquecimiento'. Pasa a 'etl_aprobado'.
        """
        if instrumento.estado != "etl_pendiente_enriquecimiento":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estado requerido: 'etl_pendiente_enriquecimiento'. Actual: '{instrumento.estado}'.",
            )

        n_ace, n_rec = _aplicar_decisiones(
            db, instrumento, request, tipos={"metadato_enriquecido", "kpi_sugerido"}
        )
        _materializar_enriquecimiento(db, instrumento)

        instrumento.estado = "etl_aprobado"
        instrumento.fecha_procesamiento = datetime.now(timezone.utc)
        db.add(instrumento)
        db.commit()
        db.refresh(instrumento)

        try:
            json_path = _generar_json_consolidado(db, instrumento)
            instrumento.ruta_json = str(json_path.relative_to(settings.PROJECT_ROOT))
            db.add(instrumento)
            db.commit()
        except Exception as e:  # noqa: BLE001
            logging.error(f"Error al generar JSON consolidado: {e}", exc_info=True)

        # Generar .SAV (solo encuestas), con etiquetas y niveles de medición SPSS.
        ruta_sav = None
        try:
            ruta_sav = _generar_sav(instrumento)
            if ruta_sav:
                instrumento.ruta_sav = ruta_sav
                db.add(instrumento)
                db.commit()
        except Exception as e:  # noqa: BLE001
            logging.error(f"Error al generar .SAV: {e}", exc_info=True)

        mensaje = f"Enriquecimiento decidido. {n_ace} aceptadas, {n_rec} rechazadas. JSON consolidado generado."
        if ruta_sav:
            mensaje += f" Archivo .SAV disponible en {ruta_sav}."

        return EnrichmentApprovalResponse(
            instrumento_id=instrumento.instrumento_id,
            estado="etl_aprobado",
            n_aceptadas=n_ace,
            n_rechazadas=n_rec,
            mensaje=mensaje,
        )
