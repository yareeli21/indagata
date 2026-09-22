# Implementation Plan

> **Nota (2026-09-20):** plan de implementación histórico del SIS. El SIS ya está implementado;
> este documento es de referencia. Estado actual: `backend/ARCHITECTURE_AUDIT_REPORT.md`.

## Overview

This plan implements the Survey Intelligence Service (SIS) as a self-contained component
under `backend/survey_intelligence/`, following the Level 1 design. Tasks are ordered so
deterministic capabilities are built and verified first, then the LLM layer, then host
wiring. Each task lists the requirements it satisfies. All tasks are code and test tasks.

## Task Dependency Graph

Tasks are grouped into waves; tasks in the same wave can proceed in parallel once the
previous wave completes. Critical path: 1 -> 3 -> 4 -> 5 -> 9 -> 10 -> 13. LLM-independent
value (pillars A and B) is complete after task 9.

```json
{
  "waves": [
    { "wave": 1, "tasks": [1, 2], "depends_on": [] },
    { "wave": 2, "tasks": [3], "depends_on": [1] },
    { "wave": 3, "tasks": [4], "depends_on": [3] },
    { "wave": 4, "tasks": [5, 6], "depends_on": [4] },
    { "wave": 5, "tasks": [7, 9], "depends_on": [5] },
    { "wave": 6, "tasks": [8, 10], "depends_on": [2, 6, 7, 9] },
    { "wave": 7, "tasks": [11, 12, 15], "depends_on": [9, 10] },
    { "wave": 8, "tasks": [13], "depends_on": [8, 11, 12] },
    { "wave": 9, "tasks": [14, 16, 17], "depends_on": [13, 15] }
  ]
}
```

## Tasks

- [x] 1. Scaffold the component and public contracts
  - Create `backend/survey_intelligence/` package with `__init__.py` exporting only the
    facade and public contracts
  - Add `versioning.py` with `SCHEMA_VERSION = "sis-1.0.0"` and `PIPELINE_VERSION`
  - Create `contracts/enums.py` (InterpretabilityStatus, Severity, ColumnClass, Measure,
    EnrichmentProvenance, SufficiencyLevel, ImprovementScope, TransformId)
  - Create Pydantic (frozen) models in `contracts/`: `request.py`
    (SurveyIngestionRequest, SourceDocument, Options), `result.py`
    (SurveyIntelligenceResult, Diagnostics, StageDiagnostic), `canonical.py`,
    `enriched.py`, `spss.py`, `improvement.py`
  - Ensure the request carries the 13 Dublin Core fields with host-matching names
  - _Requirements: 1.1, 1.3, 1.5, 15.1, 15.2, 14.1_

- [x] 2. Define ports (dependency protocols)
  - Create `ports/` Protocols: `LLMPort`, `EmbeddingPort`, `RagRetrieverPort`,
    `ClockPort`, `IdGeneratorPort`, `TelemetryPort`
  - Provide `NullRagRetriever` and a no-op `TelemetryPort` default implementation
  - Verify the core imports nothing from `api/` (add a test asserting import isolation)
  - _Requirements: 1.2, 1.4, 6.1_

- [x] 3. Build the ingestion stage (S1) and readers
  - Implement `engine/readers/csv_reader.py` handling BOM, quoted fields, empty rows
  - Implement `engine/readers/xlsx_reader.py` (openpyxl) with sheet selection
  - Implement `pipeline/stages/s1_ingestion.py` producing a raw tabular structure
  - Detect source platform (LimeSurvey signature from the 7 leading metadata columns)
  - Return `status = "failed"` with a diagnostic on unparsable input
  - Write unit tests using `parti.csv` and `saludm.csv` fixtures
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4. Build the Canonical Survey Model builder (S2)
  - Implement `pipeline/stages/s2_canonical_builder.py`
  - Normalize variable names; assign stable `variable_id`/`question_id`
  - Parse matrix pattern `stem [item]` and group items under their matrix question
  - Classify each column as `question | platform_metadata | free_text | unknown`
  - Compute `canonical_id` as a content hash (deterministic)
  - Write tests asserting identical `canonical_id` for identical content and correct
    matrix grouping on `parti.csv`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Build the data profiler (S3)
  - Implement `engine/profiling/` (type_inference, scale_detector, stats)
  - Infer per-variable data type, cardinality, null ratio (no LLM)
  - Detect Likert kind and points from observed values
  - Detect scale-value anomalies via edit distance 1 with `canonical_guess`
    (e.g. "En deesacuerdo" -> "En desacuerdo")
  - Distinguish structural nulls (conditional skips) from real nulls
  - Keep all metrics inside the Canonical Model only
  - Write tests for Likert detection, typo anomaly, and structural-null detection on both fixtures
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Build the context sufficiency stage (S4)
  - Implement `pipeline/stages/s4_context_sufficiency.py`
  - Mark INSUFFICIENT_CONTEXT candidates before any LLM call (e.g. `Seed`)
  - Produce missing_information, why_not_interpretable, required_to_interpret
  - Write tests asserting `Seed` is flagged and self-descriptive headers are not
  - _Requirements: 5.1, 5.2_

- [x] 7. Implement platform-column detection and the drop_columns proposal
  - Implement `engine/heuristics/platform_columns.py`
  - Emit a single grouped `drop_columns` proposal for the 7 LimeSurvey metadata columns
  - Emit a separate proposal for timestamp columns noting derived response-time value
  - Write tests asserting one grouped proposal (not seven) on both fixtures
  - _Requirements: 9.1, 9.6, 7.1_

- [x] 8. Implement the transform apply engine (propose then decide then apply)
  - Implement `engine/transforms/` (transform_registry, drop_columns, normalize_scale, apply_engine)
  - `apply_engine.apply(canonical, decisions)` returns an updated Canonical Model
  - `drop_columns` retains removed columns for reversibility
  - `normalize_scale` maps a misspelled value to its canonical value
  - Never mutate data without an explicit accepted decision
  - Write tests: apply/reject paths, reversibility, and typo normalization
  - _Requirements: 9.2, 9.3, 9.4, 9.5_

- [x] 9. Implement the deterministic SPSS mapper
  - Implement `engine/spss/spss_mapper.py` and `spss_validator.py`
  - Derive draft SPSS dictionary (name, variable_label, measure, type, value_labels,
    missing_values) from the Canonical Model where possible
  - Generate `value_encoding` (text -> code), mapping detected typos to the canonical code
  - Set `enrichment_provenance = auto_deterministic` for deterministically derived fields
  - Validate names (<= 64 chars, no spaces) and valid measure values
  - Write tests producing SPSS dictionary + encoding for the Likert matrix in `parti.csv`
  - _Requirements: 10.1, 10.4, 10.6_

- [x] 10. Implement robust LLM JSON parsing and the LLM stages (S6, S7)
  - Implement `engine/parsing/robust_json.py` (generalized from the existing
    `_parsear_respuesta_json`, schema-driven)
  - Implement `engine/prompts/` (audit_prompt, enrichment_prompt, spss_enrichment_prompt)
    with strict JSON output and explicit no-invention rules
  - Implement `pipeline/stages/s6_methodology_audit.py` producing survey_level_findings
    (ambiguous, without-context, too-short/long, double-barreled, wording bias,
    inconsistent scales, redundant, low value, droppable, missing metadata, deficiencies,
    risks, opportunities)
  - Implement `pipeline/stages/s7_semantic_enrichment.py` producing construct, semantic
    role, tags, chunking_hint, analytical_sufficiency, and SPSS `auto_llm` completion with
    confidence
  - Enforce the post-LLM downgrade to INSUFFICIENT_CONTEXT when evidence is missing
  - Assign analytical_sufficiency level (rica/adecuada/limitada/pobre) with a bounded
    enrichment_suggestion.type
  - Emit instrument-change suggestions as ImprovementOpportunity (future_analysis/survey),
    not executable transforms
  - Route needs_user_input SPSS fields as proposals
  - Write tests with a fake LLMPort (fixed responses) covering valid, malformed, and
    invented-meaning cases
  - _Requirements: 5.3, 5.4, 7.1, 7.2, 7.3, 7.5, 8.1, 8.2, 8.3, 8.4, 10.2, 10.3_

- [x] 11. Implement the optional RAG stage (S5)
  - Implement `pipeline/stages/s5_rag_retrieval.py`
  - Skip with reason `no_rag_sources` when run_rag is false or sources are empty
  - When enabled, index sources in a per-request_id namespace and retrieve context for
    insufficient variables; allow promotion to INTERPRETABLE with RAG evidence
  - Write tests for both the skipped path (NullRagRetriever) and the resolve path (fake retriever)
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 12. Implement gap analysis (S8) and improvement opportunities
  - Implement `pipeline/stages/s8_gap_analysis.py`
  - Generate improvement_opportunities across the 6 scopes with status `proposed`
  - Include proposed_rule (when/then) for validation_rule candidates
    (e.g. scale_typo_normalization)
  - Do not persist and do not auto-promote
  - Write tests asserting scopes present and the scale-typo candidate rule from `parti.csv`
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 13. Implement the orchestrator, enriched assembler (S9), and facade
  - Implement `pipeline/context.py` (shared PipelineContext) and
    `pipeline/orchestrator.py` (Pipeline + Chain of Responsibility)
  - Make S1/S2 fatal and S3-S9 degradable; on degradable failure continue and record it
  - Implement `pipeline/stages/s9_enriched_assembler.py` assembling the Enriched Model,
    proposals, and improvement opportunities
  - Implement `facade.py` `SurveyIntelligenceService.process(...)` building the result with
    schema_version, pipeline_version, canonical_id, and diagnostics
  - Set status to completed / completed_degraded / failed appropriately; never raise to host
  - Write an end-to-end test over `parti.csv` and `saludm.csv` (with fake LLM) asserting a
    complete SurveyIntelligenceResult
  - _Requirements: 7.4, 12.1, 12.2, 12.3, 14.1, 14.2, 14.3_

- [x] 14. Implement telemetry and diagnostics
  - Emit per-stage telemetry (name, status, duration) via TelemetryPort
  - Populate self-describing diagnostics (stages run/skipped with reasons, llm_calls, degraded)
  - Propagate request_id through events and result
  - Ensure no respondent content is emitted to telemetry
  - Write tests asserting diagnostics content and absence of respondent values in events
  - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 15. Implement the .SAV writer
  - Implement `export/sav_writer.py` using pyreadstat
  - Write variable labels, value labels, and measurement levels from the complete SPSS dictionary
  - Write a test producing a `.SAV` from the enriched `parti.csv` dictionary and re-reading it
    to assert labels/measures round-trip
  - _Requirements: 10.5_

- [x] 16. Wire the SIS into the host wizard (two-path approval + endpoint redesign)
  - Provide reference adapters (outside the core): OllamaLLMAdapter wrapping
    `enviar_mensaje_chat` (uses OLLAMA_MODEL, compatible with crear_modelo_ollama variants),
    SystemClock, UuidGenerator
  - Add `POST .../analyze` replacing `extract`; remove the `extract` endpoint
  - Split `approve` into `approve/cleaning` (transformacion -> apply_engine, executes,
    reversible) and `approve/enrichment` (metadato_enriquecido + kpi_sugerido)
  - Add pipeline states `etl_pendiente_limpieza` and `etl_pendiente_enriquecimiento`
    (update `ESTADOS_PIPELINE` CheckConstraint and `EstadoPipeline` literal)
  - Path dispatch by `dc_type`: survey -> tabular path; interview/test -> document path
  - Survey caching: cache the CanonicalSurveyModel JSON (`{hash}.canonical.json`) in
    data_path; document caching: keep plain text as today
  - Codebook: capture optional codebook at upload (survey only), pass as `rag_sources`
  - Map SurveyIntelligenceResult to `EtlPropuesta`, `MetadatosEnriquecidos`, `KpiInferido`,
    consolidated JSON (`storage/json/{id}.json`), `.SAV` (`ruta_sav`), improvement table
  - _Requirements: 1.1, 1.2, 9.3_

- [x] 17. Testing strategy consolidation
  - Add golden-dataset fixtures and expected results for `parti.csv` and `saludm.csv`
  - Add the critical-restriction test that fails the build if any context-less variable
    receives invented meaning
  - Add snapshot/contract-regression tests keyed to schema_version
  - Add a determinism test asserting identical canonical_id and deterministic findings across runs
  - _Requirements: 5.3, 3.3, 14.3, 4.1_

- [x] 18. Implement KPI inference against the host catalog
  - Add `KpiInference` contract (nombre_sugerido, score_relevancia, tipo_relacion,
    evidencia_textual, variables_fuente) and add it to SurveyIntelligenceResult
  - Implement a KPI inference sub-stage in S7 (or S7-KPI) with an LLM prompt that scores
    relevance; the SIS suggests names + scores, it does NOT own a catalog
  - Catalog matching is host-side (map nombre_sugerido -> tt_rag.kpi.kpi_id); new-KPI
    proposals are emitted as ImprovementOpportunity, not as direct KPIs
  - Test with a fake LLM asserting KpiInference shape and score bounds
  - _Requirements: 7.1, 7.2_

- [x] 19. Implement the document ingestion path (interview, standardized test)
  - Add a document reader (PDF/DOCX/TXT -> text) and a document canonical builder that
    detects sections/items as canonical "variables" (no scales/matrices)
  - Route by dc_type: survey -> tabular path (existing); interview/test -> document path
  - Reuse S4-S9 (context sufficiency, audit, enrichment, sufficiency, KPIs, improvements)
    over document segments; the output model stays homogeneous
  - Test with a small narrative fixture (interview transcript) asserting a complete result
  - _Requirements: 2.1, 3.1, 7.1, 7.2_

## Notes

- Deterministic-first ordering means tasks 1-9 deliver working value (Canonical Model,
  profiling, drop_columns proposals, SPSS draft, apply engine) without requiring Ollama.
- The LLM layer (task 10) is developed against a fake `LLMPort` for reproducible tests; the
  real Ollama adapter is host-side (task 16), preserving component decoupling.
- Do not couple the core to `api/` or `tt_rag`; all host integration lives in adapters and
  the wizard mapping, not inside `backend/survey_intelligence/`.
- The `.SAV` writer (task 15) and the drop_columns apply engine (task 8) together close the
  gap where `EtlService.approve` currently records but does not execute `transformacion` decisions.
- Fixtures `parti.csv` (school engagement, matrix Likert) and `saludm.csv` (mental-health
  services, mixed types + free text) are the primary Level-1 acceptance fixtures.
