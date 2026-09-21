# Requirements Document

> **Nota (2026-09-20):** documento de REQUISITOS de diseño. El SIS ya está implementado;
> puede diferir de este spec. Estado actual: `backend/ARCHITECTURE_AUDIT_REPORT.md`.

## Introduction

The Survey Intelligence Service (SIS) is a reusable, decoupled domain component
for the INDAGATA platform. It processes surveys from CSV/XLSX files (Google Forms,
Microsoft Forms, LimeSurvey, Qualtrics, or other sources) and runs an LLM-assisted
intelligent ETL that analyzes, cleans, enriches, and contextualizes survey
instruments.

The primary output is an enriched JSON oriented to intelligent chunking, semantic
search, embeddings, contextual retrieval (future RAG), advanced analytics, and
metadata discovery. The service also produces an SPSS variable dictionary that
enables `.SAV` export for statistical analysis.

This scope targets Level 1: operating without a codebook, interpreting the
instrument only from what is visible in headers and values. RAG is optional; the
service must operate correctly when no documentary source exists.

The SIS is an enterprise, decoupled, integrable component, not a standalone
application. It communicates through two contracts only: a `SurveyIngestionRequest`
(input) and a `SurveyIntelligenceResult` (output). It does not know FastAPI, the
`tt_rag` database, or the upload wizard. External resources (Ollama, ChromaDB,
clock, IDs) enter through injectable ports (hexagonal architecture).

## Glossary

- **Canonical Survey Model:** normalized, deterministic representation (structure + metrics).
- **Enriched Survey Model:** semantic result + SPSS metadata (free of metrics/administrative data).
- **INSUFFICIENT_CONTEXT:** state for a variable that cannot be interpreted; no meaning is invented.
- **analytical_sufficiency:** judgment of the explanatory power of an interpretable question.
- **enrichment_provenance:** origin of an SPSS metadata field (auto_deterministic, auto_llm, needs_user_input, user_provided).
- **propose-decide-apply:** the SIS proposes, the user decides, the SIS executes only what is approved.
- **Improvement Opportunity:** improvement recommendation (survey/pipeline/future) emitted as `proposed`.

## Requirements

### Requirement 1: Decoupled contract-based interface

**User Story:** As a platform integrator, I want the SIS to expose a single entry
point with clear input/output contracts, so that I can integrate it without coupling
to its internals.

#### Acceptance Criteria

1. WHEN the host invokes the SIS THEN the SIS SHALL expose exactly one entry facade (`SurveyIntelligenceService`) that accepts a `SurveyIngestionRequest` and returns a `SurveyIntelligenceResult`.
2. THE SIS SHALL NOT import any module from the host application (`api/`, `tt_rag`, FastAPI, or the upload wizard).
3. THE SIS SHALL receive survey content as bytes within the request and SHALL NOT read from disk or a database directly.
4. WHERE external capabilities are required (LLM, embeddings, RAG retrieval, clock, ID generation, telemetry) THE SIS SHALL depend only on injected port protocols.
5. THE SurveyIngestionRequest SHALL carry the 13 Dublin Core metadata fields using the same field names as the host `MetadatosDC` model.

### Requirement 2: Ingestion of CSV/XLSX from multiple sources

**User Story:** As a researcher, I want to ingest CSV/XLSX exports from common survey
platforms, so that I can process instruments regardless of their source.

#### Acceptance Criteria

1. WHEN a CSV file is provided THEN the SIS SHALL parse it, handling BOM markers, quoted fields, and empty rows.
2. WHEN an XLSX file is provided THEN the SIS SHALL parse the specified sheet, or the first sheet when none is specified.
3. WHEN the file cannot be parsed (corrupt or unsupported) THEN the SIS SHALL return a result with `status = failed` and a diagnostic explaining the cause.
4. THE SIS SHALL attempt to detect the source platform (for example, LimeSurvey) and record it as `platform_guess`.
5. WHEN rows exceed `options.max_rows_profiled` THEN the SIS SHALL limit profiling to that bound and record the limitation in diagnostics.

### Requirement 3: Canonical Survey Model (deterministic)

**User Story:** As a data engineer, I want a normalized, deterministic representation
of the survey, so that downstream steps and the host rely on a stable structural truth.

#### Acceptance Criteria

1. WHEN ingestion succeeds THEN the SIS SHALL build a Canonical Survey Model containing variables, questions, dimensions, and source information.
2. THE Canonical Survey Model SHALL be produced without any LLM call.
3. WHEN the same content is ingested twice THEN the SIS SHALL produce an identical `canonical_id` (content hash).
4. WHERE a matrix question pattern `stem [item]` is present THEN the SIS SHALL parse the stem and item, group items under their matrix question, and use the bracketed text as the item text.
5. THE Canonical Survey Model SHALL classify each column as `question`, `platform_metadata`, `free_text`, or `unknown`.

### Requirement 4: Data profiling

**User Story:** As a data engineer, I want structural profiling of each variable, so
that scales, types, and missing values are characterized objectively.

#### Acceptance Criteria

1. THE SIS SHALL infer, per variable, the data type, cardinality, and null ratio without an LLM.
2. WHEN a Likert-type scale is present THEN the SIS SHALL detect its kind and number of points from observed values.
3. WHEN a scale value is a near-miss of a canonical label (edit distance 1, for example "En deesacuerdo" versus "En desacuerdo") THEN the SIS SHALL record it as an anomaly with a `canonical_guess`.
4. WHERE nulls result from conditional skip logic THEN the SIS SHALL distinguish structural nulls from real nulls.
5. THE profiling results (metrics, counts) SHALL reside only in the Canonical Survey Model and SHALL NOT appear in the Enriched Survey Model.

### Requirement 5: Context sufficiency and the no-invention rule

**User Story:** As a survey methodologist, I want the system to refuse to invent meaning
for variables it cannot interpret, so that the enrichment remains trustworthy.

#### Acceptance Criteria

1. WHEN a variable has no associated question, description, labels, or RAG match THEN the SIS SHALL classify it as `INSUFFICIENT_CONTEXT`.
2. WHEN a variable is classified `INSUFFICIENT_CONTEXT` THEN the SIS SHALL explain what information is missing, why it cannot be interpreted, and what is required to interpret it.
3. IF the LLM proposes meaning for a variable that has no supporting evidence in the Canonical Model or RAG THEN the SIS SHALL downgrade that variable to `INSUFFICIENT_CONTEXT`.
4. THE SIS SHALL require non-empty `evidence` for any variable marked `INTERPRETABLE`.

### Requirement 6: Optional RAG

**User Story:** As a researcher, I want the system to use documentary sources when
available and still work when they are absent, so that RAG remains a value-add rather
than a dependency.

#### Acceptance Criteria

1. WHEN `options.run_rag` is false OR `rag_sources` is empty THEN the SIS SHALL skip RAG retrieval and record the stage as `skipped` with reason `no_rag_sources`.
2. WHEN `rag_sources` are provided AND `run_rag` is true THEN the SIS SHALL index them in a namespace isolated per `request_id` and retrieve context for variables marked insufficient.
3. WHEN RAG provides a definition for an insufficient variable THEN the SIS SHALL allow promotion to `INTERPRETABLE` with `evidence` citing the RAG source.
4. THE overall pipeline behavior SHALL remain identical whether or not RAG is present, except for the RAG stage outcome.

### Requirement 7: LLM-assisted methodological audit and semantic enrichment

**User Story:** As a survey methodologist, I want automated detection of methodological
issues and semantic enrichment per question, so that I can improve the instrument and
enable semantic retrieval.

#### Acceptance Criteria

1. WHEN the audit stage runs THEN the SIS SHALL detect ambiguous questions, questions without context, too-short questions, too-long questions, double-barreled questions, suspected wording bias, inconsistent scales, redundant variables, low-analytical-value variables, droppable columns, missing metadata, methodology deficiencies, analysis risks, and enrichment opportunities.
2. WHEN enrichment runs for an interpretable variable THEN the SIS SHALL produce a construct, semantic role, semantic tags, and a `chunking_hint` with embeddable text.
3. THE Enriched Survey Model SHALL contain only semantic content and SPSS metadata and SHALL NOT contain metrics, counts, dates, response IDs, or timings.
4. WHEN the LLM is unavailable or returns invalid output after one retry THEN the SIS SHALL degrade gracefully, returning the Canonical Model and deterministic findings with `degraded = true`, and SHALL NOT raise an exception to the host.
5. THE SIS SHALL parse LLM JSON output robustly (direct JSON, markdown-fenced JSON, and embedded JSON) and validate it against the expected schema.

### Requirement 8: Analytical sufficiency assessment

**User Story:** As a researcher, I want the system to judge whether each question is
sufficient for later analysis and suggest enrichment, so that future surveys yield richer data.

#### Acceptance Criteria

1. WHEN a variable is interpretable THEN the SIS SHALL assign an `analytical_sufficiency.level` of `rica`, `adecuada`, `limitada`, or `pobre`.
2. WHEN sufficiency is below `rica` THEN the SIS SHALL provide a reason, a description of what the question could reveal, and an `enrichment_suggestion`.
3. THE `enrichment_suggestion.type` SHALL be one of: `add_followup_open_ended`, `add_reason_field`, `split_double_barreled`, `clarify_scope`, `add_missing_dimension`.
4. WHEN an enrichment suggestion implies changing the instrument (which cannot apply to already-collected responses) THEN the SIS SHALL emit it as an ImprovementOpportunity of scope `future_analysis` or `survey`, NOT as an executable transformation.

### Requirement 9: Propose-decide-apply transformations

**User Story:** As a data owner, I want the system to propose data transformations and
apply them only after I approve each one, so that I keep control over my dataset.

#### Acceptance Criteria

1. WHEN the SIS detects platform metadata columns THEN it SHALL emit a single grouped `drop_columns` proposal listing all such columns, not one proposal per column.
2. THE SIS SHALL NOT modify the dataset automatically; transformations SHALL apply only after an explicit approval decision.
3. WHEN a `transformacion` proposal is approved THEN the SIS SHALL apply it and produce an updated Canonical Model plus a reversible record of the change.
4. WHEN a `drop_columns` transformation is applied THEN the SIS SHALL retain the removed columns data so the operation can be reversed.
5. WHEN a scale typo anomaly is detected THEN the SIS SHALL offer a `normalize_scale` proposal mapping the misspelled value to its canonical value.
6. WHERE a column may have derived analytical value (for example, response time from start/submit timestamps) THEN the SIS SHALL present its removal as a separate proposal with that caveat.

### Requirement 10: SPSS metadata and .SAV export (hybrid enrichment)

**User Story:** As an analyst, I want a standards-based SPSS variable dictionary and a
`.SAV` export, so that the enriched instrument is ready for statistical analysis.

#### Acceptance Criteria

1. THE SIS SHALL derive a draft SPSS variable dictionary (`name`, `variable_label`, `measure`, `type`, `value_labels`, `missing_values`) from the Canonical Model deterministically where possible.
2. WHERE a field is unambiguously interpretable THEN the SIS SHALL complete it via LLM with `enrichment_provenance = auto_llm` and a confidence score, marking it `confirmed`.
3. WHERE a field cannot be decided with certainty THEN the SIS SHALL leave it blank and mark it `needs_user_input`, emitting it as a proposal rather than inventing a value.
4. THE SIS SHALL generate a `value_encoding` mapping observed text values to numeric codes, mapping detected scale typos to the canonical code.
5. WHEN the SPSS dictionary is complete THEN the SIS SHALL be able to produce a `.SAV` file with variable labels, value labels, and measurement levels.
6. THE SPSS field origin SHALL be one of `auto_deterministic`, `auto_llm`, `needs_user_input`, or `user_provided`.

### Requirement 11: Continuous improvement opportunities

**User Story:** As a platform owner, I want each processed survey to generate improvement
recommendations, so that the platform learns which methodological, structural, and
semantic aspects to strengthen.

#### Acceptance Criteria

1. WHEN a survey is processed THEN the SIS SHALL generate `improvement_opportunities` covering scopes: `survey`, `pipeline`, `future_analysis`, `validation_rule`, `quality_heuristic`, and `pattern`.
2. THE SIS SHALL emit each opportunity with `status = proposed` and SHALL NOT promote any candidate rule to an active rule automatically.
3. THE SIS SHALL NOT persist improvement opportunities; persistence and promotion are the host responsibility.
4. WHEN a candidate validation rule is provided THEN the opportunity SHALL include a `proposed_rule` with when/then semantics.

### Requirement 12: Automatic full analysis on ingestion

**User Story:** As a researcher, I want a complete analysis to run automatically on every
ingestion, so that I do not have to request it manually.

#### Acceptance Criteria

1. WHEN a survey is ingested THEN the SIS SHALL run the full 9-stage pipeline in one invocation without requiring a separate analyze call.
2. THE only fatal stages SHALL be ingestion (S1) and canonical building (S2); all other stages SHALL be degradable.
3. WHEN a degradable stage fails THEN the pipeline SHALL continue and record the failure in diagnostics.

### Requirement 13: Observability and diagnostics

**User Story:** As an operator, I want observability into each run, so that I can debug
and monitor the service without exposing respondent data.

#### Acceptance Criteria

1. THE SIS SHALL emit per-stage telemetry (stage name, status, duration) through the injected `TelemetryPort`.
2. THE SurveyIntelligenceResult SHALL include self-describing diagnostics: which stages ran, which were skipped and why, the number of LLM calls, and whether the run degraded.
3. THE `request_id` SHALL be propagated through all telemetry events and the result.
4. THE SIS SHALL NOT include respondent response content in telemetry or logs.

### Requirement 14: Versioning

**User Story:** As a maintainer, I want explicit versioning, so that contract and behavior
changes are traceable and comparable across runs.

#### Acceptance Criteria

1. THE SurveyIntelligenceResult SHALL include `schema_version` (contract shape), `pipeline_version` (behavior), and `canonical_id` (content identity).
2. WHEN a candidate rule is promoted or a prompt changes THEN `pipeline_version` SHALL increase even if `schema_version` is unchanged.
3. WHEN the JSON contract shape changes THEN `schema_version` SHALL increase per SemVer.

### Requirement 15: Physical packaging as a single component

**User Story:** As a maintainer, I want the entire service to live in one self-contained
folder, so that it can be reused or relocated as a unit.

#### Acceptance Criteria

1. ALL SIS source code SHALL reside under a single folder `backend/survey_intelligence/`.
2. THE component SHALL expose only the facade and the public contracts through its package `__init__`.
3. THE design/spec documentation SHALL reside under `.kiro/specs/survey-intelligence-service/` and SHALL NOT be placed inside the component source folder.
