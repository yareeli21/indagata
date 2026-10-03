# Downstream breakage report — `shared/` realigned to `01_schema.sql`

The `shared/` data layer now mirrors `infrastructure/postgres/init/01_schema.sql`
1:1. Service files were NOT edited (per the task). This is the catalog of every
downstream reference expected to break because its table/column/class no longer
exists in the SQL. The user must triage these in the services.

## Removed classes/tables (no table in the SQL)

- `PermisoInstrumento` (table `permiso_instrumento`) — deleted.
- `PreguntaKPI` (table `pregunta_kpi`) — deleted.
- `Institucion` (table `instituciones`) — deleted.
- `ValorVariable` (table `valor_variable`) — deleted.
- `MetadatosEnriquecidosPruebasEstandarizadas` — renamed to
  `MetadatosEnriquecidosPruebas` (table `metadatos_enriquecidos_pruebas`).

## Active services

### services/instrument-service/app/service.py
- Imports `PermisoInstrumento` → `ImportError` (class removed).
- Constructs `InstrumentoProcesado(nombre=..., tipo_instrumento=..., plataforma=..., estado=...)`
  and uses `.instrumento_id`. The realigned model has `id_instrumento`, `id_crudo`,
  `ruta_de_archivo_limpio`, `ruta_json`, `estado`, `fecha_procesamiento`,
  `fecha_aprobado` only. `nombre`, `tipo_instrumento`, `plataforma`,
  `instrumento_id` do not exist.
- Constructs `RawData(instrumento_id=..., rol_archivo=..., nombre_original=...,
  tamano_bytes=..., hash_md5=...)`. The realigned `raw_data` has `id_crudo`,
  `id_owner`, `tipo_instrumento`, `nombre_archivo`, `raw_archivo`,
  `raw_archivo_original`, `fecha_carga` only. None of those old columns exist.

### services/instrument-service/app/routers/upload.py
- Uses `InstrumentoProcesado` with old attributes (`nombre`, `tipo_instrumento`,
  `plataforma`, `instrumento_id`) → `AttributeError`/construction failures.

### services/instrument-service/app/dependencies.py
- Imports `Usuario` (still exists) but references `.usuario`/`.creado_en`, which no
  longer exist (now `nombre`/`fecha_registro`).

### services/analysis-service/app/service.py
- Imports `MetadatosEnriquecidosPruebasEstandarizadas` → `ImportError` (renamed to
  `MetadatosEnriquecidosPruebas`).
- Uses `MetadatosDC(instrumento_id=...)`; PK is now `id_crudo` (FK to
  `raw_data.id_crudo`). `instrumento_id` removed.
- Uses `inst.nombre`, `inst.ruta_texto_limpio`, `inst.tipo_instrumento` on
  `InstrumentoProcesado` — none exist in the realigned model.
- Uses `KPIInferido.instrumento_id`, `KPIInferido.score_similitud` — removed. The
  realigned `kpi_inferido` has composite PK `(id_procesado, kpi_id)` plus `razon`,
  `resultado`, `fecha_inferencia`.
- Uses `KPI.nombrekpi` — now `nombre_kpi`.

### services/analysis-service/app/kpi_search.py
- Uses `KPI.nombrekpi` (now `nombre_kpi`), `KPI.direccion_deseada`, `KPI.activo`,
  `KPI.unidad` — none exist in the realigned `kpi`.

### services/analysis-service/app/storage.py
- Uses `RawData.instrumento_id`, `RawData.rol_archivo`, `RawData.raw_data_id` —
  none exist (SQL `raw_data` has `id_crudo`, `id_owner`, `raw_archivo`, ...).

### services/analysis-service/app/dependencies.py
- Imports `Usuario` (still exists) but references `.usuario`/`.creado_en` — removed.

## Repository layer

- The entire `shared/repositories/` layer was deleted as unsalvageable: every repo
  depended on a removed Create/Update DTO (which nothing imported) or referenced a
  column absent from the SQL. A repo-wide grep found NO importer of
  `shared.repositories.*` today, so no active service breaks from the removal.
  `shared/repositories/__init__.py` remains so the package stays importable.
  Services needing persistence helpers should build them against the realigned
  models.

Removed repos: `documento_vectorizado_repository.py`, `instrumento_repository.py`,
`kpi_repository.py`, `pregunta_kpi_repository.py`, `prompt_repository.py`,
`rag_log_repository.py`.

## Out of scope

- `services/services_que_estaban_en_backend/*` is legacy/dead code importing from a
  different `api.*`/`app.*` package and is NOT part of the active shared contract.
  It references `PermisoInstrumento`, `nombrekpi`, etc., and would break too, but it
  is out of scope for this realignment.
