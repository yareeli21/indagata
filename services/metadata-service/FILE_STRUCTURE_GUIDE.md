# 🏗️ Metadata Service - Complete File Structure & Purpose Guide

## Overview

```
metadata-service/
├── main.py                           ← FastAPI app initialization
├── models.py                         ← (Optional) Local ORM extensions
├── requirements.txt                  ← Python dependencies
├── README.md                         ← Service overview & testing
├── IMPLEMENTATION_GUIDE.md           ← Detailed architecture guide
├── routers/
│   ├── __init__.py                   ← Export all routers
│   ├── health.py                     ← /health & /health/ready endpoints
│   ├── metadata.py                   ← Dublin Core CRUD endpoints
│   └── enrichment.py                 ← Enrichment proposal endpoints
└── services/
    ├── __init__.py                   ← Export DCManager & EnrichmentEngine
    ├── dc_manager.py                 ← Dublin Core business logic
    └── enrichment_engine.py          ← Enrichment proposal logic
```

---

## 📝 File-by-File Breakdown

### **1. main.py** — Service Entry Point
```
┌─────────────────────────────────────┐
│  FastAPI Application Initialization │
└─────────────────────────────────────┘
         ↓
    ┌─────────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓
[Logger]  [CORS]   [Database]  [Routers]
    ↓         ↓         ↓         ↓
    └─────────┴─────────┴─────────┘
         ↓
   ✅ Ready on port 8003
```

**Contains:**
- FastAPI app creation
- CORS middleware configuration
- Database initialization
- Router registration
- Lifespan (startup/shutdown) hooks
- Uvicorn entry point for `docker run`

**When to use:** 
- Never manually edit unless changing app configuration
- Auto-generated most settings from environment variables

---

### **2. requirements.txt** — Dependencies
```
fastapi           → Web framework
uvicorn           → ASGI server
sqlalchemy        → ORM
psycopg[binary]   → PostgreSQL driver
pydantic          → Data validation
python-dotenv     → Environment config
```

**When to modify:**
- Add new libraries (e.g., validation, serialization)
- Update versions for security patches

---

### **3. routers/__init__.py** — Router Exports
```python
from .health import router as health_router
from .metadata import router as metadata_router
from .enrichment import router as enrichment_router

__all__ = [...]
```

**Purpose:** Make routers importable as: `from routers import health, metadata, enrichment`

**Never manually edit:**
- Auto-maintained, just add new routers as needed

---

### **4. routers/health.py** — Health Checks
```
┌──────────────────┐
│  Health Probes   │
├──────────────────┤
│ GET /health      │ → {"status": "ok"}
│ GET /health/ready│ → {"ready": true, db: "ok"}
│ GET /health/live │ → {"status": "alive"}
└──────────────────┘
```

**Purpose:**
- **Liveness Probe** (`/health`) — Is the service running?
- **Readiness Probe** (`/health/ready`) — Can it handle requests? (checks DB)
- Used by Docker/Kubernetes to monitor service health

**When to modify:**
- Add more health checks (cache, external APIs, etc.)
- Improve error reporting

---

### **5. routers/metadata.py** — Dublin Core CRUD

```
┌──────────────────────────────────────────────────┐
│       Dublin Core Metadata API Endpoints         │
├──────────────────────────────────────────────────┤
│ GET    /metadata/{id}/init                       │
│ POST   /metadata/{id}          [Register]        │
│ GET    /metadata/{id}                            │
│ GET    /metadata               [List all]        │
│ DELETE /metadata/{id}          [Cleanup]         │
└──────────────────────────────────────────────────┘
         ↓
    All route to DCManager for business logic
```

**13 Dublin Core Fields:**

| Field | Source | Example |
|-------|--------|---------|
| dc_title | User | "Student Satisfaction Survey 2024" |
| dc_creator | Auto | "admin" |
| dc_subject | User | ["education", "survey"] |
| dc_description | User | "Annual student satisfaction measurement" |
| dc_publisher | Auto | "Indagata" |
| dc_date | Auto | "2024-01-15" |
| dc_type | Auto | "encuesta" |
| dc_format | Auto | "xlsx" |
| dc_language | Auto | "es" |
| dc_coverage | User | "University A, 2024" |
| dc_rights | User | "CC-BY-4.0" |
| dc_source | User | "Original research" |
| dc_relation | User | "Linked to survey #3" |

**Key Feature:** **IMMUTABLE** — Once registered (POST), cannot be changed. Prevents data inconsistency.

---

### **6. routers/enrichment.py** — Enrichment Workflow

```
┌──────────────────────────────────────────────────┐
│     Enriched Metadata Proposal Endpoints         │
├──────────────────────────────────────────────────┤
│ POST   /enrichment/{id}/create                   │
│        ↓ Called by analysis-service after LLM   │
│        ↓ Stores proposals: pendiente → pending   │
│                                                   │
│ GET    /enrichment/{id}                          │
│        ↓ User reviews proposals                  │
│        ↓ Returns: pendiente, aceptada, rechazada │
│                                                   │
│ POST   /enrichment/{id}/approve                  │
│        ↓ User submits accept/reject decisions    │
│        ↓ Materializes accepted enrichments       │
│        ↓ Updates state → etl_aprobado            │
│                                                   │
│ GET    /enrichment/{id}/summary                  │
│        ↓ Statistics on approval progress         │
└──────────────────────────────────────────────────┘
```

**Enrichment Workflow:**
1. **Proposal Storage** (after LLM analysis)
2. **User Review** (see all proposals)
3. **User Decision** (accept/reject each)
4. **Materialization** (store accepted ones)

---

### **7. services/__init__.py** — Service Exports

```python
from .dc_manager import DCManager
from .enrichment_engine import EnrichmentEngine

__all__ = ["DCManager", "EnrichmentEngine"]
```

**Purpose:** Make services importable as: `from services import DCManager, EnrichmentEngine`

---

### **8. services/dc_manager.py** — Dublin Core Logic

```
┌─────────────────────────────────────────┐
│     DCManager (Static Methods)           │
├─────────────────────────────────────────┤
│ get_initial_data(db, id)                │
│   → {dc_creator, dc_publisher, ...}     │
│                                          │
│ register_dc(db, id, request)            │
│   → Create MetadatosDC (13 fields)      │
│   → Enforce immutability                │
│   → Update state → metadata_registrado   │
│                                          │
│ get_dc(db, id)                          │
│   → Retrieve all 13 fields              │
│                                          │
│ list_dc(db, skip, limit)                │
│   → Paginated list                      │
│                                          │
│ delete_dc(db, id)                       │
│   → Remove (cleanup only)               │
└─────────────────────────────────────────┘
```

**Core Responsibility:**
- Auto-fill 6 fields (creator, publisher, type, format, date, language)
- Validate 7 user-provided fields
- Enforce **immutability** (1x registration per instrument)
- Update instrument state transitions
- Database CRUD operations

**Database Model:** `shared.models.metadatos_dc.MetadatosDC`

---

### **9. services/enrichment_engine.py** — Enrichment Logic

```
┌──────────────────────────────────────────┐
│    EnrichmentEngine (Static Methods)     │
├──────────────────────────────────────────┤
│ create_proposals(db, id, proposals)      │
│   ← Receives from analysis-service       │
│   → Store as "pendiente"                 │
│                                           │
│ get_proposals(db, id, filter_status)    │
│   → List for user review                 │
│   → Optional filter                      │
│                                           │
│ approve_proposals(db, id, decisions)     │
│   ← Receives user accept/reject          │
│   → Update states                        │
│   → Materialize accepted               │
│   → Update state → etl_aprobado          │
│                                           │
│ get_summary(db, id)                      │
│   → Approval statistics                  │
└──────────────────────────────────────────┘
```

**Core Responsibility:**
- Store LLM-generated enrichment proposals
- Track approval decisions
- Materialize accepted enrichments
- Update workflow state

**Status:** 50% complete (skeleton provided, needs DB integration)

---

## 🔄 Data Flow Through Service

### **Scenario 1: User Registers Metadata**
```
Frontend User
    ↓ clicks "Register Metadata"
GET /metadata/{id}/init
    ↓ [routers/metadata.py]
DCManager.get_initial_data()
    ↓ [services/dc_manager.py]
Query MetadatosDC from DB
    ↓
Return: {dc_creator, dc_publisher, dc_type, ...}
    ↓
Frontend shows form with auto-filled fields
    ↓ User enters dc_title, dc_subject, etc.
POST /metadata/{id}
    ↓ [routers/metadata.py with request body]
DCManager.register_dc()
    ↓ [services/dc_manager.py]
  1. Check immutability (already registered?)
  2. Auto-fill 6 fields
  3. Create MetadatosDC record
  4. Update InstrumentoProcesado.estado
  5. Commit to DB
    ↓
Return: {all 13 fields, estado: "metadata_registrado"}
    ↓
✅ Frontend: "Metadata registered! Ready for analysis."
```

### **Scenario 2: Analysis Service Sends Enrichment Proposals**
```
Analysis Service (analysis-service:8002)
    ↓ Completes LLM processing
POST /enrichment/{id}/create
    ↓ [routers/enrichment.py with proposals]
EnrichmentEngine.create_proposals()
    ↓ [services/enrichment_engine.py]
  1. Verify instrument exists
  2. Store proposals (estado = "pendiente")
  3. Return success
    ↓
Response: {n_proposals: 3, status: "created"}
    ↓
✅ Analysis Service: "Enrichment proposals stored"
```

### **Scenario 3: User Approves Enrichment**
```
Frontend User
    ↓ reviews enrichment proposals
GET /enrichment/{id}
    ↓ [routers/enrichment.py]
EnrichmentEngine.get_proposals()
    ↓ [services/enrichment_engine.py]
Query proposals from DB
    ↓
Return: [proposal1, proposal2, ...] with states
    ↓
Frontend shows approve/reject buttons
    ↓ User clicks decisions
POST /enrichment/{id}/approve
    ↓ [routers/enrichment.py with decisions dict]
EnrichmentEngine.approve_proposals()
    ↓ [services/enrichment_engine.py]
  1. Verify state is "etl_pendiente_enriquecimiento"
  2. Update proposal estados_decision
  3. Materialize accepted enrichments
  4. Update InstrumentoProcesado.estado → "etl_aprobado"
  5. Commit to DB
    ↓
Return: {n_aceptadas: 2, n_rechazadas: 1}
    ↓
✅ Frontend: "Enrichment approved! Ready for JSON generation."
```

---

## 🧩 Integration Points with Other Services

### From **instrument-service**:
```
GET /metadata/{id}/init          ← Initialize form before registration
POST /metadata/{id}              ← Register metadata after upload
```

### From **analysis-service**:
```
POST /enrichment/{id}/create     ← Send enrichment proposals after LLM
```

### From **visualization-service**:
```
GET /metadata/{id}               ← Fetch for display
GET /enrichment/{id}             ← Show in details view
```

### From **frontend**:
```
GET /metadata/{id}/init
POST /metadata/{id}
GET /enrichment/{id}
POST /enrichment/{id}/approve
```

---

## ✅ Checklist for Completing Implementation

- [x] File structure created
- [x] All endpoint skeletons implemented
- [x] Core business logic 80% complete
- [ ] **TODO:** Integrate shared models
- [ ] **TODO:** Complete enrichment storage
- [ ] **TODO:** Add database migrations
- [ ] **TODO:** Write unit tests
- [ ] **TODO:** E2E testing

---

## 🚀 Quick Test

```bash
# Build
docker compose build metadata-service

# Run with dependencies
docker compose up -d postgres redis metadata-service

# Test health
curl http://localhost:8003/health
# Expected: {"status": "ok", "service": "metadata-service"}

# View API docs
open http://localhost:8003/docs

# Stop
docker compose down
```

---

## 📖 Documentation Files

- **README.md** — Overview, testing, deployment
- **IMPLEMENTATION_GUIDE.md** — Detailed architecture & design
- **This file** — File structure & purpose guide

---

**Status:** ✅ Structure complete, ⏳ Ready for model integration and enrichment completion
