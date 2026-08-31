# Design — Modelo de Conocimiento y Estrategia de Recuperación Semántica

## Overview

This document defines the technical design for implementing the knowledge model and semantic retrieval strategy specified in `requirements.md`. It maps each functional requirement to concrete modules, classes, data structures, and integration points within the existing FastAPI + PostgreSQL + ChromaDB stack.

The design introduces **five new services**, **four new ORM models**, **two new routers**, **one schema extension**, and **one async-migrated core module**. All changes are additive and backwards-compatible with the existing pipeline.

---

## Architecture

The system is structured around three physically separated planes that must never be conflated:

```
┌─────────────────────────────────────────────────────────────────────┐
│  PLANE 1 — OPERATIVE (PostgreSQL)                                    │
│  Pipeline state, file paths, audit logs, user management            │
└──────────────────────────────────────────────────────────────────── ┘

┌─────────────────────────────────────────────────────────────────────┐
│  PLANE 2 — SEMANTIC (JSON files on disk)                            │
│  InstrumentoSemantico: contexto, dublin_core, especifico,           │
│  kpis_inferidos, plan_chunking, unidades_semanticas                 │
└──────────────────────────────────────────────────────────────────── ┘

┌─────────────────────────────────────────────────────────────────────┐
│  PLANE 3 — VECTOR INDEX (ChromaDB — derived from Plane 2)           │
│  contenido_narrativo (document) + embedding + 13 metadata fields    │
│  Regenerable from Plane 2 at any time without data loss             │
└──────────────────────────────────────────────────────────────────── ┘
```

### Pipeline flow

```
EXISTING PIPELINE (unchanged)
  cargar.py → limpieza → metadatos_base → metadatos_enriquecidos
                              ↓
                   estado: "estandarizado"
                              ↓ triggers new stages
NEW PIPELINE STAGES
  kpi_inferencia_service  ←→  OllamaClient (async)
          ↓
  json_canonico_service
          ↓
  chunking_service  ←→  OllamaClient (async)
          ↓
  vectorizacion_service  ←→  ChromaDB + SentenceTransformers
          ↓
  estado: "vectorizado"
          ↓ enables
RAG QUERY LAYER
  rag_service  ←→  ChromaDB (retrieval) + OllamaClient (generation)
       ↓
  rag_log (PostgreSQL audit)
```

### State machine

The instrument pipeline is extended from 5 to 8 states:

```
ingresado → limpio → metadatos_base → estandarizado
    → kpis_inferidos → json_generado → vectorizado
    → error  (from any stage on failure)
```

Each transition is atomic: the service commits to PostgreSQL only after successful completion. On failure, `estado` is set to `"error"` and details are written to `metadatos["error_pipeline"]`.

---

## Components and Interfaces

### Core modules

**`backend/app/core/ollama_client.py`** — REPLACE (sync → async)

```
OllamaClient
  __init__(host: str, model: str, timeout: float = 120.0)

  async enviar_chat(system_prompt: str, historial: list[dict]) -> str
    POST /api/chat, stream=False. Raises OllamaError on failure.

  async enviar_chat_stream(system_prompt: str, historial: list[dict]) -> AsyncGenerator[str]
    POST /api/chat, stream=True. Yields SSE token deltas.

  async generar_json_estructurado(system_prompt: str, schema_hint: str) -> dict
    POST /api/chat with JSON output instruction. Parses and returns dict.
    Raises OllamaError if response is not valid JSON.

# Module-level singleton:
ollama_client = OllamaClient(settings.OLLAMA_HOST, settings.OLLAMA_MODEL)
```

**`backend/app/core/embeddings_client.py`** — NEW

```
EmbeddingsClient
  __init__(model_name: str = "paraphrase-multilingual-mpnet-base-v2")
    Loads SentenceTransformer at module startup.

  async encode(text: str) -> list[float]
    Returns 768-dimensional vector. Runs model.encode() in thread executor.

  async encode_batch(texts: list[str]) -> list[list[float]]
    Batch encoding for vectorization stage.

  count_tokens(text: str) -> int
    Uses model tokenizer. Deterministic. Used by chunking_service.

MAX_TOKENS: int = 384

# Module-level singleton:
embeddings_client = EmbeddingsClient()
```

### Services

**`backend/app/services/kpi_inferencia_service.py`** — NEW (RF-10)

```
async inferir_kpis(db: Session, instrumento_id: int) -> list[KpiInferido]
  Loads instrument metadata and KPI catalog from PostgreSQL.
  Calls ollama_client.generar_json_estructurado() with inference prompt.
  Filters results with score < KPI_INFERENCIA_MIN_SCORE (0.3).
  Persists to pregunta_kpi. Advances estado to "kpis_inferidos".

_build_inference_prompt(metadatos: dict, kpis: list[Kpi]) -> str
_persist_kpi_inferencia(db: Session, instrumento_id: int, kpis: list[KpiInferido]) -> None
```

**`backend/app/services/json_canonico_service.py`** — NEW (RF-03)

```
async generar_json_canonico(db: Session, instrumento_id: int) -> Path
  Loads instrumento_procesado, pregunta_kpi records, and KPI details.
  Builds InstrumentoSemantico from prior pipeline stages.
  Writes to settings.json_path_abs / f"{instrumento_id}.json".
  Updates instrumento_procesado.ruta_json. Advances estado to "json_generado".
  Returns Path to written file.

_build_dublin_core(metadatos_base: dict, codigo: str, tipo: str) -> DublinCore
  dc_identifier = f"IND-{codigo}"  (semantic ID, not internal PK)

_build_especifico(tipo: str, metadatos_enriquecidos: dict) -> EspecificoEncuesta | EspecificoEntrevista | EspecificoPruebaEstandarizada
```

**`backend/app/services/chunking_service.py`** — NEW (RF-05, RF-06, RF-07)

```
async ejecutar_iec(instrumento_id: int) -> list[UnidadSemantica]
  Orchestrates the four IEC steps. Reads/writes JSON semantic file.

async _paso1_analisis_semantico(instrumento: InstrumentoSemantico) -> PlanChunking
  LLM analyzes full JSON. Produces plan with types, justifications, references.
  Saves plan to instrumento.plan_chunking (audit field only).

async _paso2_generar_narrativos(instrumento: InstrumentoSemantico, plan: PlanChunking) -> list[UnidadSemantica]
  LLM generates contenido_narrativo for each planned unit.
  Validates anchor prefix presence on each generated narrative.

async _paso3_control_longitud(instrumento: InstrumentoSemantico, chunks: list[UnidadSemantica]) -> list[UnidadSemantica]
  Deterministic token counting via embeddings_client.count_tokens().
  Calls _dividir_chunk_semanticamente() for any chunk > 384 tokens.
  Sub-chunks: ids "chunk_003a", "chunk_003b", inherit chunk_padre and anchor.

_paso4_ensamblar(instrumento_id: int, instrumento: InstrumentoSemantico, chunks: list[UnidadSemantica]) -> None
  Writes final chunks to instrumento.unidades_semanticas.
  Persists updated InstrumentoSemantico to JSON file.

_construir_ancla_semantica(contexto: ContextoInstrumento) -> str
  Pure function. Builds mandatory anchor prefix from contexto fields.

_validar_chunk_invariantes(chunk: UnidadSemantica, contexto: ContextoInstrumento) -> None
  Raises ChunkInvariantError if any invariant from RNF-03 is violated.
```

**`backend/app/services/vectorizacion_service.py`** — NEW (RF-04, RF-08, RF-12)

```
async vectorizar_instrumento(db: Session, instrumento_id: int, force: bool = False) -> int
  Reads InstrumentoSemantico from JSON file.
  Deletes existing ChromaDB entries for instrumento_id (idempotent).
  For each chunk: generates embedding, builds ChunkMetadata, adds to collection.
  Registers each chunk in documento_vectorizado (PostgreSQL).
  Advances estado to "vectorizado". Returns count of indexed chunks.

async re_vectorizar_completo(db: Session) -> dict[int, int]
  Iterates all instruments with ruta_json set. Calls vectorizar_instrumento for each.

_build_chroma_metadata(unidad: UnidadSemantica, instrumento: InstrumentoSemantico) -> ChunkMetadata
  kpis_ids: json.dumps(unidad.kpis_asociados)
  kpis_nombres: comma-joined names from instrumento.kpis_inferidos

_get_or_create_collection() -> chromadb.Collection
  PersistentClient at settings.chroma_path_abs.
  Collection name: settings.CHROMA_COLLECTION ("instrumentos_edu").
  Distance metric: cosine.
```

**`backend/app/services/rag_service.py`** — NEW (RF-11)

```
async consultar(db: Session, request: ConsultaRAGRequest) -> ConsultaRAGResponse
  1. Retrieves top_k chunks from ChromaDB with optional where filters.
  2. Selects top RAG_CONTEXT_MAX_CHUNKS (5) by distance score.
  3. Builds numbered source context string.
  4. Calls ollama_client.enviar_chat() with RAG_SYSTEM_PROMPT.
  5. Extracts FuenteRAG list from chunk metadatas.
  6. Logs to rag_log with chunks_usados JSONB.
  7. Returns ConsultaRAGResponse.

async consultar_stream(db: Session, request: ConsultaRAGRequest) -> AsyncGenerator[str]
  Same retrieval steps 1-3. Uses enviar_chat_stream(). Yields SSE tokens.
  Logs after stream completes.

_recuperar_chunks(request: ConsultaRAGRequest) -> list[dict]
  Embeds question. Queries ChromaDB with where_clause. Returns documents + metadatas + distances.

_build_where_clause(request: ConsultaRAGRequest) -> dict | None
  tipo_instrumento → $eq filter
  institucion → $eq filter
  periodo → $eq filter
  kpi_id → $contains filter on kpis_ids string
  Returns None if no filters.

RAG_SYSTEM_PROMPT: str
  Instructs LLM to answer only from provided evidence and cite [Fuente N] inline.
```

### Routers

**`backend/app/routers/pipeline.py`** — NEW

```
POST /pipeline/{instrumento_id}/kpis
POST /pipeline/{instrumento_id}/json-canonico
POST /pipeline/{instrumento_id}/chunking
POST /pipeline/{instrumento_id}/vectorizar
POST /pipeline/{instrumento_id}/re-vectorizar
GET  /pipeline/{instrumento_id}/estado
```

Each endpoint delegates to the corresponding service, returns `{ok, instrumento_id, estado}` on success and `{ok: false, error, etapa}` on failure.

**`backend/app/routers/rag.py`** — NEW (replaces `chat.py` stub)

```
GET  /rag                         → renders chat_ia.html template
POST /rag/consultar               → ConsultaRAGRequest → ConsultaRAGResponse
GET  /rag/consultar/stream        → StreamingResponse (text/event-stream)
GET  /rag/historial               → last 20 rag_log entries for current user
GET  /rag/fuente/{instrumento_id} → source metadata for attribution display
GET  /rag/descargar/{instrumento_id} → FileResponse from ruta_original
```

**`backend/app/main.py`** — MODIFY

```python
from app.routers import pipeline, rag
app.include_router(pipeline.router)
app.include_router(rag.router)
# chat.py kept temporarily for backward compatibility
```

---

## Data Models

### Pydantic schemas — `backend/app/schemas/semantico.py` (new file)

**Instrument context:**
```python
class ContextoInstrumento(BaseModel):
    titulo: str
    tipo_instrumento: Literal["encuesta", "entrevista", "prueba_estandarizada"]
    descripcion: str
    objetivo: str
    institucion_responsable: str
    poblacion_alcance: str
    periodo_inicio: str
    periodo_fin: str
    idioma: str = "es"
    condiciones_uso: str | None = None
    palabras_clave: list[str] = []
```

**Dublin Core (ISO 15836):**
```python
class DublinCore(BaseModel):
    dc_title: str
    dc_creator: str
    dc_subject: list[str] = []
    dc_description: str
    dc_publisher: str
    dc_contributor: str | None = None
    dc_date: str
    dc_type: str = "Dataset"
    dc_format: str
    dc_identifier: str        # "IND-ENC-042" — semantic, not internal PK
    dc_source: str | None = None
    dc_language: str = "es"
    dc_relation: str | None = None
    dc_coverage: str | None = None
    dc_rights: str | None = None
```

**KPI inference:**
```python
class KpiInferido(BaseModel):
    kpi_id: int
    nombre_kpi: str
    descripcion_kpi: str
    evidencia_textual: str
    score_inferencia: float   # 0.0 – 1.0
    secciones_relacionadas: list[str] = []
```

**Semantic unit (chunk):**
```python
class UnidadSemantica(BaseModel):
    id_chunk: str             # "chunk_000", "chunk_003a"
    chunk_padre: str | None   # null for resumen_instrumento only
    tipo: Literal["resumen_instrumento", "unidad_semantica", "hallazgo"]
    titulo: str
    descripcion: str | None = None
    contenido_narrativo: str  # starts with anchor — never contains admin data
    kpis_asociados: list[int] = []
    datos_cuantitativos: str | None = None
    dimensiones_origen: list[str] = []   # only populated for hallazgo type
```

**Instrument-specific blocks:**
```python
# Encuesta
class DimensionEncuesta(BaseModel):
    nombre_dimension: str
    descripcion: str
    n_items: int
    items_representativos: list[str] = []
    hallazgos_observados: str

class EspecificoEncuesta(BaseModel):
    n_items_total: int
    escala_respuesta: str
    dimensiones: list[DimensionEncuesta]
    metodologia_aplicacion: str
    tasa_respuesta: float | None = None
    limitaciones: list[str] = []

# Entrevista
class TemaEntrevista(BaseModel):
    tema: str
    pregunta_guia: str
    preguntas_de_profundizacion: list[str] = []
    hallazgos_cualitativos: str

class EspecificoEntrevista(BaseModel):
    tipo_entrevista: str
    n_preguntas_guia: int
    duracion_estimada: str | None = None
    guion_tematico: list[TemaEntrevista]
    perfil_entrevistados: str
    tecnica_analisis: str
    limitaciones: list[str] = []

# Prueba estandarizada
class AreaCompetencia(BaseModel):
    nombre_area: str
    descripcion: str
    n_reactivos: int
    nivel_cognitivo: str
    hallazgos_observados: str

class EspecificoPruebaEstandarizada(BaseModel):
    n_reactivos_total: int
    areas_competencia: list[AreaCompetencia]
    escala_calificacion: str
    normas_referencia: str
    poblacion_normativa: str
    coeficiente_confiabilidad: float | None = None
    validez: str | None = None
    limitaciones: list[str] = []

# Root model — serialized to /storage/json/{instrumento_id}.json
class InstrumentoSemantico(BaseModel):
    contexto: ContextoInstrumento
    dublin_core: DublinCore
    especifico: EspecificoEncuesta | EspecificoEntrevista | EspecificoPruebaEstandarizada
    kpis_inferidos: list[KpiInferido] = []
    plan_chunking: dict | None = None     # audit only — not embedded or indexed
    unidades_semanticas: list[UnidadSemantica] = []
```

**ChromaDB metadata (validated before insert):**
```python
class ChunkMetadata(BaseModel):
    instrumento_id: int
    codigo_instrumento: str
    tipo_instrumento: str
    tipo_chunk: str
    titulo_chunk: str
    institucion: str
    periodo: str
    poblacion: str
    kpis_ids: str          # json.dumps([3, 7, 12]) — serialized for $contains filter
    kpis_nombres: str
    chunk_padre: str | None
    id_chunk: str
    idioma: str = "es"
```

**RAG API schemas:**
```python
class ConsultaRAGRequest(BaseModel):
    pregunta: str
    tipo_instrumento: str | None = None
    institucion: str | None = None
    periodo: str | None = None
    kpi_id: int | None = None
    top_k: int = 8

class FuenteRAG(BaseModel):
    id_chunk: str
    codigo_instrumento: str
    titulo_chunk: str
    tipo_instrumento: str
    institucion: str
    periodo: str
    tipo_chunk: str
    kpis_nombres: str

class ConsultaRAGResponse(BaseModel):
    respuesta: str
    fuentes: list[FuenteRAG]
    latencia_ms: int
    modelo_llm: str
    modelo_embeddings: str
```

### ORM models

**`backend/app/models/instrumento.py`** — MODIFY

Add three columns to `InstrumentoProcesado`:
```python
codigo:         Mapped[str | None] = mapped_column(String(20), unique=True)
schema_version: Mapped[str | None] = mapped_column(String(10), default="1.0")
ruta_original:  Mapped[str | None] = mapped_column(Text)
```

**`backend/app/models/conocimiento.py`** — NEW

Four ORM models mapped to existing SQL tables:

```python
class RawData(Base):
    __tablename__ = "raw_data"
    __table_args__ = {"schema": "tt_rag"}
    raw_data_id:        Mapped[int]      # PK
    instrumento_id:     Mapped[int]      # FK → instrumento_procesado
    usuario_id:         Mapped[int | None]
    subido:             Mapped[datetime]
    tipo_de_instrumento: Mapped[str | None]
    raw_archivo:        Mapped[str | None]
    nombre_original:    Mapped[str | None]
    tipo_mime:          Mapped[str | None]
    tamano_bytes:       Mapped[int | None]
    hash_md5:           Mapped[str | None]

class DocumentoVectorizado(Base):
    __tablename__ = "documento_vectorizado"
    __table_args__ = {"schema": "tt_rag"}
    documento_vectorizado_id: Mapped[int]   # PK
    instrumento_id:           Mapped[int]   # FK
    prompt_id:                Mapped[int | None]
    vector_id:                Mapped[str | None]
    col_id:                   Mapped[str | None]
    tipo_chunk:               Mapped[str | None]  # resumen_instrumento | unidad_semantica | hallazgo
    activo:                   Mapped[bool]
    fecha_vectorizacion:      Mapped[datetime | None]

class PreguntaKpi(Base):
    __tablename__ = "pregunta_kpi"
    __table_args__ = {"schema": "tt_rag"}
    pregunta_id:     Mapped[int]          # PK
    instrumento_id:  Mapped[int]          # FK
    codigo_pregunta: Mapped[str | None]
    kpi_id:          Mapped[int]          # FK
    score_inferencia: Mapped[float | None]
    fecha:           Mapped[datetime | None]

class Prompt(Base):
    __tablename__ = "prompt"
    __table_args__ = {"schema": "tt_rag"}
    prompt_id: Mapped[int]    # PK
    tipo:      Mapped[str | None]   # chunking | metadatos | kpi_inferencia | query | contextualizacion
    version:   Mapped[str | None]
    contenido: Mapped[str | None]
    fecha:     Mapped[datetime | None]
    activo:    Mapped[bool]
```

### Database migration

**`postgres/init/migrations/02_knowledge_model.sql`** — NEW

Does not modify `01_schema.sql`. Applies additive changes only:

```sql
-- Add columns to instrumento_procesado
ALTER TABLE tt_rag.instrumento_procesado
  ADD COLUMN IF NOT EXISTS codigo         VARCHAR(20) UNIQUE,
  ADD COLUMN IF NOT EXISTS schema_version VARCHAR(10) DEFAULT '1.0',
  ADD COLUMN IF NOT EXISTS ruta_original  TEXT;

-- Backfill codigo
UPDATE tt_rag.instrumento_procesado
SET codigo = CONCAT(
  CASE plataforma
    WHEN 'Encuesta'             THEN 'ENC'
    WHEN 'Entrevista'           THEN 'ENT'
    WHEN 'Prueba estandarizada' THEN 'PRB'
    ELSE 'INS'
  END, '-', LPAD(instrumento_id::TEXT, 3, '0')
) WHERE codigo IS NULL;

-- Extend estado CHECK constraint
ALTER TABLE tt_rag.instrumento_procesado
  DROP CONSTRAINT IF EXISTS instrumento_procesado_estado_check;
ALTER TABLE tt_rag.instrumento_procesado
  ADD CONSTRAINT instrumento_procesado_estado_check
  CHECK (estado IN (
    'ingresado', 'limpio', 'metadatos_base', 'estandarizado',
    'kpis_inferidos', 'json_generado', 'vectorizado', 'error'
  ));

-- Fix tipo_chunk alignment with spec RF-06
ALTER TABLE tt_rag.documento_vectorizado
  DROP CONSTRAINT IF EXISTS documento_vectorizado_tipo_chunk_check;
ALTER TABLE tt_rag.documento_vectorizado
  ADD CONSTRAINT documento_vectorizado_tipo_chunk_check
  CHECK (tipo_chunk IN ('resumen_instrumento', 'unidad_semantica', 'hallazgo'));

-- Extend rag_log for full traceability (RF-11)
ALTER TABLE tt_rag.rag_log
  ADD COLUMN IF NOT EXISTS chunks_usados JSONB,
  ADD COLUMN IF NOT EXISTS usuario_id    INTEGER REFERENCES tt_rag.usuarios(usuario_id);
```

### Configuration additions

Add to `backend/app/core/config.py`:

```python
EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"
EMBEDDING_MAX_TOKENS: int = 384
CHROMA_COLLECTION: str = "instrumentos_edu"
KPI_INFERENCIA_MIN_SCORE: float = 0.3
IEC_MIN_TOKENS_FOR_SPLIT: int = 100
RAG_TOP_K: int = 8
RAG_CONTEXT_MAX_CHUNKS: int = 5
```

---

## Correctness Properties

The following invariants must hold at all times. Any implementation that violates them is incorrect regardless of test results:

### Property 1: No admin data in embeddings
`contenido_narrativo` never contains: database IDs, file paths, MD5 hashes, load timestamps, usernames, pipeline states, or schema versions.

**Validates: Requirements 1.1, 1.4**

### Property 2: Anchor prefix required
Every `contenido_narrativo`, regardless of chunk type, begins with the anchor phrase constructed from `contexto.tipo_instrumento`, `contexto.titulo`, `contexto.institucion_responsable`, `contexto.poblacion_alcance`, `contexto.periodo_inicio`, and `contexto.periodo_fin`.

**Validates: Requirements 1.7, 1.4**

### Property 3: ChromaDB stores exactly 3 things per chunk
`document` (contenido_narrativo), `embedding` (768-dimensional vector), and `metadatas` (the 13 fields defined in ChunkMetadata). Nothing else.

**Validates: Requirements 1.4, 1.3**

### Property 4: JSON semantic file is the sole source of truth for semantics
ChromaDB is derived from it and must be fully regenerable from it without accessing raw instrument files.

**Validates: Requirements 1.3, 1.12, 1.4**

### Property 5: Hallazgo chunks require at least one KPI
A chunk of type `hallazgo` with an empty `kpis_asociados` list is invalid and must not be indexed.

**Validates: Requirements 1.6, 1.10, 1.4**

### Property 6: One resumen_instrumento per instrument
Exactly one chunk with `tipo = "resumen_instrumento"` and `chunk_padre = null` must exist per instrument in ChromaDB.

**Validates: Requirements 1.6, 1.4**

### Property 7: Token limit enforced deterministically
`contenido_narrativo` must be verified by `embeddings_client.count_tokens()` before indexing. Any chunk exceeding 384 tokens must be split before reaching ChromaDB.

**Validates: Requirements 1.8, 1.2, 1.4**

### Property 8: State transitions are atomic
PostgreSQL `estado` is updated only after the stage completes successfully. Partial completion leaves `estado` unchanged (not advanced).

**Validates: Requirements 1.2, 1.4**

---

## Error Handling

### Pipeline service errors

Each service wraps its core logic in try/except. On any unhandled exception:
- Set `instrumento_procesado.estado = "error"` via a separate DB session (to avoid rollback of audit data).
- Write `instrumento_procesado.metadatos["error_pipeline"] = {"etapa": stage_name, "mensaje": str(exc), "timestamp": iso_timestamp}`.
- Log full traceback at ERROR level.
- Return `{"ok": false, "error": str(exc), "etapa": stage_name}` from the router (HTTP 200, not 500 — allows frontend to handle gracefully).

### ChunkInvariantError

Raised by `_validar_chunk_invariantes` when any correctness invariant is violated. Caught by `ejecutar_iec`, which sets instrument to error state with the invariant name and offending chunk ID. Prevents malformed chunks from reaching ChromaDB.

### OllamaError

Raised by `OllamaClient` on connection failure, timeout, or invalid JSON response. Propagated to the calling service, which sets instrument state to error. The pipeline can be retried from the failing stage once Ollama recovers.

### ChromaDB unavailability

`ChromaDBError` raised by `vectorizacion_service`. Instrument remains in `"json_generado"` state (not advanced to `"error"`) — the vectorization stage can be retried independently once ChromaDB recovers, without re-running kpi_inferencia or json_canonico stages.

### RAG query with no results

When ChromaDB returns zero chunks (no indexed instruments, or filters too restrictive), `rag_service.consultar()` returns a structured response without calling Ollama: `ConsultaRAGResponse(respuesta="No se encontró evidencia suficiente...", fuentes=[], ...)`. This is a valid response, not an error.

---

## Testing Strategy

### Unit tests

**`tests/test_chunking_invariants.py`**
- Verify `_construir_ancla_semantica` produces correct prefix for each instrument type.
- Verify `_validar_chunk_invariantes` raises `ChunkInvariantError` for: missing anchor, hallazgo with no KPIs, contenido_narrativo exceeding 384 tokens.
- Verify `_paso3_control_longitud` correctly triggers split for chunks > 384 tokens.
- Verify sub-chunk IDs follow the `{parent_id}{letter}` format.

**`tests/test_chroma_metadata.py`**
- Verify `_build_chroma_metadata` produces exactly 13 fields for each chunk type.
- Verify `kpis_ids` is a valid JSON-serialized list string.
- Verify no administrative fields leak into ChunkMetadata.

**`tests/test_json_canonico.py`**
- Verify `_build_dublin_core` maps all 15 Dublin Core fields correctly.
- Verify `dc_identifier` is built as `IND-{codigo}`, never using `instrumento_id` directly.
- Verify `_build_especifico` dispatches to the correct model for each `plataforma` value.

**`tests/test_rag_service.py`**
- Verify `_build_where_clause` builds correct ChromaDB filter syntax for each filter combination.
- Verify `consultar` returns a no-evidence response when chunk list is empty (no Ollama call made).
- Verify `_registrar_en_rag_log` includes `chunks_usados` with correct chunk identifiers.

### Integration tests

**`tests/test_pipeline_integration.py`**
- Load a test instrument fixture through all pipeline stages end-to-end.
- Assert estado transitions: estandarizado → kpis_inferidos → json_generado → vectorizado.
- Assert JSON semantic file exists and validates against `InstrumentoSemantico` schema.
- Assert ChromaDB contains the expected number of chunks with correct metadata.
- Assert re-vectorization produces the same chunk count as initial vectorization.

### Fixture strategy

All integration tests use a small synthetic instrument fixture (not a real uploaded file) with known structure:
- 1 encuesta with 2 dimensiones and 1 hallazgo above the independence threshold.
- Expected output: 4 chunks (1 resumen + 2 unidades + 1 hallazgo).
- Ollama calls are mocked in unit tests; real Ollama is used only in explicit integration test runs.

---

## File and Module Map

```
backend/app/
├── core/
│   ├── config.py               MODIFY — 7 new config fields
│   ├── ollama_client.py        REPLACE — async OllamaClient class + singleton
│   └── embeddings_client.py    NEW — EmbeddingsClient + MAX_TOKENS + singleton
│
├── models/
│   ├── instrumento.py          MODIFY — codigo, schema_version, ruta_original
│   └── conocimiento.py         NEW — RawData, DocumentoVectorizado, PreguntaKpi, Prompt
│
├── schemas/
│   ├── metadatos.py            KEEP — unchanged
│   └── semantico.py            NEW — all Pydantic models for the semantic plane
│
├── services/
│   ├── kpi_inferencia_service.py    NEW
│   ├── json_canonico_service.py     NEW
│   ├── chunking_service.py          NEW
│   ├── vectorizacion_service.py     NEW
│   └── rag_service.py               NEW
│
├── routers/
│   ├── pipeline.py             NEW
│   ├── rag.py                  NEW
│   └── chat.py                 DEPRECATE (keep for backward compat)
│
└── main.py                     MODIFY — register pipeline and rag routers

postgres/init/
└── migrations/
    └── 02_knowledge_model.sql  NEW — additive schema changes only

tests/
├── test_chunking_invariants.py NEW
├── test_chroma_metadata.py     NEW
├── test_json_canonico.py       NEW
├── test_rag_service.py         NEW
└── test_pipeline_integration.py NEW
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `OllamaClient` as class with singleton | Enables future circuit breaker, retry logic, or connection pooling without changing call sites in services |
| `EmbeddingsClient.encode()` runs in thread executor | `SentenceTransformer.encode()` is synchronous and CPU-bound; thread executor prevents blocking the FastAPI event loop |
| Two-step IEC (analysis then generation) | Separating structural planning from prose generation consistently produces better results than combined prompts |
| `PersistentClient` for ChromaDB | Data survives container restarts, consistent with the Docker volume mount in `docker-compose.yaml` |
| Cosine distance for ChromaDB collection | Sentence-transformer embeddings are L2-normalized; cosine is the correct similarity metric for this embedding family |
| Migration file separate from `01_schema.sql` | Preserves original file intact for clean database initializations; migration runs only on existing deployments |
| `chunks_usados` as JSONB in `rag_log` | Full per-query traceability without a separate join table; no referential integrity on chunk IDs is an acceptable tradeoff for this audit use case |
| Single collection `instrumentos_edu` | Cross-instrument queries are the primary use case; metadata filters handle type, institution, and KPI scoping |
| ChromaDB state independent from pipeline error | If vectorization fails (ChromaDB down), instrument stays `json_generado` and can retry; it does not block earlier stages from being considered successful |
