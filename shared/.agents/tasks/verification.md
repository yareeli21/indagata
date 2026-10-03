# Verification note — `shared/` realigned to `01_schema.sql`

Iteration: FIRST (no prior `review.json`). Source of truth read in full:
`infrastructure/postgres/init/01_schema.sql` (NOT modified).

## Commands run (from repo root `c:\Users\yarel\Documents\indagata\indagata`)

### 1. Import smoke test (17-table gate)
```
.\.venv\Scripts\python.exe -c "import shared.models as m; from shared.db.base import Base; print(sorted(t.name for t in Base.metadata.sorted_tables))"
```
Output:
```
['coleccion_vectorial', 'documento_vectorizado', 'instrumento_procesado', 'kpi', 'kpi_inferido', 'kpi_inferido_chunk', 'kpi_variable', 'metadatos_dc', 'metadatos_enriquecidos_encuestas', 'metadatos_enriquecidos_entrevistas', 'metadatos_enriquecidos_pruebas', 'prompts', 'rag_log', 'raw_data', 'usuario', 'valor_variable_inferido', 'variable']
```
Exactly the 17 SQL table names. Exit 0.

### 2. Byte-compile
```
.\.venv\Scripts\python.exe -m compileall shared -q
```
Exit 0. No SyntaxErrors.

### 3. Final package + metadata gate
```
.\.venv\Scripts\python.exe -c "import shared.models, shared.schemas, shared.repositories; from shared.db.base import Base; t=sorted(Base.metadata.tables.keys()); assert len(t)==17, t; ..."
```
Output:
```
tables ['tt_rag.coleccion_vectorial', 'tt_rag.documento_vectorizado', 'tt_rag.instrumento_procesado', 'tt_rag.kpi', 'tt_rag.kpi_inferido', 'tt_rag.kpi_inferido_chunk', 'tt_rag.kpi_variable', 'tt_rag.metadatos_dc', 'tt_rag.metadatos_enriquecidos_encuestas', 'tt_rag.metadatos_enriquecidos_entrevistas', 'tt_rag.metadatos_enriquecidos_pruebas', 'tt_rag.prompts', 'tt_rag.rag_log', 'tt_rag.raw_data', 'tt_rag.usuario', 'tt_rag.valor_variable_inferido', 'tt_rag.variable']
all ['ColeccionVectorial', 'DocumentoVectorizado', 'InstrumentoProcesado', 'KPI', 'KPIInferido', 'KPIVariable', 'KpiInferidoChunk', 'MetadatosDC', 'MetadatosEnriquecidosEncuestas', 'MetadatosEnriquecidosEntrevistas', 'MetadatosEnriquecidosPruebas', 'Prompt', 'RagLog', 'RawData', 'Usuario', 'ValorVariableInferido', 'Variable']
schemas_all ['InstrumentoRead', 'KPIRead', 'MetadatosDCBase', 'UsuarioRead']
KPIRead ['kpi_id', 'nombre_kpi', 'descripcion', 'categoria', 'ambito', 'url_documentacion', 'formula']
UsuarioRead ['usuario_id', 'nombre', 'email', 'rol']
InstrumentoRead ['id_instrumento', 'id_crudo', 'ruta_de_archivo_limpio', 'ruta_json', 'estado', 'fecha_procesamiento', 'fecha_aprobado']
```
Exit 0. `shared.schemas` and `shared.repositories` import cleanly (no `ModuleNotFoundError: app`).

## Files created
- `shared/models/coleccion_vectorial.py` (ColeccionVectorial)
- `shared/models/valor_variable_inferido.py` (ValorVariableInferido)
- `shared/models/kpi_inferido_chunk.py` (KpiInferidoChunk)
- `shared/repositories/__init__.py` (new, keeps package importable)

## Files rewritten
- `shared/models/usuario.py` (table `usuario`)
- `shared/models/raw_data.py`
- `shared/models/instrumento_procesado.py` (+ CHECK on estado)
- `shared/models/metadatos_dc.py` (FK id_crudo, dropped registrado_en)
- `shared/models/metadatos_encuestas.py`
- `shared/models/metadatos_entrevistas.py`
- `shared/models/metadatos_pruebasestandarizadas.py` (class MetadatosEnriquecidosPruebas, table metadatos_enriquecidos_pruebas)
- `shared/models/prompt.py` (table `prompts`, dropped UniqueConstraint)
- `shared/models/kpi.py`
- `shared/models/variable.py`
- `shared/models/kpi_variable.py` (ondelete CASCADE added)
- `shared/models/kpi_inferido.py` (composite PK)
- `shared/models/rag_log.py` (column literally `timestamp`)
- `shared/models/documento_vectorizado.py`
- `shared/models/__init__.py` (17 imports + __all__)
- `shared/schemas/__init__.py` (UsuarioRead, InstrumentoRead, MetadatosDCBase, KPIRead)
- `shared/__init__.py` (fixed stale docstring example)

## Files deleted
- Models: `institucion.py`, `permiso_instrumento.py`, `pregunta_kpi.py`, `valor_variable.py`
- Loose legacy schemas (no importers): `instrumento_procesado.py`, `kpi.py`,
  `kpi_inferido.py`, `metadatos_dc.py`, `metadatos_encuestas.py`,
  `metadatos_entrevistas.py`, `metadatos_pruebasestandarizadas.py`,
  `pregunta_kpi.py`, `prompt.py`, `rag_log.py`, `raw_data.py`, `usuario.py`,
  `variable.py`, `documento_vectorizado.py`
- Repositories (all unsalvageable): `documento_vectorizado_repository.py`,
  `instrumento_repository.py`, `kpi_repository.py`, `pregunta_kpi_repository.py`,
  `prompt_repository.py`, `rag_log_repository.py`

## Broken downstream service references
See `shared/.agents/tasks/breakages.md` for the full catalog (instrument-service
and analysis-service; `PermisoInstrumento`, `nombrekpi`, old `RawData`/
`InstrumentoProcesado`/`KPIInferido`/`MetadatosDC` columns, etc.). Service files
were intentionally not edited per the task.

## Dependencies
SQLAlchemy 2.x and Pydantic 2.x present in `.venv`. Nothing installed.
