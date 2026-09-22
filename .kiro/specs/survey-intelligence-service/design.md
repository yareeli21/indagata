# Design Document — Survey Intelligence Service (SIS)

> **Nota (2026-09-20):** documento de DISEÑO. El SIS ya está implementado y puede diferir
> en detalles de este spec. Fuente de verdad del estado actual:
> `backend/ARCHITECTURE_AUDIT_REPORT.md` y el código en `backend/survey_intelligence/`.

> Status: Consolidated design — Level 1 (no codebook)
> Scope: reusable, decoupled domain component for the INDAGATA platform

## Overview

The Survey Intelligence Service (SIS) is a domain service that processes surveys
from CSV/XLSX files (Google Forms, Microsoft Forms, LimeSurvey, Qualtrics, or other
sources) and runs an LLM-assisted intelligent ETL to analyze, clean, enrich, and
contextualize survey instruments.

The primary output is an enriched JSON oriented to intelligent chunking, semantic
search, embeddings, contextual retrieval (future RAG), advanced analytics, and
metadata discovery. It also produces an SPSS variable dictionary that enables `.SAV`
export.

The SIS is an enterprise, decoupled, integrable component, not a standalone
application. It communicates through two contracts only: `SurveyIngestionRequest`
(input) and `SurveyIntelligenceResult` (output). It does not know FastAPI, the
`tt_rag` database, or the upload wizard. All external resources (Ollama, ChromaDB,
clock, IDs) enter through injectable ports (Ports and Adapters / hexagonal).

### Level 1 scope

Level 1 covers the "no codebook" case: everything is interpreted from what is visible
in headers and values. It is functional because modern forms already carry meaning in
the header. The SIS exploits three always-present signals:

1. The header text = the question (sometimes with a `stem [item]` pattern).
2. The observed values = the scale and its consistency.
3. The distribution = type, nulls, cardinality, junk columns.

RAG is optional. The SIS must operate correctly when no documentary source exists.

### Four Level-1 pillars

| Pillar | Description | Needs LLM |
|---|---|---|
| A. Canonical + Profiling | Normalized representation and structural statistics | No |
| B. Junk-column detection | Column removal proposal (propose-decide-apply) | Partial |
| C. Analytical sufficiency | Semantic judgment of explanatory power per question | Yes |
| D. SPSS metadata / .SAV export | Standard variable dictionary for `.SAV` | Partial |

### Multi-platform support (Google Forms, Microsoft Forms, LimeSurvey, others)

LimeSurvey is only one example. The SIS must handle exports from several platforms and
also unknown platforms. Platform detection is NOT hardcoded: a column is classified as
`platform_metadata` because it is structurally administrative (IDs, timestamps, language,
seeds, email, name, progress) and has no question shape, not because it comes from a
specific tool. A `platform_signature_registry` (in `engine/heuristics/platform_columns.py`)
holds per-platform admin-column signatures and is extensible; even without a matching
signature, admin columns are still detected by shape.

Three real-world findings from actual exports drive the reader/canonical design:

**Finding 1 — matrix questions use different notations per platform.** The matrix parser
is a Strategy with multiple configurable patterns, not a single format:

| Platform | Notation | Example |
|---|---|---|
| LimeSurvey | `stem [item]` | `Evalúa... [Confidencialidad]` |
| Microsoft Forms | `stem .subitem` | `Evalúa los siguientes aspectos... .Calidad de la enseñanza` |
| Google Forms | no matrix in sample; single-question columns | headers are full questions |

**Finding 2 — multiple-choice comes in two opposite shapes.** These are inverse
representations of the same question type:

- LimeSurvey explodes each option into its own binary `Yes/No` column (`[Página web]`, `[Redes sociales]`...).
- Microsoft Forms collapses all chosen options into a single cell separated by `;`
  (`Horarios poco flexibles;Carga académica elevada;...`).
- Google Forms collapses options into a single cell separated by `, ` (comma+space)
  (`Deportivas, Culturales o artísticas, Tecnológicas`).

The profiler detects the delimited multi-value cell as a dedicated data type
`multi_select`. The multi_select delimiter is NOT assumed: the detector recognizes both
`;` (Microsoft Forms) and `, ` (Google Forms). For SPSS/.SAV a `multi_select` question is
later expanded into multiple dummy variables.

**Finding 3 — character encoding must be detected, not assumed.** Real Microsoft Forms
exports arrived as mojibake (`finalizaci�n`, `a�o`), indicating Latin-1/CP1252 read as
UTF-8. The CSV reader tries encodings in order (UTF-8, UTF-8-BOM, CP1252/Latin-1). The
LimeSurvey export instead carries a UTF-8 BOM. Headers may also contain embedded newlines
(Microsoft Forms), which are normalized.

Admin-column signatures per platform (initial registry):

- **LimeSurvey:** `Response ID`, `Date submitted`, `Last page`, `Start language`, `Seed`, `Date started`, `Date last action`.
- **Microsoft Forms:** `Id`, `Hora de inicio`, `Hora de finalización`, `Correo electrónico`, `Nombre` (and the English equivalents `Id`, `Start time`, `Completion time`, `Email`, `Name`).
- **Google Forms:** `Marca temporal` / `Timestamp` (a real datetime value, deserialized by openpyxl), and optionally `Dirección de correo electrónico` / `Email address` when the form collects it. Minimal admin footprint: often a single `Marca temporal` column. Confirmed from `googleforms_extracurriculares.xlsx`.

Finding 4 — the multi_select delimiter differs per platform: Microsoft Forms uses `;`,
Google Forms uses `, `. Timestamps may arrive as native datetime (XLSX) or as strings
(CSV); the reader normalizes both to a consistent datetime in the Canonical.

### Instrument types: the SIS analyzes all three (survey, interview, standardized test)

The SIS is NOT survey-only. It analyzes the three host instrument types (`encuesta`,
`entrevista`, `prueba_estandarizada`). Surveys get more structural detail because they
are tabular; interviews and standardized tests are narrative documents. The SIS has two
ingestion paths but ONE homogeneous output model (Canonical + Enriched + proposals +
KPI inferences + improvement opportunities):

| Path | Instrument types | S1 input | Canonical "variables" are | Scales/matrices |
|---|---|---|---|---|
| Survey (tabular) | `encuesta` | CSV/XLSX bytes | columns | yes |
| Document (narrative) | `entrevista`, `prueba_estandarizada` | PDF/DOCX/TXT text | detected sections/items | no |

The LLM enrichment (constructs, analytical sufficiency, KPI inference) applies to both
paths; only the deterministic structure differs. The host selects the path by `dc_type`.

### KPI inference against the host catalog

The SIS infers relevant KPIs and scores their relevance, but does NOT own a KPI catalog.
It emits `KpiInference` objects with a suggested name, relevance score, relation type,
textual evidence and source variables. The host matches `nombre_sugerido` to a real
`kpi_id` in its `tt_rag.kpi` catalog and creates the `KpiInferido` (origen=propuesta_etl).
Level 1 does catalog matching only (no invention of new KPIs); proposing brand-new KPIs
is emitted as an ImprovementOpportunity for governance.

### Codebook as optional RAG input (wired now, active in Level 2)

When the instrument is a survey, the host upload offers attaching a codebook. That file
travels in the request as a `rag_sources` entry. In Level 1 the retriever is null (S5
skipped), but the codebook already flows through the contract so Level 2 (RAG) activates
without contract changes. The codebook is the practical trigger of Level 2.

### Caching strategy (host-side, respects the 90-day cache)

The host caches by file SHA-256 in `data_path`. What is cached differs by path:
- Document path: the extracted plain text (as today).
- Survey path: the `CanonicalSurveyModel` JSON (`{hash}.canonical.json`).

Only DETERMINISTIC output (Canonical) is cached, never LLM enrichment: the Canonical is
reproducible; enrichment varies with the Ollama model (see `crear_modelo_ollama`). On
re-ingestion after delete, the survey path skips S1-S3 and starts from the cached Canonical.

## Architecture

The core of the SIS is pure; adapters (Ollama, Chroma) live at the edge and are
provided by the host. Guiding pattern: Hexagonal Architecture (Ports and Adapters).

```
+---------------------------------------------------------------+
|  INDAGATA PLATFORM (host)                                     |
|   routers_carga.py --+                                        |
|   EtlService --------+                                        |
|                      v                                        |
|         +---------------------------+                         |
|         |  SIS FACADE (single port) |  <-- only coupling      |
|         |  SurveyIntelligenceService|                         |
|         +---------------------------+                         |
|                      |                                        |
|   +------------------+-------------------------------+        |
|   |  INJECTED PORTS                                   |       |
|   |  LLMPort . EmbeddingPort . RagRetrieverPort .     |       |
|   |  ClockPort . IdGeneratorPort . TelemetryPort      |       |
|   +---------------------------------------------------+       |
+---------------------------------------------------------------+
```

### Physical packaging (single folder)

```
backend/
  survey_intelligence/                 <- self-contained component
    __init__.py                        <- exports ONLY the facade and contracts
    facade.py                          <- SurveyIntelligenceService (entry port)
    versioning.py                      <- SCHEMA_VERSION, PIPELINE_VERSION
    contracts/
      request.py                       <- SurveyIngestionRequest, SourceDocument
      result.py                        <- SurveyIntelligenceResult, Diagnostics
      canonical.py                     <- CanonicalSurveyModel
      enriched.py                      <- EnrichedSurveyModel
      spss.py                          <- SpssVariableMetadata, Measure, Provenance
      improvement.py                   <- ImprovementOpportunity
      enums.py                         <- InterpretabilityStatus, Severity, etc.
    ports/
      llm_port.py                      <- Protocol LLMPort
      embedding_port.py                <- Protocol EmbeddingPort
      rag_port.py                      <- Protocol RagRetrieverPort
      clock_port.py, ids_port.py, telemetry_port.py
    pipeline/
      orchestrator.py                  <- runs the 9 stages
      context.py                       <- shared PipelineContext
      stages/
        s1_ingestion.py
        s2_canonical_builder.py
        s3_data_profiler.py
        s4_context_sufficiency.py
        s5_rag_retrieval.py
        s6_methodology_audit.py
        s7_semantic_enrichment.py
        s8_gap_analysis.py
        s9_enriched_assembler.py
    engine/
      readers/       (csv_reader.py, xlsx_reader.py)
      profiling/     (type_inference.py, scale_detector.py, stats.py)
      heuristics/    (rule_registry.py, quality_rules.py, platform_columns.py)
      transforms/    (transform_registry.py, drop_columns.py, normalize_scale.py, apply_engine.py)
      spss/          (spss_mapper.py, spss_validator.py)
      prompts/       (audit_prompt.py, enrichment_prompt.py, spss_enrichment_prompt.py)
      parsing/       (robust_json.py)
    export/
      sav_writer.py                    <- Enriched (SPSS side) -> .SAV (pyreadstat)
```

The host only imports:

```python
from survey_intelligence import (
    SurveyIntelligenceService,
    SurveyIngestionRequest,
    SurveyIntelligenceResult,
)
```

### Pipeline of 9 stages

```
SurveyIngestionRequest
  |
 [S1] Ingestion ---------> read bytes, detect CSV/XLSX, platform (FATAL if corrupt)
 [S2] Canonical Builder -> normalize variables/questions, detect matrices stem[item]
 [S3] Data Profiling ----> types, scales, structural vs real nulls, anomalies
 [S4] Context Sufficiency> mark INSUFFICIENT_CONTEXT candidates BEFORE the LLM
 [S5] RAG Retrieval -----> ONLY if rag_sources non-empty (else: skipped)
 [S6] Methodology Audit -> LLM: ambiguity, double-barreled, bias (degradable)
 [S7] Semantic Enrichment> LLM: construct, role, analytical sufficiency, SPSS auto_llm
 [S8] Gap Analysis ------> compare expected vs found -> Improvement Opportunities
 [S9] Enriched Assembler > assemble Enriched + proposals + final result
  |
SurveyIntelligenceResult
```

- Automatic execution: the facade runs the 9 stages in one invocation per ingestion.
- Fatal stages: only S1 and S2. All others are degradable.
- Each Stage receives and enriches a shared PipelineContext
  (Pipeline + Chain of Responsibility).

### Design patterns

| Pattern | Where | Why |
|---|---|---|
| Ports and Adapters (Hexagonal) | core vs LLM/RAG/Chroma | decouple from host and Ollama |
| Facade | SurveyIntelligenceService | minimal integration surface |
| Pipeline + Chain of Responsibility | orchestrator/stages | isolable, testable 9-step flow |
| Strategy | readers, scale detectors, transforms | extensible sources/scales/actions |
| Registry | rule_registry, transform_registry | add rules/transforms without touching engine |
| Result Object | SurveyIntelligenceResult + status | graceful degradation, no exceptions to host |
| DTO immutables (Pydantic) | contracts | stable, versioned contracts |
| Null Object | NullRagRetriever | operate without RAG without dirty branching |

## Components and Interfaces

### Ports (dependency contracts)

The host implements these `Protocol`s. `ollama_client` and future Chroma become
trivial adapters.

```python
class LLMPort(Protocol):
    def complete_json(self, *, system_prompt: str, user_prompt: str,
                      temperature: float, timeout_s: float) -> str: ...

class EmbeddingPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class RagRetrieverPort(Protocol):
    def index(self, sources: list) -> None: ...
    def retrieve(self, query: str, k: int) -> list: ...

class ClockPort(Protocol):
    def now(self) -> "datetime": ...

class TelemetryPort(Protocol):
    def event(self, name: str, attrs: dict) -> None: ...
```

Example adapter (wraps existing code):

```python
class OllamaLLMAdapter:
    def complete_json(self, *, system_prompt, user_prompt, temperature, timeout_s):
        return enviar_mensaje_chat(
            system_prompt=system_prompt,
            historial=[{"role": "user", "content": user_prompt}],
            timeout=timeout_s,
        )
```

Without RAG, the host passes a `NullRagRetriever` and S5 is skipped.

### Facade

`SurveyIntelligenceService.process(request: SurveyIngestionRequest) -> SurveyIntelligenceResult`
is the single entry point. It constructs the PipelineContext, runs the orchestrator,
and returns the Result Object.

### Propose-decide-apply transformations

The SIS proposes, the user decides, and only then the SIS executes. It never modifies
data on its own. It fits the existing `EtlService` (table `etl_propuesta`, states
`pendiente/aceptada/rechazada`).

Two natures of proposal:

1. Executable transformation over data that ALREADY exists -> applied after approval.
   - `drop_columns`: remove platform columns (grouped into ONE proposal).
   - `normalize_scale`: correct `En deesacuerdo` -> `En desacuerdo`.
   - SPSS metadata `auto_llm` high confidence -> applied automatically.
   - SPSS metadata `needs_user_input` -> proposal to be resolved by user.
2. Recommendation for the next version of the instrument (NOT executable now, the
   respondents already answered) -> emitted as an ImprovementOpportunity.
   - Add a "why?" to a low-sufficiency question.
   - Split a double-barreled question (`split_double_barreled`).

Execution flow:

```
[S6/S7] SIS detects --> proposal (state: pendiente)
                              |
              user decides (host Step 4 / approve)
                              |
              +---------------+--------------+
        REJECTED                        ACCEPTED
              |                              |
     dataset untouched          SIS.apply_transform(canonical, transform)
                                             |
                              new Canonical + reversible record
                                             |
                              regenerate Enriched + JSON + .SAV
```

Methodological note: "adds nothing" does not mean destroy. `Response ID` is removable
from semantic analysis but useful as a join key. `Date submitted - Date started` gives
response time (a possible quality indicator), so its removal is a separate proposal
with that caveat. The LLM never asserts "this is junk"; it says "this seems not to add
to the semantic analysis, should I remove it?" with a visible justification.

Reversibility: `drop_columns` stores removed columns in `valor_original`; an approval
made in error can be undone.

### Analytical sufficiency

Distinction from INSUFFICIENT_CONTEXT:
- INSUFFICIENT_CONTEXT: cannot interpret what the variable measures; no meaning invented.
- analytical_sufficiency: the variable is understood, but the question falls short for
  future analysis. Interpretable, but could yield more.

Levels: `rica`, `adecuada`, `limitada`, `pobre`.

Closed catalog of `enrichment_suggestion.type`: `add_followup_open_ended`,
`add_reason_field`, `split_double_barreled`, `clarify_scope`, `add_missing_dimension`.

### SPSS metadata and .SAV export (hybrid)

SPSS metadata is the output contract of enrichment, not a replacement for the semantic
layer. Semantic enrichment produces the SPSS metadata: the LLM does not invent arbitrary
fields; it fills a well-defined SPSS contract when it can and leaves it open for the user
when it cannot.

The Enriched Model has two faces:
1. Semantic face (for RAG/embeddings): construct, role, sufficiency, chunking.
2. SPSS face (for `.SAV`): the standard variable dictionary.

Generation flow:

```
CSV --> Canonical --> spss_mapper (deterministic draft)
                            |
                   +--------+---------+
          certain fields          uncertain fields
        (auto_deterministic)          |
                   |                   v
                   |          LLM completes (auto_llm + confidence)
                   |                   |
                   |          +--------+--------+
                   |   high confidence    low confidence
                   |   (confirmed)        (needs_user_input)
                   |       |                   |
                   |       |          user decides (propose/apply)
                   v       v                   v
              Full Enriched Model (SPSS face + semantic face)
                            |
                   +--------+--------+
                   v                 v
            sav_writer          enriched JSON
            -> .SAV             -> RAG/embeddings
```

Text-to-code encoding: CSVs store text (`"De acuerdo"`), but `.SAV` needs numeric code +
`value_labels`. The SIS generates `value_encoding` (`"De acuerdo" -> 4`). Side effect:
`"En deesacuerdo"` maps to the same code `2` as `"En desacuerdo"`, cleaning the data.

Host integration: `InstrumentoProcesado` already has `ruta_sav`; `config` already has
`sav_path_abs`; the code already anticipates `pyreadstat`.

### Optional RAG strategy

- Optional by design. `run_rag` + non-empty `rag_sources` activate S5. Otherwise S5
  reports `skipped/no_rag_sources` and the pipeline continues identically.
- Ephemeral indexing per request (namespace = `request_id`) by default, to avoid context
  leaks between surveys.
- Directed use: RAG is queried to resolve variables marked insufficient in S4. If it
  provides a definition -> variable becomes INTERPRETABLE with `evidence: ["rag:..."]`.
  If not -> remains INSUFFICIENT_CONTEXT.
- Anti-hallucination: retrieved context is passed as citable evidence; the validator
  requires non-empty `evidence` for any interpretation.

### LLM strategy

- One port, two uses (S6 audit, S7 enrichment) with distinct prompts and low temperature
  (0.1) for reproducibility.
- Prompts with strict JSON output contract + explicit negation rules ("if no evidence,
  INSUFFICIENT_CONTEXT, do not invent").
- Robust parsing reused: `_parsear_respuesta_json` logic from the current `llm_service`
  generalized into `engine/parsing/robust_json.py`.
- Post-LLM validation with Pydantic against each stage schema; invalid response -> 1
  retry -> if it fails, degraded stage keeping the deterministic findings.
- Partial determinism: nulls, cardinality, scales, and lengths NEVER depend on the LLM.

### Continuous improvement strategy

Each run produces `improvement_opportunities` in 6 scopes: `survey`, `pipeline`,
`future_analysis`, `validation_rule`, `quality_heuristic`, `pattern`.

- Origin: S8 compares what the pipeline expected to determine vs what it could.
- Lifecycle: `proposed -> under_review -> accepted -> promoted | rejected`. The SIS
  only emits `proposed`. Promotion to an active rule is human governance.
- Persistence: host responsibility (`tt_rag.improvement_opportunity`). The SIS is stateless.
- Safe learning: promoting a `validation_rule` adds it to the versioned `rule_registry`
  and raises `pipeline_version`.

### Observability strategy

- `TelemetryPort` injected: per-stage spans (`sis.stage.<name>`), metrics
  (`sis.llm.calls`, `sis.stage.duration_ms`, `sis.variables.insufficient_context.count`,
  `sis.degraded`), and events. The host decides the backend.
- Diagnostics in the output: each result is self-describing.
- Correlation: `request_id` flows through everything.
- No PII in logs: structure and metrics only, never respondent content.
- Host bridge: spans can map to `pipeline_ingesta_log` without the SIS knowing that table.

### Versioning strategy

Three independent, explicit versions in every output:
- `schema_version` (SemVer, `sis-1.0.0`): JSON contract shape.
- `pipeline_version`: behavior (rules, prompts, heuristics).
- `canonical_id` (content hash): deterministic identity of the input.

### Host integration (without coupling)

`EtlService.extract_and_propose` remains the host orchestrator:
- Today: calls `llm_service.generar_propuestas_etl(...)` (one call, flat proposals).
- Tomorrow: builds a `SurveyIngestionRequest` (bytes + 13 DC + optional RAG), invokes
  `SurveyIntelligenceService.process(req)`, and maps:
  - `enriched.survey_level_findings` + `variables_enriched` -> `EtlPropuesta`.
  - `proposals` (drop_columns, normalize_scale, SPSS needs_user_input) -> `EtlPropuesta`
    type `transformacion`.
  - `improvement_opportunities` -> new governance table.
  - `canonical` + `enriched` -> consolidated JSON (`ruta_json`).
  - SPSS face of `enriched` -> `.SAV` via `sav_writer` (`ruta_sav`).

Gap in current code: `EtlService.approve` does NOT execute accepted `transformacion`
proposals today (it only records the decision and processes `metadato_enriquecido` and
`kpi_sugerido`). The missing piece is the SIS `apply_engine`.

### Host endpoint redesign (wizard integration)

The current `extract` + `proposals` + `approve` flow is replaced by a single `analyze`
call plus a two-path approval, reflecting propose-decide-apply and the cleaning-then-
enrichment order.

| Current endpoint | Fate |
|---|---|
| `upload` | keep (pre-SIS) |
| `metadata/init`, `metadata` | keep (pre-SIS) |
| `GET .../etl/extract` | remove (fused into `analyze`) |
| `GET .../etl/proposals` | keep (idempotent view of SIS proposals) |
| `POST .../etl/approve` | split into two paths (below) |

New endpoints:
- `POST .../analyze` — runs the SIS end-to-end (S1..S9) in one call, persists proposals.
  Reflects "automatic full analysis on ingestion".
- `POST .../approve/cleaning` — decide on `transformacion` proposals (drop_columns,
  normalize_scale). On accept, the SIS `apply_engine` EXECUTES on data (reversible).
  Runs FIRST because it changes the Canonical.
- `POST .../approve/enrichment` — decide on `metadato_enriquecido` and `kpi_sugerido`.
  On accept, writes into the consolidated JSON / `KpiInferido`. Runs on cleaned data.

New pipeline states (host `ESTADOS_PIPELINE` + `EstadoPipeline` literal):
```
metadata_registrado
  -> analyze (SIS full run)
  -> etl_pendiente_limpieza          (approve/cleaning)
  -> etl_pendiente_enriquecimiento   (approve/enrichment)
  -> etl_aprobado                    (consolidated JSON written to storage/json/{id}.json)
```

The codebook (optional, survey only) is captured at upload and passed as `rag_sources`
in the `SurveyIngestionRequest`. The consolidated JSON is written to `storage/json/{id}.json`,
structured for the future chunking/RAG phase.

## Data Models

The SIS generates two models separated by responsibility:
- Canonical Survey Model: structural and administrative truth. 100% deterministic.
  Contains metrics, types, nulls, scales, platform columns, dates, IDs.
- Enriched Survey Model: purely semantic + SPSS metadata. Result of AI + heuristics.
  Free of metrics and administrative data.

> Golden rule: metrics, counts, and administrative data live in the Canonical. The
> Enriched only contains what enriches the semantic field + the SPSS dictionary.

### Canonical Survey Model

```json
{
  "canonical_id": "sha256-of-normalized-content",
  "source": { "platform_guess": "limesurvey", "file_name": "parti.csv", "sheet": null },
  "dimensions": { "n_rows": 7, "n_columns": 40 },
  "variables": [
    {
      "variable_id": "v_008",
      "raw_header": "Indica que tan de acuerdo... [Estoy muy interesado/a en aprender.]",
      "normalized_name": "interes_aprender",
      "position": 8,
      "column_class": "question",
      "inferred_data_type": "ordinal",
      "detected_scale": {
        "kind": "likert",
        "points": 5,
        "labels": ["Totalmente desacuerdo", "En desacuerdo",
                   "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"],
        "consistent": true,
        "anomalies": [{ "value": "En deesacuerdo", "occurrences": 2, "canonical_guess": "En desacuerdo" }]
      },
      "matrix_group": {
        "stem": "Indica que tan de acuerdo estas... sobre lo que aprendes en la escuela.",
        "item": "Estoy muy interesado/a en aprender."
      },
      "value_distribution": {
        "n_non_null": 6, "n_null": 1, "null_ratio": 0.143, "cardinality": 4
      }
    }
  ],
  "questions": [
    { "question_id": "q_008", "variable_ids": ["v_008"], "text": "Estoy muy interesado/a en aprender.",
      "length_chars": 34, "length_words": 6 }
  ]
}
```

`column_class`: `question` | `platform_metadata` | `free_text` | `unknown`.

### Enriched Survey Model

```json
{
  "based_on_canonical_id": "sha256-...",
  "survey_summary": {
    "purpose_inferred": "Measure school engagement (interest, belonging, effort, study strategies)",
    "confidence": 0.78,
    "provenance": "llm+metadata"
  },
  "variables_enriched": [
    {
      "variable_id": "v_008",
      "interpretability_status": "INTERPRETABLE",
      "spss_metadata": {
        "name": "interes_aprender",
        "variable_label": "Estoy muy interesado/a en aprender",
        "measure": "ordinal",
        "type": "numeric",
        "value_labels": {
          "1": "Totalmente desacuerdo", "2": "En desacuerdo",
          "3": "Ni de acuerdo ni en desacuerdo", "4": "De acuerdo",
          "5": "Totalmente de acuerdo"
        },
        "value_encoding": { "Totalmente desacuerdo": 1, "En desacuerdo": 2,
          "En deesacuerdo": 2, "Ni de acuerdo ni en desacuerdo": 3,
          "De acuerdo": 4, "Totalmente de acuerdo": 5 },
        "missing_values": [],
        "enrichment_provenance": "auto_llm",
        "confidence": 0.97,
        "status": "confirmed"
      },
      "semantic_enrichment": {
        "construct": "interest in learning",
        "semantic_role": "predictor",
        "semantic_tags": ["interest", "intrinsic_motivation"],
        "chunking_hint": {
          "chunk_group": "interes_aprendizaje",
          "embeddable_text": "Interest in learning - Likert 5-point item of the school engagement construct"
        },
        "evidence": ["explicit header"],
        "analytical_sufficiency": {
          "level": "adecuada",
          "reason": "Clear Likert item within a school-interest battery.",
          "what_it_could_reveal": "Could distinguish boredom by content vs by teaching method.",
          "enrichment_suggestion": {
            "type": "clarify_scope",
            "proposed_item": "Clarify whether interest refers to content or to how it is taught.",
            "rationale": "Increases diagnostic value without lengthening the instrument too much."
          }
        }
      }
    },
    {
      "variable_id": "v_seed",
      "interpretability_status": "INSUFFICIENT_CONTEXT",
      "missing_information": ["definition of Seed in the platform"],
      "why_not_interpretable": "Numeric column with no associated question or labels; LimeSurvey technical name unconfirmed.",
      "required_to_interpret": ["LimeSurvey documentation or codebook defining Seed"]
    }
  ],
  "survey_level_findings": {
    "ambiguous_questions": [],
    "questions_without_context": [],
    "too_short_questions": [],
    "too_long_questions": [],
    "double_barreled": ["q_satisfaccion_equipo_jefe"],
    "wording_bias_suspected": [],
    "inconsistent_scales": [
      { "group": ["v_008"], "detail": "Misspelled value En deesacuerdo detected twice" }
    ],
    "redundant_variables": [],
    "low_analytical_value": [],
    "droppable_columns": [
      { "variable_ids": ["v_001","v_002","v_003","v_004","v_005","v_006","v_007"],
        "reason": "LimeSurvey platform metadata, not question responses" }
    ],
    "missing_metadata": ["Start language declares en but content is in Spanish"],
    "methodology_deficiencies": [],
    "analysis_risks": [],
    "enrichment_opportunities": []
  }
}
```

### SPSS contract

| Field | Description | Example |
|---|---|---|
| `name` | Short variable name (<= 64 chars, no spaces) | `interes_aprender` |
| `variable_label` | Readable label = question text | "Estoy muy interesado/a en aprender" |
| `value_labels` | Code -> label mapping | `{"1":"Totalmente desacuerdo", ...}` |
| `value_encoding` | Observed text -> code (to write `.SAV`) | `{"De acuerdo": 4, ...}` |
| `measure` | Measurement level | `nominal` \| `ordinal` \| `scale` |
| `type` | Data type | `numeric` \| `string` |
| `missing_values` | Codes considered missing | `[]` |

Canonical -> SPSS correspondence (raw material already detected without AI):

| Detected in Canonical | Populates in SPSS |
|---|---|
| Likert 5pts scale + labels | `value_labels` + `measure: ordinal` |
| header text | `variable_label` |
| inferred type | `type` + `measure` |
| `normalized_name` | `name` |
| structural nulls (conditional skips) | `missing_values` |

`enrichment_provenance`: `auto_deterministic`, `auto_llm`, `needs_user_input`, `user_provided`.

### Improvement Opportunity

```json
{
  "opportunity_id": "uuid",
  "scope": "survey | pipeline | future_analysis | validation_rule | quality_heuristic | pattern",
  "title": "Candidate rule: normalize misspelled scale variants",
  "description": "Detected En deesacuerdo as a variant of En desacuerdo.",
  "evidence": ["v_008:En deesacuerdo x2"],
  "proposed_rule": {
    "rule_id_candidate": "scale_typo_normalization",
    "when": "scale value with edit distance 1 from a canonical label",
    "then": "propose normalize_scale with the canonical value"
  },
  "confidence": 0.8,
  "status": "proposed",
  "generated_by": "gap_analysis_stage",
  "created_at": "2026-09-14T10:00:00Z"
}
```

### Input contract — SurveyIngestionRequest

```json
{
  "request_id": "uuid-generated-by-host",
  "survey": {
    "file_name": "parti.csv",
    "file_bytes_b64": "<base64>",
    "mime_type": "text/csv",
    "sheet": null
  },
  "metadata": {
    "dc_title": "...", "dc_creator": "...", "dc_subject": ["..."],
    "dc_description": "...", "dc_publisher": "INDAGATA", "dc_date": "2026-03-14",
    "dc_type": "encuesta", "dc_format": "csv", "dc_language": "es",
    "dc_coverage": "...", "dc_rights": "...", "dc_source": null, "dc_relation": null
  },
  "rag_sources": [],
  "options": {
    "run_rag": false,
    "run_methodology_audit": true,
    "language_hint": "es",
    "max_rows_profiled": 50000,
    "llm_temperature": 0.1
  }
}
```

### Output contract — SurveyIntelligenceResult

```json
{
  "request_id": "uuid",
  "schema_version": "sis-1.0.0",
  "pipeline_version": "pipeline-1.0.0",
  "generated_at": "2026-09-14T10:00:00Z",
  "status": "completed",
  "canonical_survey_model": { "...": "see Canonical" },
  "enriched_survey_model": { "...": "see Enriched" },
  "proposals": [ { "...": "see propose-decide-apply" } ],
  "improvement_opportunities": [ { "...": "see Improvement Opportunity" } ],
  "diagnostics": {
    "stages": [
      { "stage": "ingestion", "status": "ok", "ms": 120 },
      { "stage": "rag_retrieval", "status": "skipped", "reason": "no_rag_sources" }
    ],
    "llm_calls": 3,
    "warnings": [],
    "degraded": false
  }
}
```

`status`: `completed` | `completed_degraded` | `failed`.

## Correctness Properties

### Property 1: Determinism of deterministic stages

Given the same input bytes, S1-S4 (ingestion, canonical, profiling, context sufficiency)
produce byte-identical output; the same content yields the same `canonical_id`.

**Validates: Requirements 3.2, 3.3, 4.1**

### Property 2: No-invention invariant

No variable receives `construct`, `suggested_description`, or `semantic_role` without
supporting evidence. Enforced in two layers (prompt + post-LLM validator that downgrades to
`INSUFFICIENT_CONTEXT`).

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 3: Metric separation

The Enriched Survey Model never contains metrics, counts, dates, response IDs, or timings.

**Validates: Requirements 4.5, 7.3**

### Property 4: No autonomous mutation

The dataset is never modified without an explicit approval; transformations apply only after
a decision.

**Validates: Requirements 9.2, 9.3**

### Property 5: Reversibility

An applied `drop_columns` transformation retains removed data.

**Validates: Requirements 9.4**

### Property 6: RAG independence

Pipeline behavior is identical with or without RAG, except the RAG stage outcome.

**Validates: Requirements 6.1, 6.4**

### Property 7: Statelessness

The SIS persists nothing; improvement opportunities are returned, not stored.

**Validates: Requirements 11.3**

## Error Handling

- Fatal errors (S1 ingestion, S2 canonical): return `SurveyIntelligenceResult` with
  `status = "failed"` and a diagnostic; no partial models.
- Degradable errors (S3-S9): the stage is marked degraded in diagnostics, the pipeline
  continues, and the result carries `degraded = true` with `status = "completed_degraded"`.
- LLM failures: 1 controlled retry; on repeated failure the stage degrades and only
  deterministic findings are kept. No exception propagates to the host.
- Invalid LLM JSON: robust parser attempts direct/markdown/embedded extraction; if all
  fail, the stage degrades.
- External content is untrusted: RAG/LLM content is treated as data, never as instructions.

## Testing Strategy

- Golden datasets: fixtures with/without codebook, mixed scales, known double-barreled
  items, junk columns, and their expected `SurveyIntelligenceResult`.
- Deterministic assertions (exact): scale detection, nulls, droppable columns, lengths.
- Semantic metrics (LLM): precision/recall for `double_barreled`, `wording_bias`,
  `INSUFFICIENT_CONTEXT`, sufficiency levels, against human labels.
- Critical-restriction test: a dedicated test feeds context-less variables and fails the
  build if any receives invented meaning.
- Contract regression: snapshot testing of the output JSON; shape changes require a
  `schema_version` bump.
- Reproducibility: with `temperature=0`, canonical + deterministic findings are
  byte-identical across runs.
- Real multi-platform fixtures (in `backend/survey_intelligence/tests/fixtures/`):
  - `limesurvey_participacion.csv` — LimeSurvey, 33-item Likert matrix `stem [item]`, includes the "En deesacuerdo" scale typo and an empty (abandoned) response row.
  - `limesurvey_salud_mental.csv` — LimeSurvey, mixed types: binary, exploded multiple-choice, evaluation matrix, and free text; conditional-skip structural nulls.
  - `msforms_graduacion.csv` — Microsoft Forms, `.subitem` matrix notation, `;`-collapsed multi_select cells, admin columns `Id/Hora de inicio/Hora de finalización/Correo electrónico/Nombre`, embedded newlines in headers.
  - Google Forms fixture pending a real export to finalize its admin-column signature.

## Roadmap (Level 1)

1. Reader + Canonical + platform-column detection (deterministic) -> generate `drop_columns`
   proposal over `parti.csv` and `saludm.csv`.
2. `apply_engine` + `drop_columns` + `normalize_scale` (reversible).
3. Deterministic `spss_mapper` -> SPSS dictionary draft.
4. LLM connection (S6/S7): semantic judgment, `analytical_sufficiency`, SPSS `auto_llm`.
5. `sav_writer` -> `.SAV` export with `pyreadstat`.
6. Wire into `EtlService` -> the wizard uses the SIS underneath.
