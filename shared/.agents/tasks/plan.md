# Implementation Plan — Realign `shared/` to `01_schema.sql`

Source of truth (READ-ONLY, NEVER EDIT): `infrastructure/postgres/init/01_schema.sql`
Target package: `shared/`
Workspace root: `c:\Users\yarel\Documents\indagata\indagata`

## Context discovered during exploration

- `shared/db/base.py` defines `SCHEMA = "tt_rag"` and a single `Base(DeclarativeBase)`. Every model inherits `Base` and sets `__table_args__ = {"schema": SCHEMA}` (merged with constraints where needed). Do NOT change `base.py`.
- The current models in `shared/models/` describe an OLD, different data model (wrong table names like `usuarios`, `prompt`, `metadatos_enriquecidos_pruebas_estandarizadas`; phantom tables `instituciones`, `permiso_instrumento`, `pregunta_kpi`, `valor_variable`; surrogate PKs where the SQL uses composite PKs; many extra columns not in the SQL).
- The SQL comment header mentions names like `collection_id` and `chunk_id`, but the actual DDL declares `coleccion_id` and `chroma_vector_id`. ALWAYS follow the DDL, never the comment.
- Build/verify toolchain: Python 3.14 venv at `.\.venv\`. `sqlalchemy==2.0.x`, `pydantic==2.x` installed. There is NO test framework and NO test suite in the repo. Verification is import/metadata smoke tests run from the repo root with `.\.venv\Scripts\python.exe`.
- Repositories currently import from `app.models.*` / `app.schemas.*` (a package that does not exist at repo root), so `shared.repositories.*` fails to import today (`ModuleNotFoundError: No module named 'app'`).
- Loose schema modules in `shared/schemas/` (e.g. `instrumento_procesado.py`, `kpi.py`, `raw_data.py`, ...) are legacy. A repo-wide grep for `shared.schemas.<module>` finds ZERO importers (the only hit is a docstring in `shared/__init__.py` referencing a non-existent `shared.schemas.instrumento`). Only the package-level `shared.schemas` symbols are imported downstream: `analysis-service/app/schemas.py` does `from shared.schemas import MetadatosDCBase`.
- Downstream active services (`services/analysis-service`, `services/instrument-service`) are coupled to the OLD model. Per the task, do NOT edit service files; realign `shared/` to the SQL and REPORT every expected breakage (collected in the final step).
- Column type mapping convention (from SQL): `SERIAL PK` -> `mapped_column(primary_key=True, autoincrement=True)` (SQLAlchemy emits SERIAL/IDENTITY on PostgreSQL); `INTEGER` -> `Integer`; `VARCHAR(n)` -> `String(n)`; `TEXT` -> `Text`; `BOOLEAN` -> `Boolean`; `NUMERIC` -> `Numeric`; `JSONB` -> `from sqlalchemy.dialects.postgresql import JSONB`; `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` -> `mapped_column(server_default=func.now())`; nullable column -> `Mapped[T | None]` without `nullable=False`.
- FK convention: `ForeignKey(f"{SCHEMA}.<table>.<col>", ondelete="<...>")`. Composite PKs: mark each member `primary_key=True`. Composite FKs: use `ForeignKeyConstraint([...], [f"{SCHEMA}.<t>.<c>", ...], ondelete="...")` inside `__table_args__` tuple together with `{"schema": SCHEMA}` as the LAST element.
- CHECK on `estado`: `CheckConstraint("estado IN ('recibido','limpieza_en_proceso','limpio','metadatos_registrados','estandarizado','vectorizado','error')", name="ck_instrumento_estado")` in `__table_args__`.

Baseline verification (run from repo root `c:\Users\yarel\Documents\indagata\indagata`):
```
.\.venv\Scripts\python.exe -c "import shared.models; from shared.db.base import Base; print(sorted(Base.metadata.tables.keys()))"
```
After realignment this MUST list EXACTLY these 17 tables (schema-qualified):
`tt_rag.usuario, tt_rag.raw_data, tt_rag.instrumento_procesado, tt_rag.metadatos_dc, tt_rag.metadatos_enriquecidos_encuestas, tt_rag.metadatos_enriquecidos_entrevistas, tt_rag.metadatos_enriquecidos_pruebas, tt_rag.coleccion_vectorial, tt_rag.prompts, tt_rag.kpi, tt_rag.variable, tt_rag.kpi_variable, tt_rag.kpi_inferido, tt_rag.valor_variable_inferido, tt_rag.rag_log, tt_rag.documento_vectorizado, tt_rag.kpi_inferido_chunk` — and NO others (no `usuarios`, `prompt`, `instituciones`, `permiso_instrumento`, `pregunta_kpi`, `valor_variable`, `metadatos_enriquecidos_pruebas_estandarizadas`).

---

## Plan

- [ ] 1. Rewrite `usuario.py` to table `usuario`.
      Class `Usuario`, `__tablename__ = "usuario"`. Columns: `usuario_id` (SERIAL PK), `nombre String(255) NOT NULL`, `email String(255) UNIQUE NOT NULL`, `password_hash Text NOT NULL`, `rol String(50)` nullable, `fecha_registro` TIMESTAMP server_default now. Remove old `usuario`/`creado_en` fields. Update `__repr__` to use `nombre`.
      Files: `shared/models/usuario.py`
      Verify: deferred to the package import smoke test in step 18 (each model step leaves a syntactically valid module; full metadata check runs once at the end).

- [ ] 2. Rewrite `raw_data.py` to the PARENT table `raw_data`.
      Class `RawData`, `__tablename__ = "raw_data"`. Columns: `id_crudo` (SERIAL PK), `id_owner Integer NOT NULL` FK `f"{SCHEMA}.usuario.usuario_id"` ondelete `CASCADE`, `tipo_instrumento String(50) NOT NULL`, `nombre_archivo Text NOT NULL`, `raw_archivo Text NOT NULL`, `raw_archivo_original Text` nullable, `fecha_carga` TIMESTAMP server_default now. Remove ALL old columns (`raw_data_id`, `instrumento_id`, `usuario_id`, `subido`, `rol_archivo`, `nombre_original`, `tipo_mime`, `tamano_bytes`, `hash_md5`). Update `__repr__`.
      Files: `shared/models/raw_data.py`
      Verify: deferred to step 18.

- [ ] 3. Rewrite `instrumento_procesado.py` to table `instrumento_procesado`.
      Class `InstrumentoProcesado`. Columns: `id_instrumento` (SERIAL PK), `id_crudo Integer NOT NULL` FK `f"{SCHEMA}.raw_data.id_crudo"` ondelete `CASCADE`, `ruta_de_archivo_limpio String(255)` nullable, `ruta_json Text` nullable, `estado String(50) NOT NULL default 'recibido'`, `fecha_procesamiento` TIMESTAMP server_default now, `fecha_aprobado TIMESTAMP` nullable. Add `__table_args__ = (CheckConstraint(estado IN (...), name="ck_instrumento_estado"), {"schema": SCHEMA})`. Remove old columns (`instrumento_id`, `nombre`, `tipo_instrumento`, `plataforma`, `ruta_sav`, `ruta_texto_limpio`, `version`, `schema_version`, `error_detalle`, `creado_en`). Update `__repr__` to use `id_instrumento`/`estado`.
      Files: `shared/models/instrumento_procesado.py`
      Verify: deferred to step 18.

- [ ] 4. Rewrite `metadatos_dc.py` to table `metadatos_dc` (child of raw_data).
      Class `MetadatosDC`. PK = FK: `id_crudo Integer` `ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE")`, `primary_key=True`. Columns per SQL: `dc_title Text NOT NULL`, `dc_creator Text`, `dc_description Text`, `dc_type String(50)`, `dc_date String(100)`, `dc_language String(10)`, `dc_coverage Text`, `dc_subject Text`, `dc_publisher Text`, `dc_rights String(255)`, `dc_format String(50)`, `dc_source Text`, `dc_relation Text`. Remove `instrumento_id` PK and the `registrado_en` column. Fix the types that were wrong in the old model (`dc_date` was Text -> String(100); `dc_rights` String(50) -> String(255); `dc_format` String(20) -> String(50); `dc_relation` String(255) -> Text; `dc_title` nullable -> NOT NULL).
      Files: `shared/models/metadatos_dc.py`
      Verify: deferred to step 18.

- [ ] 5. Rewrite `metadatos_encuestas.py` to table `metadatos_enriquecidos_encuestas`.
      Class `MetadatosEnriquecidosEncuestas` (keep name). PK=FK `id_crudo` -> `raw_data.id_crudo` ondelete CASCADE. Columns per SQL: `n_respondentes Integer`, `n_poblacion Integer`, `carrera Text`, `poblacion_objetivo Text`, `notas_contextuales Text`, `notas_interpretacion Text`. Remove old columns (`instrumento_id`, `tipo_investigacion`, `constructo_principal`, `dimensiones`, `palabras_clave`) and drop the JSONB import.
      Files: `shared/models/metadatos_encuestas.py`
      Verify: deferred to step 18.

- [ ] 6. Rewrite `metadatos_entrevistas.py` to table `metadatos_enriquecidos_entrevistas`.
      Class `MetadatosEnriquecidosEntrevistas` (keep name). PK=FK `id_crudo` -> `raw_data.id_crudo` ondelete CASCADE. Columns per SQL: `identificador_propio Text`, `objetivo Text`, `metodologia Text`, `institucion Text`, `derechos Text`. Remove old columns (`instrumento_id`, `num_entrevistas`, `duracion_min`, `guion`); drop the `Integer` import if unused.
      Files: `shared/models/metadatos_entrevistas.py`
      Verify: deferred to step 18.

- [ ] 7. Rewrite `metadatos_pruebasestandarizadas.py` to table `metadatos_enriquecidos_pruebas`.
      Rename class to `MetadatosEnriquecidosPruebas` and set `__tablename__ = "metadatos_enriquecidos_pruebas"`. PK=FK `id_crudo` -> `raw_data.id_crudo` ondelete CASCADE. Columns per SQL: `unidad_de_aprendizaje Text`, `mapeo_de_reactivos_por_seccion JSONB` (use `from sqlalchemy.dialects.postgresql import JSONB`), `institucion Text`, `campus Text`, `grado Text`, `grupo Text`, `ciclo_escolar Text`, `tipo_de_prueba Text`, `version Text`, `taxonomia_bloom Text`, `nivel_educativo Text`, `objetivo_de_evaluacion Text`, `subareas Text`, `competencias Text`. Remove old columns (`instrumento_id`, `aplicantes`) and add the ones that were missing (`grupo`, `nivel_educativo`, `subareas`, `competencias`); `mapeo_de_reactivos_por_seccion` was Text -> JSONB. (Keep the file name `metadatos_pruebasestandarizadas.py`; only the class name and table name change — the `__init__` import path is updated in step 15.)
      Files: `shared/models/metadatos_pruebasestandarizadas.py`
      Verify: deferred to step 18.

- [ ] 8. Create `coleccion_vectorial.py` (NEW table `coleccion_vectorial`).
      Class `ColeccionVectorial`. Columns per SQL: `coleccion_id` (SERIAL PK), `nombre Text UNIQUE NOT NULL`, `embedding_model String(100)`, `chunk_size Integer`, `chunk_overlap Integer`, `creado_en` TIMESTAMP server_default now. `__table_args__ = {"schema": SCHEMA}`.
      Files: `shared/models/coleccion_vectorial.py`
      Verify: deferred to step 18.

- [ ] 9. Rewrite `prompt.py` to table `prompts`.
      Class `Prompt`, `__tablename__ = "prompts"`. Columns per SQL: `prompt_id` (SERIAL PK), `tipo String(50) NOT NULL`, `version String(10) NOT NULL`, `contenido Text NOT NULL`, `coleccion_id Integer` FK `f"{SCHEMA}.coleccion_vectorial.coleccion_id"` ondelete `SET NULL` (nullable), `activo Boolean default True`, `creado_en` TIMESTAMP server_default now. DROP the old `UniqueConstraint("tipo","version")` (not in SQL) so `__table_args__ = {"schema": SCHEMA}`. Remove old columns (`fecha`); `version` becomes NOT NULL.
      Files: `shared/models/prompt.py`
      Verify: deferred to step 18.

- [ ] 10. Rewrite `kpi.py` to table `kpi`.
      Class `KPI` (keep name). Columns per SQL: `kpi_id` (SERIAL PK), `nombre_kpi Text NOT NULL`, `descripcion Text`, `categoria Text`, `ambito Text`, `url_documentacion Text`, `formula Text`. Remove ALL old columns not in SQL (`nombrekpi`, `direccion_deseada`, `razon`, `umbral_bajo`, `umbral_medio`, `umbral_alto`, `unidad`, `activo`). NOTE: the attribute is now `nombre_kpi` (not `nombrekpi`) and there is no `activo` — these drive downstream breakage reports in step 20. Update `__repr__` to use `nombre_kpi`. Drop unused imports (`Boolean`, `Numeric`, `String` if unused).
      Files: `shared/models/kpi.py`
      Verify: deferred to step 18.

- [ ] 11. Rewrite `variable.py` to table `variable`.
      Class `Variable` (keep name). Columns per SQL: `variable_id` (SERIAL PK), `nombre_variable Text NOT NULL`, `descripcion Text`, `tipo_dato String(20)`, `unidad Text`. Remove old columns (`nombre_display`); `nombre_variable` was String(255)+unique -> Text (no UNIQUE in SQL); `unidad` String(20) -> Text; `tipo_dato` String(30) NOT NULL -> String(20) nullable. Import `Text` and `String`.
      Files: `shared/models/variable.py`
      Verify: deferred to step 18.

- [ ] 12. Verify/keep `kpi_variable.py` (table `kpi_variable`).
      Class `KPIVariable` (keep name). Composite PK `(kpi_id, variable_id)`: `kpi_id Integer` FK `f"{SCHEMA}.kpi.kpi_id"` ondelete `CASCADE` `primary_key=True`; `variable_id Integer` FK `f"{SCHEMA}.variable.variable_id"` ondelete `CASCADE` `primary_key=True`. Add `ondelete="CASCADE"` to both FKs (SQL has it; current model omits it). Keep `__table_args__ = {"schema": SCHEMA}`.
      Files: `shared/models/kpi_variable.py`
      Verify: deferred to step 18.

- [ ] 13. Rewrite `kpi_inferido.py` to the composite-PK table `kpi_inferido`.
      Class `KPIInferido` (keep name). Composite PK `(id_procesado, kpi_id)`: `id_procesado Integer` FK `f"{SCHEMA}.instrumento_procesado.id_instrumento"` ondelete `CASCADE` `primary_key=True`; `kpi_id Integer` FK `f"{SCHEMA}.kpi.kpi_id"` ondelete `CASCADE` `primary_key=True`. Columns per SQL: `razon Text`, `resultado Numeric`, `fecha_inferencia` TIMESTAMP server_default now. DROP surrogate `kpi_inferido_id`, the `UniqueConstraint`, and all old columns (`instrumento_id`, `score_similitud`, `tipo_relacion`, `estado_decision`, `origen`, `evidencia_textual`, `registrado_en`, `decidido_en`). `__table_args__ = {"schema": SCHEMA}`.
      Files: `shared/models/kpi_inferido.py`
      Verify: deferred to step 18.

- [ ] 14. Create `valor_variable_inferido.py` (NEW table `valor_variable_inferido`).
      Class `ValorVariableInferido`. Composite PK `(id_procesado, kpi_id, variable_id)`. Columns: `id_procesado Integer NOT NULL primary_key`, `kpi_id Integer NOT NULL primary_key`, `variable_id Integer NOT NULL primary_key` FK `f"{SCHEMA}.variable.variable_id"` ondelete `CASCADE`, `valor_numerico Numeric`, `valor_texto Text`, `valor_booleano Boolean`, `confianza_variable Numeric`. Composite FK via `ForeignKeyConstraint(["id_procesado", "kpi_id"], [f"{SCHEMA}.kpi_inferido.id_procesado", f"{SCHEMA}.kpi_inferido.kpi_id"], ondelete="CASCADE")`. `__table_args__ = (ForeignKeyConstraint(...), {"schema": SCHEMA})`.
      Files: `shared/models/valor_variable_inferido.py`
      Verify: deferred to step 18.

- [ ] 15. Create `kpi_inferido_chunk.py` (NEW table `kpi_inferido_chunk`).
      Class `KpiInferidoChunk`. Composite PK `(id_procesado, kpi_id, documento_vectorizado_id)`. Columns: `id_procesado Integer NOT NULL primary_key`, `kpi_id Integer NOT NULL primary_key`, `documento_vectorizado_id Integer NOT NULL primary_key` FK `f"{SCHEMA}.documento_vectorizado.documento_vectorizado_id"` ondelete `CASCADE`, `score Numeric`. Composite FK via `ForeignKeyConstraint(["id_procesado", "kpi_id"], [f"{SCHEMA}.kpi_inferido.id_procesado", f"{SCHEMA}.kpi_inferido.kpi_id"], ondelete="CASCADE")`. `__table_args__ = (ForeignKeyConstraint(...), {"schema": SCHEMA})`. (Depends on step 16 declaring `documento_vectorizado`; ordering in `__init__` handled in step 17.)
      Files: `shared/models/kpi_inferido_chunk.py`
      Verify: deferred to step 18.

- [ ] 16. Rewrite `rag_log.py` to table `rag_log`.
      Class `RagLog` (keep name). Columns per SQL: `rag_log_id` (SERIAL PK), `pregunta Text NOT NULL`, `respuesta Text`, `modelo_usado String(100)`, `chunks_usados Integer`, `latencia_ms Integer`, and a column literally named `timestamp` (`timestamp: Mapped[datetime] = mapped_column("timestamp", server_default=func.now())` — map the Python attribute to the DB column `timestamp`; do NOT rename it to `fecha`). Remove old columns (`contexto`, `modelo_llm`, `modelo_embedding`, `fecha`). Keep `datetime` import.
      Files: `shared/models/rag_log.py`
      Verify: deferred to step 18.

- [ ] 17. Rewrite `documento_vectorizado.py` to table `documento_vectorizado`.
      Class `DocumentoVectorizado` (keep name). Columns per SQL: `documento_vectorizado_id` (SERIAL PK), `instrumento_id Integer` FK `f"{SCHEMA}.instrumento_procesado.id_instrumento"` ondelete `CASCADE` (nullable — SQL has no NOT NULL), `coleccion_id Integer` FK `f"{SCHEMA}.coleccion_vectorial.coleccion_id"` ondelete `SET NULL` (nullable), `chroma_vector_id Text` nullable, `chunk_index Integer`, `seccion Text`, `chunk_texto Text NOT NULL`, `chunk_metadata JSONB default '{}'::jsonb` (use `mapped_column(JSONB, server_default=text("'{}'::jsonb"))` with `from sqlalchemy import text`), `n_tokens Integer`, `almacenado_en` TIMESTAMP server_default now. Remove old columns (`prompt_id`, `vector_id`, `col_id`, `tipo_chunk`, `texto_chunk`, `embedding_modelo`, `activo`, `fecha_vectorizacion`).
      Files: `shared/models/documento_vectorizado.py`
      Verify: deferred to step 18.

- [ ] 18. DELETE the four models with no table in the SQL and rewrite `shared/models/__init__.py`.
      Delete files `shared/models/institucion.py`, `shared/models/permiso_instrumento.py`, `shared/models/pregunta_kpi.py`, `shared/models/valor_variable.py`. Rewrite `__init__.py` to import, in dependency-safe order, and re-export EXACTLY: `Usuario, RawData, InstrumentoProcesado, MetadatosDC, MetadatosEnriquecidosEncuestas, MetadatosEnriquecidosEntrevistas, MetadatosEnriquecidosPruebas, ColeccionVectorial, Prompt, KPI, Variable, KPIVariable, KPIInferido, ValorVariableInferido, RagLog, DocumentoVectorizado, KpiInferidoChunk`. Import `MetadatosEnriquecidosPruebas` from `shared.models.metadatos_pruebasestandarizadas`; import `ColeccionVectorial` from `shared.models.coleccion_vectorial`, `ValorVariableInferido` from `shared.models.valor_variable_inferido`, `KpiInferidoChunk` from `shared.models.kpi_inferido_chunk`. Remove imports of the four deleted modules. Set `__all__` to exactly those 17 names (no `Institucion`, `PermisoInstrumento`, `PreguntaKPI`, `ValorVariable`, no old `MetadatosEnriquecidosPruebasEstandarizadas`).
      Files: `shared/models/__init__.py` (+ delete the four model files)
      Verify (from repo root):
      ```
      .\.venv\Scripts\python.exe -c "import shared.models as m; from shared.db.base import Base; print(sorted(Base.metadata.tables.keys())); print(sorted(m.__all__))"
      ```
      Expect the 17 schema-qualified table names listed in the Context section (and no others), and `__all__` equal to the 17 class names above. This is the primary metadata gate for steps 1–17.

- [ ] 19. Realign the package-level Pydantic DTOs in `shared/schemas/__init__.py`.
      Fix `UsuarioRead` to SQL-aligned fields: `usuario_id: int`, `nombre: str`, `email: str`, `rol: str | None = None` (remove the `usuario` field; `email` is NOT NULL in SQL). Rewrite `InstrumentoRead` to only SQL columns of `instrumento_procesado`: `id_instrumento: int`, `id_crudo: int`, `ruta_de_archivo_limpio: str | None = None`, `ruta_json: str | None = None`, `estado: str`, `fecha_procesamiento: datetime | None = None`, `fecha_aprobado: datetime | None = None` (drop `instrumento_id`, `nombre`, `tipo_instrumento`, `plataforma`, `ruta_sav`, `ruta_texto_limpio`, `version`, `schema_version`, `error_detalle`, `creado_en`). Keep `MetadatosDCBase` EXACTLY as named (analysis-service imports it) with the 13 DC fields and `dc_title` required — verify it already matches the SQL (it does). Fix `KPIRead` to: `kpi_id: int`, `nombre_kpi: str`, `descripcion: str | None = None`, `categoria: str | None = None`, `ambito: str | None = None`, `url_documentacion: str | None = None`, `formula: str | None = None` (replace `nombrekpi`, `direccion_deseada`, `unidad`). Keep `__all__ = ["UsuarioRead", "InstrumentoRead", "MetadatosDCBase", "KPIRead"]`. Also fix the stale docstring example in `shared/__init__.py` that references the non-existent `shared.schemas.instrumento` (point it at `from shared.schemas import InstrumentoRead`).
      Files: `shared/schemas/__init__.py`, `shared/__init__.py`
      Verify (from repo root):
      ```
      .\.venv\Scripts\python.exe -c "import shared.schemas as s; print(sorted(s.__all__)); print(s.KPIRead.model_fields.keys()); print(s.UsuarioRead.model_fields.keys()); print(s.InstrumentoRead.model_fields.keys())"
      ```
      Expect the four DTO names and the SQL-aligned field sets above.

- [ ] 20. DELETE the unused legacy loose schema modules in `shared/schemas/`.
      Grep confirmed ZERO importers of `shared.schemas.<module>` anywhere in the repo (only package-level `shared.schemas` symbols are imported). Delete: `shared/schemas/instrumento_procesado.py`, `kpi.py`, `kpi_inferido.py`, `metadatos_dc.py`, `metadatos_encuestas.py`, `metadatos_entrevistas.py`, `metadatos_pruebasestandarizadas.py`, `pregunta_kpi.py`, `prompt.py`, `rag_log.py`, `raw_data.py`, `usuario.py`, `variable.py`, `documento_vectorizado.py`. (All are legacy monolith DTOs with no table/field alignment to the SQL and no importers; the authoritative DTOs live in `shared/schemas/__init__.py`.) Before deleting, re-run the grep to confirm no importer appeared:
      ```
      Get-ChildItem -Recurse -File -Filter *.py c:\Users\yarel\Documents\indagata\indagata | Where-Object { $_.FullName -notmatch '\\.venv\\|__pycache__' } | Select-String -Pattern 'shared\.schemas\.'
      ```
      If any match other than a docstring is found for a given module, KEEP that module and record it in step 22.
      Files: delete the 14 listed modules under `shared/schemas/`.
      Verify (from repo root): `.\.venv\Scripts\python.exe -c "import shared.schemas; print('schemas OK')"` and the step-19 command still pass.

- [ ] 21. Realign the repositories in `shared/repositories/` to `shared.*` and SQL-aligned attributes; delete the unsalvageable ones.
      For every repo, change `from app.models.*`/`from app.schemas.*` to the correct `shared.*` source (ORM from `shared.models`, DTOs from `shared.schemas`). Then reconcile against the SQL:
      - `pregunta_kpi_repository.py`: DELETE — no `pregunta_kpi` table exists in the SQL (and `shared.models.pregunta_kpi` is removed in step 18). Record removal in step 22.
      - `instrumento_repository.py`: references `.id_instrumento` (OK — matches SQL) but also `.hash_md5` (NOT in SQL) and imports `app.models.instrumento`/`app.schemas.instrumento` and `InstrumentoCreate/InstrumentoUpdate` DTOs that no longer exist. Delete the `get_by_hash` method (no `hash_md5` column). Keep `get_by_id` (filter on `InstrumentoProcesado.id_instrumento`), `create`, `update`, `delete`, but they depend on `InstrumentoCreate/InstrumentoUpdate` DTOs that are being removed. Since no DTOs remain for create/update, DELETE `instrumento_repository.py` entirely (unsalvageable without inventing DTOs/columns) and record it in step 22. Do NOT invent columns or DTOs.
      - `kpi_repository.py`: references `.activo` (NOT in SQL `kpi`) and `KPI.id_kpi` (actual PK is `kpi_id`), and `KPICreate/KPIUpdate` DTOs that are being removed. DELETE `kpi_repository.py` (unsalvageable) and record in step 22.
      - `prompt_repository.py`: `get_active_by_type` uses `Prompt.activo` (exists in SQL `prompts`) — salvageable — but depends on `PromptCreate` DTO being removed. DELETE `prompt_repository.py` (its `create_new_version` needs a DTO that no longer exists) OR, if preferred, keep only methods that need no DTO; given both methods need a DTO or are trivial, DELETE and record in step 22.
      - `rag_log_repository.py`: uses `RagLog.fecha` (SQL column is `timestamp`) and `RagLogCreate` DTO (removed). DELETE and record in step 22.
      - `documento_vectorizado_repository.py`: uses `.id_instrumento` (SQL FK column is `instrumento_id`), `.activo` (NOT in SQL), and `DocumentoVectorizadoCreate` DTO (removed). DELETE and record in step 22.
      Net result: with the loose schema DTOs removed in step 20, ALL current repositories are unsalvageable (each needs a removed Create/Update DTO or references a non-existent column), so DELETE all six repository modules. Leave `shared/repositories/` with only a minimal `__init__.py` if one is needed for import; check whether `shared/repositories/__init__.py` exists — the directory currently has NO `__init__.py`, so after deleting the six modules the directory may be empty. Create an empty `shared/repositories/__init__.py` so `shared.repositories` remains importable (the smoke test in step 23 imports it). Record in step 22 that the entire repository layer was removed as unsalvageable against the SQL (no DTOs/columns to back it) and that services needing persistence helpers must define their own against the realigned models.
      Files: delete `shared/repositories/{pregunta_kpi_repository,instrumento_repository,kpi_repository,prompt_repository,rag_log_repository,documento_vectorizado_repository}.py`; create `shared/repositories/__init__.py` (empty, with a short module docstring).
      Verify (from repo root): `.\.venv\Scripts\python.exe -c "import shared.repositories; print('repositories OK')"` imports cleanly (no `ModuleNotFoundError: app`).

- [ ] 22. Write the downstream-breakage report to `shared/.agents/tasks/breakages.md`.
      Produce a markdown report (do NOT edit any service file) listing every downstream reference expected to break because its table/column/class is not in the SQL. Must include at minimum:
      - `services/instrument-service/app/service.py` imports `PermisoInstrumento` (no such table) — import will raise `ImportError`; also constructs `InstrumentoProcesado(nombre=..., tipo_instrumento=..., plataforma=..., estado=...)` and uses `.instrumento_id`, `RawData(instrumento_id=..., rol_archivo=..., nombre_original=..., tamano_bytes=..., hash_md5=...)` — none of those columns exist in the realigned models.
      - `services/instrument-service/app/routers/upload.py` uses `InstrumentoProcesado` with old attributes.
      - `services/analysis-service/app/service.py` imports `MetadatosEnriquecidosPruebasEstandarizadas` (renamed to `MetadatosEnriquecidosPruebas`) — `ImportError`; uses `MetadatosDC(instrumento_id=...)` (now PK is `id_crudo`), `inst.nombre`, `inst.ruta_texto_limpio`, `inst.tipo_instrumento`, `KPIInferido.instrumento_id`, `KPIInferido.score_similitud`, `KPI.nombrekpi` (now `nombre_kpi`) — all break.
      - `services/analysis-service/app/kpi_search.py` uses `KPI.nombrekpi`, `KPI.direccion_deseada`, `KPI.activo`, `KPI.unidad` — none exist in realigned `KPI`.
      - `services/analysis-service/app/storage.py` uses `RawData.instrumento_id`, `RawData.rol_archivo`, `RawData.raw_data_id` — none exist (SQL `raw_data` has `id_crudo`, `id_owner`, `raw_archivo`, ...).
      - `services/analysis-service/app/dependencies.py` and `services/instrument-service/app/dependencies.py` import `Usuario` (still exists) but `Usuario` no longer has `.usuario`/`.creado_en`.
      - The entire `shared/repositories/` layer was deleted (unsalvageable); any service importing `shared.repositories.*` would break (grep found none today).
      - Classes/tables removed with no SQL table: `PermisoInstrumento`, `PreguntaKPI`, `Institucion`, `ValorVariable`, and schema class `MetadatosEnriquecidosPruebasEstandarizadas` (renamed).
      - Note that `services/services_que_estaban_en_backend/*` is legacy/dead code importing from a different `api.*`/`app.*` package and is NOT part of the active shared contract; list it as out-of-scope but flag it references `PermisoInstrumento`, `nombrekpi`, etc.
      Files: `shared/.agents/tasks/breakages.md`
      Verify: file exists and enumerates each item above. (`Test-Path shared\.agents\tasks\breakages.md`.)

- [ ] 23. Full package import + metadata gate (final verification).
      Run from repo root `c:\Users\yarel\Documents\indagata\indagata`:
      ```
      .\.venv\Scripts\python.exe -c "import shared.models, shared.schemas, shared.repositories; from shared.db.base import Base; t=sorted(Base.metadata.tables.keys()); assert len(t)==17, t; print('tables', t); import shared.models as m; print('all', sorted(m.__all__))"
      ```
      Expected outcome: process exits 0; exactly 17 tables, matching the schema-qualified names in the Context section; `shared.models.__all__` equals the 17 class names from step 18; `shared.schemas` and `shared.repositories` import without error. If any assertion fails or any import raises, fix the offending model/schema/__init__ before marking complete. (This replaces grep-based checks; it exercises the real SQLAlchemy metadata and Pydantic model construction.)
      Files: none (verification only)
      Verify: command above exits 0 with the expected table/class lists.

- [ ] 24. Write the review verdict file.
      When steps 1–23 pass with no blocking findings, write `shared/.agents/tasks/review.json` containing `{"verdict": "APPROVED"}`. If any blocking finding remains, write `{"verdict": "CHANGES_REQUESTED"}` with a short note. (This is the workflow loop's stop contract — same file/field/value must be preserved.)
      Files: `shared/.agents/tasks/review.json`
      Verify: `Test-Path shared\.agents\tasks\review.json` is True and the JSON `verdict` field is set.

## Assumptions and notes

- `chunk_metadata JSONB DEFAULT '{}'::jsonb` is reflected with `server_default=text("'{}'::jsonb")`; this is cosmetic for ORM behavior but keeps the model faithful to the SQL for `init_db()`/`create_all`.
- The SQL `rag_log` column is literally named `timestamp`; the model maps a Python attribute (named `timestamp`) to that DB column explicitly to avoid shadowing issues and to stay 1:1 with the SQL.
- The entire repository layer is deleted because, after removing the unused legacy DTO modules (which nothing imports), every repository depends on a removed Create/Update DTO or references a column absent from the SQL. The task explicitly authorizes deleting unsalvageable repos and reporting them; it also forbids inventing columns. Services that need persistence helpers should build them against the realigned models in their own package.
- Service files are intentionally NOT edited (per the task). All resulting breakages are catalogued in `breakages.md` for the user to triage. This realignment makes `shared/` a faithful 1:1 mirror of `01_schema.sql` and keeps the `shared` package importable; it does NOT keep the downstream services runnable, which is the explicit, user-accepted trade-off of making the SQL the single source of truth.
