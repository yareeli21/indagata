# 🗺️ Metadata Service - Visual Architecture Map

## Service Overview Diagram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   METADATA SERVICE (8003)                ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                           ┃
┃  ┌─────────────────────────────────────────────────┐    ┃
┃  │  HTTP API Layer (routers/)                      │    ┃
┃  ├─────────────────────────────────────────────────┤    ┃
┃  │                                                 │    ┃
┃  │  health.py:          /health, /health/ready    │    ┃
┃  │                                                 │    ┃
┃  │  metadata.py:  ┌── GET /metadata/{id}/init     │    ┃
┃  │               ├── POST /metadata/{id}          │    ┃
┃  │               ├── GET /metadata/{id}           │    ┃
┃  │               ├── GET /metadata (list)         │    ┃
┃  │               └── DELETE /metadata/{id}        │    ┃
┃  │                                                 │    ┃
┃  │  enrichment.py: ┌── POST /enrichment/{id}/create    │ ┃
┃  │                 ├── GET /enrichment/{id}      │    ┃
┃  │                 ├── POST /enrichment/{id}/approve   │ ┃
┃  │                 └── GET /enrichment/{id}/summary    │ ┃
┃  │                                                 │    ┃
┃  └─────────────────┬───────────────────────────────┘    ┃
┃                    │                                     ┃
┃                    ↓                                     ┃
┃  ┌─────────────────────────────────────────────────┐    ┃
┃  │  Business Logic Layer (services/)               │    ┃
┃  ├─────────────────────────────────────────────────┤    ┃
┃  │                                                 │    ┃
┃  │  ┌──────────────────────────────────────┐      │    ┃
┃  │  │ DCManager                            │      │    ┃
┃  │  ├──────────────────────────────────────┤      │    ┃
┃  │  │ • get_initial_data()                 │      │    ┃
┃  │  │ • register_dc()                      │      │    ┃
┃  │  │ • get_dc()                           │      │    ┃
┃  │  │ • list_dc()                          │      │    ┃
┃  │  │ • delete_dc()                        │      │    ┃
┃  │  │                                      │      │    ┃
┃  │  │ Handles: 13 Dublin Core fields       │      │    ┃
┃  │  └──────────────────────────────────────┘      │    ┃
┃  │                                                 │    ┃
┃  │  ┌──────────────────────────────────────┐      │    ┃
┃  │  │ EnrichmentEngine                     │      │    ┃
┃  │  ├──────────────────────────────────────┤      │    ┃
┃  │  │ • create_proposals()                 │      │    ┃
┃  │  │ • get_proposals()                    │      │    ┃
┃  │  │ • approve_proposals()                │      │    ┃
┃  │  │ • get_summary()                      │      │    ┃
┃  │  │                                      │      │    ┃
┃  │  │ Handles: LLM enrichment proposals     │      │    ┃
┃  │  └──────────────────────────────────────┘      │    ┃
┃  │                                                 │    ┃
┃  └─────────────────┬───────────────────────────────┘    ┃
┃                    │                                     ┃
┃                    ↓                                     ┃
┃  ┌─────────────────────────────────────────────────┐    ┃
┃  │  Database Layer (shared/models/)                │    ┃
┃  ├─────────────────────────────────────────────────┤    ┃
┃  │                                                 │    ┃
┃  │  • MetadatosDC              (13 fields)         │    ┃
┃  │  • MetadatosEnriquecidos    (proposals)         │    ┃
┃  │  • InstrumentoProcesado     (FK reference)      │    ┃
┃  │  • Usuario                  (creator)           │    ┃
┃  │                                                 │    ┃
┃  └─────────────────┬───────────────────────────────┘    ┃
┃                    │                                     ┃
┃                    ↓                                     ┃
┃  ┌─────────────────────────────────────────────────┐    ┃
┃  │  PostgreSQL Database                            │    ┃
┃  │  (shared with other services)                   │    ┃
┃  └─────────────────────────────────────────────────┘    ┃
┃                                                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Request Flow Diagram

### Scenario 1: Register Dublin Core Metadata

```
┌──────────┐
│ Frontend │
│ or Inst. │
│ Service  │
└────┬─────┘
     │
     │ (1) GET /metadata/{id}/init
     ├─────────────────────────────────────────────────┐
     │                                                 │
     │                               ┌─────────────┐   │
     │                               │ routers/    │   │
     │                               │ metadata.py │   │
     │                               └──────┬──────┘   │
     │                                      │          │
     │                                      ↓          │
     │                               ┌──────────────┐  │
     │                               │ DCManager.   │  │
     │                               │ get_initial_ │  │
     │                               │ data()       │  │
     │                               └──────┬───────┘  │
     │                                      │          │
     │                                      ↓          │
     │                               ┌──────────────┐  │
     │                               │ shared/db    │  │
     │                               │ Query DB     │  │
     │                               └──────┬───────┘  │
     │                                      │          │
     ├─────────────────────────────────────←┘          │
     │ (2) Returns: {dc_creator, dc_publisher, ...}    │
     │
     │ User enters: dc_title, dc_subject, dc_description, ...
     │
     │ (3) POST /metadata/{id} + request body
     ├─────────────────────────────────────────────────┐
     │                                                 │
     │                               ┌─────────────┐   │
     │                               │ routers/    │   │
     │                               │ metadata.py │   │
     │                               └──────┬──────┘   │
     │                                      │          │
     │                                      ↓          │
     │                               ┌──────────────┐  │
     │                               │ DCManager.   │  │
     │                               │ register_dc()│  │
     │                               └──────┬───────┘  │
     │                                      │          │
     │                        ┌─────────────┴───────┐  │
     │                        ↓                     ↓  │
     │                ┌────────────────┐   ┌────────────────┐
     │                │ Auto-fill (6):  │   │ Validate (7):   │
     │                │ • dc_creator    │   │ • dc_title     │
     │                │ • dc_publisher  │   │ • dc_subject   │
     │                │ • dc_type       │   │ • dc_description
     │                │ • dc_format     │   │ • dc_coverage  │
     │                │ • dc_date       │   │ • dc_rights    │
     │                │ • dc_language   │   │ • dc_source    │
     │                │                 │   │ • dc_relation  │
     │                └────────┬────────┘   └────────┬───────┘
     │                         │                    │
     │                         └─────────┬──────────┘
     │                                   ↓
     │                        ┌─────────────────┐
     │                        │ Create record:  │
     │                        │ MetadatosDC     │
     │                        │ (13 fields)     │
     │                        └────────┬────────┘
     │                                 ↓
     │                        ┌─────────────────┐
     │                        │ Update state:   │
     │                        │ metadata_       │
     │                        │ registrado      │
     │                        └────────┬────────┘
     │                                 ↓
     │                        ┌─────────────────┐
     │                        │ Commit to DB    │
     │                        └────────┬────────┘
     │                                 │
     ├─────────────────────────────────┘
     │ (4) Success: {all 13 fields, estado: "metadata_registrado"}
     ↓
  ✅ Done
```

---

### Scenario 2: Enrichment Workflow

```
┌──────────────────────┐
│ Analysis Service     │
│ (LLM completes)      │
└──────────┬───────────┘
           │
           │ (1) POST /enrichment/{id}/create
           │     + proposals from LLM
           │
           ├──────────────────────────┐
           │                          ↓
           │            ┌──────────────────────┐
           │            │ routers/enrichment.py│
           │            └──────────┬───────────┘
           │                       ↓
           │            ┌──────────────────────┐
           │            │ EnrichmentEngine.    │
           │            │ create_proposals()   │
           │            └──────────┬───────────┘
           │                       ↓
           │            ┌──────────────────────┐
           │            │ Store proposals in DB│
           │            │ estado="pendiente"   │
           │            └──────────┬───────────┘
           │                       │
           ├───────────────────────┘
           │ (2) Success: {n_proposals: 3}
           │
           │
┌──────────┴──────────┐
│ Frontend User       │
│ (reviews proposals) │
└──────────┬──────────┘
           │
           │ (3) GET /enrichment/{id}
           │
           ├──────────────────────────┐
           │                          ↓
           │            ┌──────────────────────┐
           │            │ routers/enrichment.py│
           │            └──────────┬───────────┘
           │                       ↓
           │            ┌──────────────────────┐
           │            │ EnrichmentEngine.    │
           │            │ get_proposals()      │
           │            └──────────┬───────────┘
           │                       ↓
           │            ┌──────────────────────┐
           │            │ Query proposals + DB │
           │            │ (filter by status)   │
           │            └──────────┬───────────┘
           │                       │
           ├───────────────────────┘
           │ (4) Returns: [{proposal1}, {proposal2}, ...]
           │     with: tipo, valor, confianza, estado
           │
           │ User clicks: ✅ Accept / ❌ Reject
           │
           │ (5) POST /enrichment/{id}/approve
           │     + decisions: {p_id: "aceptada", ...}
           │
           ├──────────────────────────┐
           │                          ↓
           │            ┌──────────────────────┐
           │            │ routers/enrichment.py│
           │            └──────────┬───────────┘
           │                       ↓
           │            ┌──────────────────────┐
           │            │ EnrichmentEngine.    │
           │            │ approve_proposals()  │
           │            └──────────┬───────────┘
           │                       │
           │        ┌──────────────┴──────────────┐
           │        ↓                             ↓
           │   ┌─────────────┐   ┌─────────────────┐
           │   │ Update DB:  │   │ Materialize:    │
           │   │ proposal    │   │ accepted into   │
           │   │ estados     │   │ MetadatosEnr... │
           │   └──────┬──────┘   └────────┬────────┘
           │          │                  │
           │          └──────────┬───────┘
           │                     ↓
           │         ┌─────────────────────┐
           │         │ Update state:       │
           │         │ etl_aprobado        │
           │         └─────────┬───────────┘
           │                   ↓
           │         ┌─────────────────────┐
           │         │ Commit to DB        │
           │         └─────────┬───────────┘
           │                   │
           ├───────────────────┘
           │ (6) Success: {n_aceptadas: 2, n_rechazadas: 1}
           │
           ↓
        ✅ Done → Ready for JSON generation
```

---

## Dublin Core Fields Map

```
┌───────────────────────────────────────────────────┐
│  13 Dublin Core Fields                            │
├───────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────────────────────────────────┐    │
│  │  AUTO-FILLED (6 fields)                 │    │
│  ├─────────────────────────────────────────┤    │
│  │                                         │    │
│  │  1. dc_creator ← Authenticated user     │    │
│  │  2. dc_publisher ← APP_NAME config      │    │
│  │  3. dc_type ← instrumento.tipo          │    │
│  │  4. dc_format ← file.extension          │    │
│  │  5. dc_date ← datetime.now()            │    │
│  │  6. dc_language ← "es" (constant)       │    │
│  │                                         │    │
│  └─────────────────────────────────────────┘    │
│                                                   │
│  ┌─────────────────────────────────────────┐    │
│  │  USER INPUT (7 fields)                  │    │
│  ├─────────────────────────────────────────┤    │
│  │                                         │    │
│  │  7. dc_title                            │    │
│  │     (required)                          │    │
│  │     "Student Satisfaction Survey 2024"  │    │
│  │                                         │    │
│  │  8. dc_subject                          │    │
│  │     (required, list)                    │    │
│  │     ["education", "survey", "students"] │    │
│  │                                         │    │
│  │  9. dc_description                      │    │
│  │     (optional)                          │    │
│  │     "Annual measurement of student..."  │    │
│  │                                         │    │
│  │  10. dc_coverage                        │    │
│  │      (optional)                         │    │
│  │      "Universidad A, 2024"              │    │
│  │                                         │    │
│  │  11. dc_rights                          │    │
│  │      (optional)                         │    │
│  │      "CC-BY-4.0"                        │    │
│  │                                         │    │
│  │  12. dc_source                          │    │
│  │      (optional)                         │    │
│  │      "Original research"                │    │
│  │                                         │    │
│  │  13. dc_relation                        │    │
│  │      (optional)                         │    │
│  │      "Linked to survey #5"              │    │
│  │                                         │    │
│  └─────────────────────────────────────────┘    │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## File Dependency Graph

```
main.py
  ├─→ routers/__init__.py
  │   ├─→ routers/health.py
  │   ├─→ routers/metadata.py
  │   │   └─→ services/dc_manager.py
  │   │       └─→ shared/models/metadatos_dc.py
  │   │       └─→ shared/models/instrumento_procesado.py
  │   └─→ routers/enrichment.py
  │       └─→ services/enrichment_engine.py
  │           └─→ shared/models/instrumento_procesado.py
  └─→ shared/db/database.py
      └─→ PostgreSQL (via environment variables)
```

---

## State Transitions

```
Metadata Registration Flow:
═════════════════════════════════════════════════════════

[pendiente]
    ↓ POST /metadata/{id}
    ↓ DCManager.register_dc()
    ├─→ Create MetadatosDC (13 fields)
    └─→ Update InstrumentoProcesado
         ↓
    [metadata_registrado]
    ✅ Ready for analysis


Enrichment Approval Flow:
═════════════════════════════════════════════════════════

[etl_pendiente_limpieza]
    ↓ Analysis-service generates enrichment proposals
    ↓ POST /enrichment/{id}/create
    ↓ EnrichmentEngine.create_proposals()
    ├─→ Store in MetadatosEnriquecidos
    │   (estado_decision = "pendiente")
    │
    ↓ User reviews at GET /enrichment/{id}
    │
    ↓ User decides at POST /enrichment/{id}/approve
    ↓ EnrichmentEngine.approve_proposals()
    ├─→ Update proposal estados_decision
    ├─→ Materialize accepted enrichments
    └─→ Update InstrumentoProcesado
         ↓
    [etl_aprobado]
    ✅ Ready for JSON generation
```

---

**These diagrams should help visualize the service architecture, data flow, and state transitions!**
