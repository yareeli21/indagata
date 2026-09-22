# Changelog - Indagata Backend

## [2026-09-20] - Refactorización por fases (auditoría A-G) + soporte de entrevistas

Basado en `backend/ARCHITECTURE_AUDIT_REPORT.md`. Verificado con la suite del SIS
(`python -m survey_intelligence.tests.run_all`, 80 tests) + arranque de la app.

### Fase A — Documentación e higiene
- Documentación (READMEs) alineada al flujo real; `httpx` declarado; `pool_pre_ping=True`;
  `print()` de depuración → logging.

### Fase B — Consistencia y encapsulación
- Normalizador único de `tipo_instrumento` (fuente única en `schemas_carga`).
- `survey_intelligence/host_toolkit.py`: superficie pública del SIS para el host.
- `api/core/domain_constants.py`: fuente única de constantes de dominio (tipos/estados).

### Fase C — Rendimiento y consistencia
- `relationship KpiInferido↔KPI` (viewonly, lazy=joined): elimina el N+1 y el SQL crudo repetido.
- Estado obsoleto `etl_pendiente` retirado del filtro de listado.

### Retiro de obsoletos del ETL antiguo
- Eliminados `EtlService._approve_legacy`, schemas `EtlExtractResponse` y `AprobacionResponse`.
- `services/llm_service.py`: retirado el ETL viejo (parser incluido); conserva solo stubs futuros del RAG.

### Fase D — Extracción unificada + envoltorio de JSON
- `api/services/extraction/`: módulo unificado de extracción por formato, desacoplado del tipo de instrumento.
- Envoltorio común aditivo del JSON consolidado (`instrument_type`, `summary_humano`, `traceability`, `rag_hints`).

### Fase E — Entrevistas (SIS)
- Contratos de entrevista (`contracts/interview.py`), `engine/nlp/` (diarización + análisis),
  etapa `s10_interview_analysis`, y consolidado con conocimiento de entrevista (participantes, turnos, temas, hallazgos, citas).

### Fases F/G — División de `services_carga.py`
- De 1236 líneas → `services_carga.py` (clases del wizard) + `carga_sis_mapping.py` (mapeo/caché/decisiones) + `carga_artifacts.py` (artefactos).

### Flujo ETL vigente (reemplaza al antiguo `etl/extract` + `etl/approve`)
```
upload → metadata → analyze (SIS) → approve/cleaning → approve/enrichment
estados: pendiente → metadata_registrado → etl_pendiente_limpieza
         → etl_pendiente_enriquecimiento → etl_aprobado
```

### Pendiente (Fase H — al activar JWT)
- Autenticación real (JWT), centralizar autorización, endurecer CORS.
- Flecos: `KPI.activo` (bool sobre Integer), docstring no-op de ChromaDB en `delete()`.

---

## [2026-09-03] - Sistema de visibilidad eliminado

### Cambios estructurales
- ✅ **Eliminado campo `visibilidad`** de `instrumento_procesado`
- ✅ **Todo es público** - Acceso RAG colaborativo
- ✅ **Permisos solo para escritura** - Solo propietario puede modificar/eliminar
- ✅ **Datos inmutables** - No se puede editar después de aprobar, solo eliminar y re-subir

### Migración aplicada
```sql
-- postgres/migrations/03_remove_visibilidad.sql
ALTER TABLE tt_rag.instrumento_procesado DROP CONSTRAINT IF EXISTS ck_visibilidad;
ALTER TABLE tt_rag.instrumento_procesado DROP COLUMN IF EXISTS visibilidad;
```

### Archivos modificados
- `backend/api/models/models_instrumentos.py` - Eliminado campo y constraint
- `backend/api/schemas/schemas_carga.py` - Eliminado `Visibilidad` type y campo en `UploadRequest`
- `backend/api/schemas/schemas_visualizacion.py` - Eliminado campo `visibilidad` de responses
- `backend/api/services/services_carga.py` - Eliminada asignación de visibilidad en upload
- `backend/api/services/services_visualizacion.py` - Eliminados filtros por visibilidad
- `backend/api/dependencies/dependencies_instrumentos.py` - Simplificado `puede_acceder_o_403()`
- `backend/api/routers/routers_carga.py` - Eliminado parámetro `visibilidad` de upload
- `backend/api/routers/routers_visualizacion.py` - Documentación actualizada
- `postgres/init/01_schema.sql` - Schema limpio sin visibilidad

### Estado anterior
- Instrumentos podían ser `public` o `private`
- Filtros por visibilidad en queries
- Lógica compleja en `puede_acceder_o_403()`

### Estado actual
- ✅ Todos los instrumentos son públicos
- ✅ Cualquier usuario puede ver/descargar cualquier instrumento
- ✅ Solo propietario puede aprobar ETL y eliminar
- ✅ Sin edición - para cambiar algo: eliminar y re-subir

---

## [Previo] - Cambios sistema de metadatos

### Metadatos Dublin Core
- ❌ **Eliminados:** `dc_contributor`, `dc_identifier`
- ✅ **Conservados:** 13 campos DC estándar
- ✅ **Autocompletados:** 6 campos (creator, publisher, type, format, date, language)
- ✅ **Manuales:** 7 campos (title, subject, description, coverage, rights, source, relation)

### KPIs
- ✅ KPIs se generan en **Paso 3 (ETL)** por el LLM
- ❌ NO se capturan manualmente en metadata

### LLM
- ✅ Modelo: `llama3.2:3b` (reemplazó `phi3:latest`)
- ✅ JSON más consistente
- ✅ Parser robusto con normalización de tildes

### JSON consolidado
- ✅ Se genera automáticamente en **Paso 4 (approve)**
- ✅ Guardado en `storage/json/{id}.json`
- ✅ Ruta actualizada en BD (`ruta_json`)

### Endpoint ingest()
- ❌ **DESHABILITADO** (comentado en router)
- ✅ JSON se genera en approve() automáticamente
- 📝 Estado final del módulo: `etl_aprobado`

---

## Flujo de endpoints (histórico a 2026-09-03 — reemplazado; ver entrada 2026-09-20)

### Carga (routers_carga.py)
1. `POST /instrumentos/upload` - Subir archivo (tipo_instrumento)
2. `GET /instrumentos/{id}/metadata/init` - Obtener datos pre-poblados
3. `POST /instrumentos/{id}/metadata` - Registrar 7 campos manuales
4. `GET /instrumentos/{id}/etl/extract` - LLM analiza y genera propuestas
5. `GET /instrumentos/{id}/etl/proposals` - Ver propuestas generadas
6. `POST /instrumentos/{id}/etl/approve` - **PASO FINAL** - Aprobar/rechazar propuestas, genera JSON

### Visualización (routers_visualizacion.py)
1. `GET /kpis` - Catálogo de KPIs
2. `GET /instrumentos` - Lista todos (acceso público)
3. `GET /instrumentos/{id}` - Detalle completo (acceso público)
4. `GET /instrumentos/{id}/download?type=original|json|sav` - Descargar (acceso público)
5. `DELETE /instrumentos/{id}` - Eliminar (solo propietario)

---

## Base de datos

### Estado limpio
```sql
-- Tablas maestras (conservadas con datos)
usuarios: 2 registros
kpi: 55 registros
kpi_variable: 116 registros
variable: 91 registros

-- Tablas de instrumentos (vacías después de limpieza)
instrumento_procesado: 0
metadatos_dc: 0
kpi_inferido: 0
etl_propuesta: 0
metadatos_enriquecidos: 0
permiso_instrumento: 0
pipeline_ingesta_log: 0
```

### Scripts de limpieza
- `postgres/migrations/04_limpiar_datos_prueba.sql` - Limpia instrumentos
- `limpiar_storage.ps1` - Limpia archivos físicos

---

## Próximos pasos

### Pendiente para .SAV (Futuro)
- Generación de archivos `.SAV` para encuestas
- Service: `backend/services/sav_generator.py`
- Integración en `approve()` solo para `tipo_instrumento == "encuesta"`
- Dependencia: `pyreadstat>=1.2.0`

### Vectorización (Módulo futuro)
- Estado final: `vectorizado` (después de `etl_aprobado`)
- Chunks en ChromaDB
- Endpoint separado: `POST /instrumentos/{id}/vectorize`
- Metadata en ChromaDB: `propietario_id` (ya no necesita `visibilidad`)

---

## Notas técnicas

### Convenciones
- IDs empiezan desde 1 después de limpieza
- Rutas relativas guardadas en BD (desde `PROJECT_ROOT`)
- Estados pipeline (vigentes): `pendiente` → `metadata_registrado` → `etl_pendiente_limpieza` → `etl_pendiente_enriquecimiento` → `etl_aprobado`

### Permisos
- Lectura: Todos (RAG colaborativo)
- Escritura: Solo propietario
- Tabla `permiso_instrumento` identifica propietario
- Función `puede_acceder_o_403()` siempre permite lectura
- Función `verificar_propietario()` valida escritura/eliminación
