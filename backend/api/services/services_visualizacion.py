# app/services/services_visualizacion.py
"""
Servicios de VISUALIZACIÓN y DESCARGA de instrumentos.

Responsabilidad: consultas de solo lectura + eliminación.
  InstrumentVisualizacionService.list()       → catálogo con filtros
  InstrumentVisualizacionService.get_detail() → detalle completo desde BD
  InstrumentVisualizacionService.download()   → ruta del artefacto en disco
  InstrumentVisualizacionService.delete()     → eliminar instrumento completo

No llama al LLM. Sin efectos secundarios de estado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models.models_instrumentos import (
    InstrumentoProcesado,
    KPI,
    KpiInferido,
    MetadatosDC,
    MetadatosEnriquecidos,
    PermisoInstrumento,
)
from api.schemas.schemas_visualizacion import (
    FiltrosInstrumento,
    InstrumentoDetalle,
    InstrumentoResumen,
    KpiCatalogo,
    KpiInferidoOutput,
    MetadatosEnriquecidosOutput,
    TipoDescarga,
)
from api.services.services_compartidos import ArchivoService, PermissionService


class InstrumentVisualizacionService:

    # ── Catálogo de KPIs ──────────────────────────────────────────────────────

    @staticmethod
    def list_kpis(db: Session) -> list[KpiCatalogo]:
        """
        Devuelve el catálogo completo de KPIs disponibles en el sistema.
        Se usa para llenar dropdowns y filtros en el frontend.
        """
        kpis = (
            db.query(KPI)
            .order_by(KPI.nombrekpi)
            .all()
        )

        return [
            KpiCatalogo(
                kpi_id=k.kpi_id,
                nombre=k.nombrekpi,
                descripcion=k.descripcion,
            )
            for k in kpis
        ]

    # ── Catálogo de instrumentos ──────────────────────────────────────────────

    @staticmethod
    def list(
        db:         Session,
        usuario_id: int,
        filtros:    FiltrosInstrumento,
    ) -> list[InstrumentoResumen]:
        """
        Lista todos los instrumentos del sistema (acceso público para RAG colaborativo).
        Solo muestra instrumentos con metadatos registrados (desde paso 2).
        Todos los instrumentos son en español (dc_language = 'es').
        
        Filtros aplicados:
        - tipo_instrumento: encuesta, entrevista, prueba_estandarizada
        - kpi_nombre: búsqueda parcial en nombres de KPIs asociados
        - busqueda: búsqueda de texto libre en dc_title y dc_description
        - desde/hasta: rango de fechas de creación
        """
        query = db.query(InstrumentoProcesado).filter(
            InstrumentoProcesado.estado.in_([
                "metadata_registrado",
                "etl_pendiente_limpieza",
                "etl_pendiente_enriquecimiento",
                "etl_aprobado",
                "en_ingesta", "vectorizado", "error",
            ]),
        )

        # Filtro: tipo de instrumento
        if filtros.tipo_instrumento:
            query = query.filter(InstrumentoProcesado.tipo_instrumento == filtros.tipo_instrumento)

        # Filtro: KPI por nombre (búsqueda parcial, case-insensitive)
        if filtros.kpi_nombre:
            # Usar una subquery con ORM correcto
            subq_kpi = (
                db.query(KpiInferido.instrumento_id)
                .join(KPI, KpiInferido.kpi_id == KPI.kpi_id)
                .filter(KPI.nombrekpi.ilike(f"%{filtros.kpi_nombre}%"))
                .scalar_subquery()
            )
            query = query.filter(InstrumentoProcesado.instrumento_id.in_(subq_kpi))

        # Filtro: búsqueda de texto libre en título y descripción
        if filtros.busqueda:
            query = query.join(MetadatosDC, MetadatosDC.instrumento_id == InstrumentoProcesado.instrumento_id, isouter=False)

            busqueda = f"%{filtros.busqueda.lower()}%"
            query = query.filter(
                or_(
                    MetadatosDC.dc_title.ilike(busqueda),
                    MetadatosDC.dc_description.ilike(busqueda)
                )
            )

        # Filtro: rango de fechas
        if filtros.desde:
            query = query.filter(InstrumentoProcesado.creado_en >= filtros.desde)
        if filtros.hasta:
            from datetime import datetime, time
            # Incluir todo el día hasta
            hasta_fin = datetime.combine(filtros.hasta, time.max)
            query = query.filter(InstrumentoProcesado.creado_en <= hasta_fin)

        instrumentos = (
            query
            .order_by(InstrumentoProcesado.creado_en.desc())
            .offset(filtros.skip)
            .limit(filtros.limit)
            .all()
        )

        # Construir respuesta con KPIs incluidos
        resultado = []
        for instr in instrumentos:
            # Nombres de KPIs vía relationship (joined load; sin SQL crudo ni N+1).
            kpis_nombres = [
                k.kpi.nombrekpi for k in instr.kpis_inferidos if k.kpi is not None
            ]

            resultado.append(InstrumentoResumen(
                instrumento_id=instr.instrumento_id,
                nombre=instr.nombre,
                tipo_instrumento=instr.tipo_instrumento,    # type: ignore
                idioma=instr.metadatos_dc.dc_language if instr.metadatos_dc else None,
                propietario=PermissionService.obtener_nombre_propietario(db, instr.instrumento_id),
                creado_en=instr.creado_en,
                kpis=kpis_nombres,
            ))
        
        return resultado

    # ── Detalle completo ──────────────────────────────────────────────────────

    @staticmethod
    def get_detail(
        db:          Session,
        instrumento: InstrumentoProcesado,
    ) -> InstrumentoDetalle:
        """
        Devuelve metadatos DC, KPIs con nombre resuelto desde tt_rag.kpi,
        y metadatos enriquecidos si existen. Todo desde PostgreSQL, no del JSON en disco.
        """
        propietario = PermissionService.obtener_nombre_propietario(db, instrumento.instrumento_id)
        idioma: str | None = None
        dublin_core: dict[str, Any] | None = None

        if instrumento.metadatos_dc:
            dc = instrumento.metadatos_dc
            idioma = dc.dc_language
            dublin_core = {
                "dc_title": dc.dc_title, 
                "dc_creator": dc.dc_creator,
                "dc_subject": json.loads(dc.dc_subject),
                "dc_description": dc.dc_description, 
                "dc_publisher": dc.dc_publisher,
                "dc_date": dc.dc_date,
                "dc_type": dc.dc_type, 
                "dc_format": dc.dc_format,
                "dc_language": dc.dc_language,
                "dc_coverage": dc.dc_coverage, 
                "dc_rights": dc.dc_rights,
                "dc_source": dc.dc_source, 
                "dc_relation": dc.dc_relation,
            }

        kpis_output: list[KpiInferidoOutput] = []
        for k in instrumento.kpis_inferidos:
            # Nombre del KPI vía relationship (joined load; sin SQL crudo ni N+1).
            nombre_kpi = k.kpi.nombrekpi if k.kpi is not None else f"KPI {k.kpi_id}"
            kpis_output.append(KpiInferidoOutput(
                kpi_id=k.kpi_id,
                nombre_kpi=nombre_kpi,
                tipo_relacion=k.tipo_relacion,
                evidencia_textual=k.evidencia_textual,
                score_inferencia=float(k.score_inferencia) if k.score_inferencia else None,
                origen=k.origen,
            ))

        meta_enriq: MetadatosEnriquecidosOutput | None = None
        if instrumento.metadatos_enriquecidos:
            me = instrumento.metadatos_enriquecidos
            meta_enriq = MetadatosEnriquecidosOutput(
                metadatos=me.metadatos or {}
            )

        return InstrumentoDetalle(
            instrumento_id=instrumento.instrumento_id,
            nombre=instrumento.nombre,
            tipo_instrumento=instrumento.tipo_instrumento,  # type: ignore
            idioma=idioma,
            propietario=propietario,
            creado_en=instrumento.creado_en,
            dublin_core=dublin_core,
            metadatos_enriquecidos=meta_enriq,
            kpis_inferidos_detalle=kpis_output,
            fecha_procesamiento=instrumento.fecha_procesamiento,
            error_detalle=instrumento.error_detalle,
        )

    # ── Descarga ──────────────────────────────────────────────────────────────

    @staticmethod
    def download(instrumento: InstrumentoProcesado, tipo: TipoDescarga) -> tuple[Path, str]:
        """
        Devuelve (ruta_absoluta, nombre_archivo) según el tipo solicitado.
        El router es el responsable de construir el FileResponse.
        """
        if tipo == "original":
            if not instrumento.ruta_archivo:
                raise HTTPException(status_code=404, detail="Archivo original no disponible.")
            return (
                ArchivoService.ruta_absoluta(instrumento.ruta_archivo),
                Path(instrumento.ruta_archivo).name,
            )

        if tipo == "json":
            if not instrumento.ruta_json:
                raise HTTPException(status_code=404, detail="JSON enriquecido no disponible. Completa la ingesta.")
            return (
                ArchivoService.ruta_absoluta(instrumento.ruta_json),
                f"instrumento_{instrumento.instrumento_id}.json",
            )

        if tipo == "sav":
            if instrumento.tipo_instrumento != "encuesta":
                raise HTTPException(status_code=422, detail=f"Solo las encuestas generan .sav. Tipo: '{instrumento.tipo_instrumento}'.")
            if not instrumento.ruta_sav:
                raise HTTPException(status_code=404, detail="Archivo .sav no disponible aún.")
            return (
                ArchivoService.ruta_absoluta(instrumento.ruta_sav),
                f"instrumento_{instrumento.instrumento_id}.sav",
            )

        raise HTTPException(status_code=422, detail=f"Tipo inválido: '{tipo}'. Use original, json o sav.")

    # ── Eliminación ───────────────────────────────────────────────────────────

    @staticmethod
    def delete(db: Session, instrumento: InstrumentoProcesado) -> None:
        """
        Elimina el instrumento, sus archivos en disco y los chunks en ChromaDB.
        
        Opción A (conservadora): NO elimina caché de texto limpio.
        Razón: Puede reutilizarse si se vuelve a subir el mismo archivo.
        La limpieza por antigüedad (script automático) se encarga del resto.
        
        Operación irreversible.
        """
        for ruta_rel in [
            instrumento.ruta_archivo,    # storage/raw/{id}.pdf
            instrumento.ruta_json,       # storage/json/{id}.json
            instrumento.ruta_sav,        # storage/sav/{id}.sav
            # ✅ NO eliminar ruta_texto_limpio (caché reutilizable)
            # instrumento.ruta_texto_limpio,  # storage/data/{hash}.txt
        ]:
            if ruta_rel:
                ArchivoService.eliminar_archivo(ArchivoService.ruta_absoluta(ruta_rel))

        # No-op hasta que se implemente el cliente de ChromaDB
        # VectorStoreService.delete_by_instrumento(instrumento.instrumento_id)

        db.delete(instrumento)
        db.commit()
