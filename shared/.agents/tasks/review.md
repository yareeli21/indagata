# Realign `shared/` to `01_schema.sql` — 1:1 ORM/DTO mapping

The coder rewrote `shared/models`, `shared/schemas`, and `shared/repositories` so the shared package mirrors the 17 tables of schema `tt_rag` in `infrastructure/postgres/init/01_schema.sql` exactly, with no invented tables or columns. Every model was checked column-by-column against the DDL: table names, PK columns (including the four composite PKs), column names/types/nullability, FK targets with `ondelete`, the composite `ForeignKeyConstraint`s, the `estado` CHECK, the literally-named `timestamp` column on `rag_log`, and the `chunk_metadata` JSONB default. The four phantom models (`institucion`, `permiso_instrumento`, `pregunta_kpi`, `valor_variable`) are gone, the 14 unused legacy schema modules and all 6 repositories were deleted, and `shared/models/__init__.py` exports exactly the 17 classes. The SQL source of truth was not modified.

Watch for: nothing blocking. One informational note on `rag_log.timestamp` shadowing a Python builtin at the attribute level (confirmed, intentional per plan, 1:1 with SQL). The whole repository layer was deleted as unsalvageable, which is a user-accepted trade-off documented in the plan and breakages report (confirmed).

**Verdict**: APPROVED

## High-level view

The 17 ORM classes map 1:1 to the SQL. Scalar columns, nullability (`Mapped[T]` vs `Mapped[T | None]`), and types line up with the DDL — `SERIAL` PKs use `primary_key=True, autoincrement=True`, `VARCHAR(n)` → `String(n)`, `TEXT` → `Text`, `JSONB` → the Postgres dialect type, `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` → `server_default=func.now()`. Every model carries `__table_args__` with `schema=tt_rag`, directly or as the trailing dict in a constraints tuple.

Relationship wiring matches the DDL. Single-column FKs use `ForeignKey(..., ondelete=...)`; the two composite children (`valor_variable_inferido`, `kpi_inferido_chunk`) use a `ForeignKeyConstraint` back to `kpi_inferido`'s composite PK plus a separate single FK, both placed before the schema dict in the tuple. The four composite-PK tables (`kpi_variable`, `kpi_inferido`, `valor_variable_inferido`, `kpi_inferido_chunk`) mark each PK member correctly.

The DTO surface in `shared/schemas/__init__.py` is four Pydantic models (`UsuarioRead`, `InstrumentoRead`, `MetadatosDCBase`, `KPIRead`) whose fields are a subset of the matching SQL columns with correct optionality. `MetadatosDCBase` keeps its exact name (analysis-service imports it) and carries all 13 DC fields with only `dc_title` required.

The repository layer is intentionally empty (`__init__.py` only). Every prior repo depended on a removed Create/Update DTO or referenced a column absent from the SQL, so all six were deleted rather than patched with invented columns. Services needing persistence helpers must build them against the realigned models — a trade-off the plan calls out explicitly.

<details>
<summary>Issues (0)</summary>

No blocking or actionable findings. See the informational notes in the summary and sections below.

</details>

<details>
<summary>Details</summary>

### Per-table correctness

Checked each model against the DDL. All 17 match on table name, PK, columns, types, nullability, and FK/`ondelete`:

- `usuario` → `Usuario`: `usuario_id` SERIAL PK; `nombre String(255)` NOT NULL; `email String(255)` unique NOT NULL; `password_hash Text` NOT NULL; `rol String(50)` nullable; `fecha_registro` server_default now. Match.
- `raw_data` → `RawData`: `id_crudo` SERIAL PK; `id_owner` FK→`usuario.usuario_id` CASCADE NOT NULL; `tipo_instrumento String(50)` NOT NULL; `nombre_archivo`/`raw_archivo` Text NOT NULL; `raw_archivo_original` Text nullable; `fecha_carga` server_default now. Match.
- `instrumento_procesado` → `InstrumentoProcesado`: `id_instrumento` SERIAL PK; `id_crudo` FK→`raw_data.id_crudo` CASCADE NOT NULL; `ruta_de_archivo_limpio String(255)`; `ruta_json Text`; `estado String(50)` NOT NULL default `'recibido'` with the 7-value CHECK (`ck_instrumento_estado`); `fecha_procesamiento` server_default now; `fecha_aprobado` nullable. CHECK value list matches the SQL verbatim. Match.
- `metadatos_dc` → `MetadatosDC`: `id_crudo` PK=FK→`raw_data.id_crudo` CASCADE; `dc_title Text` NOT NULL; remaining 12 DC columns with exact types (`dc_date String(100)`, `dc_rights String(255)`, `dc_format String(50)`, `dc_relation Text`, etc.). Match.
- `metadatos_enriquecidos_encuestas` → `MetadatosEnriquecidosEncuestas`: PK=FK `id_crudo` CASCADE; `n_respondentes`/`n_poblacion Integer`; four Text columns. Match.
- `metadatos_enriquecidos_entrevistas` → `MetadatosEnriquecidosEntrevistas`: PK=FK `id_crudo` CASCADE; 5 Text columns. Match.
- `metadatos_enriquecidos_pruebas` → `MetadatosEnriquecidosPruebas` (file `metadatos_pruebasestandarizadas.py`): PK=FK `id_crudo` CASCADE; `mapeo_de_reactivos_por_seccion` JSONB; 13 other columns incl. `grupo`, `nivel_educativo`, `subareas`, `competencias`. Match.
- `coleccion_vectorial` → `ColeccionVectorial`: `coleccion_id` SERIAL PK; `nombre Text` unique NOT NULL; `embedding_model String(100)`; `chunk_size`/`chunk_overlap Integer`; `creado_en` server_default now. Match.
- `prompts` → `Prompt` (`__tablename__ = "prompts"`): `prompt_id` SERIAL PK; `tipo String(50)` NOT NULL; `version String(10)` NOT NULL; `contenido Text` NOT NULL; `coleccion_id` FK→`coleccion_vectorial.coleccion_id` SET NULL nullable; `activo Boolean` default True; `creado_en` server_default now. Old `UniqueConstraint(tipo,version)` correctly dropped. Match.
- `kpi` → `KPI`: `kpi_id` SERIAL PK; `nombre_kpi Text` NOT NULL; `descripcion`/`categoria`/`ambito`/`url_documentacion`/`formula` Text nullable. No `activo`/`nombrekpi`. Match.
- `variable` → `Variable`: `variable_id` SERIAL PK; `nombre_variable Text` NOT NULL; `descripcion Text`; `tipo_dato String(20)`; `unidad Text`. No UNIQUE on `nombre_variable` (SQL has none). Match.
- `kpi_variable` → `KPIVariable`: composite PK `(kpi_id, variable_id)`, both FKs CASCADE. Match.
- `kpi_inferido` → `KPIInferido`: composite PK `(id_procesado, kpi_id)`; `id_procesado` FK→`instrumento_procesado.id_instrumento` CASCADE; `kpi_id` FK→`kpi.kpi_id` CASCADE; `razon Text`; `resultado Numeric`; `fecha_inferencia` server_default now. Match.
- `valor_variable_inferido` → `ValorVariableInferido`: composite PK `(id_procesado, kpi_id, variable_id)`; `variable_id` single FK→`variable.variable_id` CASCADE; composite FK `(id_procesado, kpi_id)`→`kpi_inferido` CASCADE; value columns Numeric/Text/Boolean/Numeric. Match.
- `rag_log` → `RagLog`: `rag_log_id` SERIAL PK; `pregunta Text` NOT NULL; `respuesta Text`; `modelo_usado String(100)`; `chunks_usados`/`latencia_ms Integer`; column literally named `timestamp` via `mapped_column("timestamp", ...)`. Match.
- `documento_vectorizado` → `DocumentoVectorizado`: `documento_vectorizado_id` SERIAL PK; `instrumento_id` FK CASCADE nullable; `coleccion_id` FK SET NULL nullable; `chroma_vector_id Text`; `chunk_index Integer`; `seccion Text`; `chunk_texto Text` NOT NULL; `chunk_metadata JSONB server_default text("'{}'::jsonb")`; `n_tokens Integer`; `almacenado_en` server_default now. Match.
- `kpi_inferido_chunk` → `KpiInferidoChunk`: composite PK `(id_procesado, kpi_id, documento_vectorizado_id)`; `documento_vectorizado_id` single FK→`documento_vectorizado` CASCADE; composite FK `(id_procesado, kpi_id)`→`kpi_inferido` CASCADE; `score Numeric`. Match.

No model or schema references a table or column absent from the SQL. No invented columns found.

### Composite-FK placement and schema qualification

For the two composite children, `__table_args__` is a tuple with the `ForeignKeyConstraint` first and `{"schema": SCHEMA}` as the trailing element — the required ordering so the schema dict is recognized. The single-column `variable_id`/`documento_vectorizado_id` FKs on those tables are declared on the column (correct, since they target single-column PKs), while the two-column parent key goes through the constraint. This matches the SQL, which declares the composite FK separately from the single-column `variable`/`documento_vectorizado` references. Every one of the 17 models carries `schema=tt_rag`.

### `rag_log.timestamp` naming (informational, confirmed)

The attribute is named `timestamp` and explicitly mapped to the DB column `"timestamp"` via `mapped_column("timestamp", ...)`, keeping the model 1:1 with the SQL column name. Intentional per the plan, not a defect.

### Deleted models, schemas, and repositories

Directory listing confirms `shared/models/` holds exactly the 17 model modules plus `__init__.py` — `institucion.py`, `permiso_instrumento.py`, `pregunta_kpi.py`, `valor_variable.py`, and `tabla_chunks.py` are gone. `shared/schemas/` holds only `__init__.py` (14 legacy loose DTO modules deleted). `shared/repositories/` holds only `__init__.py`.

The repository layer was removed in full because, once the unused legacy Create/Update DTOs were deleted, every repo either depended on one of those DTOs or referenced a column not in the SQL (`hash_md5`, `KPI.activo`, `KPI.id_kpi`, `RagLog.fecha`, `DocumentoVectorizado.id_instrumento`/`.activo`). Deleting rather than inventing columns is the correct call under the "map only to the SQL" constraint, and it is a documented, user-accepted trade-off (the plan and `breakages.md` catalog the downstream service breakage).

### `__init__.py` exports

`shared/models/__init__.py` imports and re-exports exactly the 17 classes — `Usuario, RawData, InstrumentoProcesado, MetadatosDC, MetadatosEnriquecidosEncuestas, MetadatosEnriquecidosEntrevistas, MetadatosEnriquecidosPruebas, ColeccionVectorial, Prompt, KPI, Variable, KPIVariable, KPIInferido, ValorVariableInferido, RagLog, DocumentoVectorizado, KpiInferidoChunk` — with `__all__` matching and no dangling imports of deleted modules. `MetadatosEnriquecidosPruebas` is imported from `metadatos_pruebasestandarizadas` (file kept, class/table renamed), as intended.

### DTO surface

`shared/schemas/__init__.py` exposes `UsuarioRead`, `InstrumentoRead`, `MetadatosDCBase`, `KPIRead`. Each field is a subset of its SQL table's columns with correct optionality (`email` required, `rol` optional on Usuario; `estado` required, timestamps optional on Instrumento; `nombre_kpi` required on KPI). `MetadatosDCBase` keeps its exact name and all 13 DC fields with only `dc_title` required. No invented fields.

### SQL source of truth unmodified

`01_schema.sql` shows a diff against `HEAD`, but that is a pre-existing working-tree change: the file's on-disk `LastWriteTime` (09:47) predates every file the coder wrote for this task (10:06–10:08) by ~20 minutes, and it belongs to the broader uncommitted refactor (the `01_schema_BACKUP.sql` move, etc.). The coder did not touch it during this task. The models were verified against the current on-disk SQL content.

### Verification evidence (not re-run)

Per the task, the coder's smoke test, `compileall`, and metadata gate were not re-run. The recorded evidence in `verification.md` shows the import test listing exactly the 17 table names, `compileall` exit 0, and the final gate asserting `len(tables)==17` with `__all__` and the DTO field sets matching. The 17-table smoke-test list in the evidence is correct and matches the SQL. No articulable doubt required a spot-check beyond the per-model reads above (which I did directly).

### Not tested

- No live `CREATE TABLE`/migration run against a real Postgres (plan notes there is no DB in CI); FK/CHECK DDL emission is assumed from SQLAlchemy metadata, not executed.
- `server_default` SQL emission (`func.now()`, `text("'{}'::jsonb")`) is cosmetic for ORM behavior and was not asserted against generated DDL.

</details>

<details>
<summary>File map</summary>

- `shared/models/*.py` — 17 ORM models rewritten/created to mirror the SQL; `__init__.py` exports the 17 classes.
- `shared/schemas/__init__.py` — 4 realigned Pydantic DTOs; 14 legacy loose modules deleted.
- `shared/repositories/__init__.py` — empty package marker; 6 unsalvageable repos deleted.
- `shared/models/{institucion,permiso_instrumento,pregunta_kpi,valor_variable}.py` — deleted (no SQL table).
- `infrastructure/postgres/init/01_schema.sql` — source of truth, unmodified by this task.

</details>
