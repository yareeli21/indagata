# Metadata Service - Implementation Summary

## 🎯 Service Overview

The Metadata Service manages all metadata operations for research instruments, including:
- **Dublin Core (DC) Registration** — 13 standard metadata fields
- **Enriched Metadata** — LLM-inferred contextual information
- **Approval Workflows** — User decision on enriched metadata

**Port:** 8003  
**Status:** ⚠️ Core structure complete, business logic needs integration with shared models

---

## 📁 File Structure

```
metadata-service/
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Dependencies (fastapi, sqlalchemy, etc.)
├── models.py                   # (Empty) Local ORM models if needed
├── routers/
│   ├── __init__.py            # Router exports
│   ├── health.py              # /health, /health/ready endpoints
│   ├── metadata.py            # Dublin Core CRUD endpoints
│   └── enrichment.py          # Enriched metadata endpoints
├── services/
│   ├── __init__.py            # Service exports
│   ├── dc_manager.py          # Dublin Core business logic
│   └── enrichment_engine.py   # Enrichment proposals logic
└── IMPLEMENTATION_GUIDE.md    # Detailed architecture guide
```

---

## 🚀 File Descriptions

### **main.py** ✅
**Status:** Complete  
**Purpose:** FastAPI service initialization  
**Key Components:**
- Imports all routers (health, metadata, enrichment)
- Configures CORS middleware
- Sets up database initialization on startup
- Defines lifespan (startup/shutdown hooks)

**Port Configuration:** 8003 (hardcoded, set by docker-compose)

### **routers/health.py** ✅
**Status:** Complete  
**Endpoints:**
- `GET /health` → Simple "ok" status (Docker liveness)
- `GET /health/ready` → Database connectivity check (Docker readiness)
- `GET /health/live` → Alternative liveness probe

### **routers/metadata.py** ✅
**Status:** Complete (Skeleton)  
**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/metadata/{id}/init` | Pre-populate form (auto-filled fields) |
| POST | `/metadata/{id}` | Register 13 DC fields (immutable) |
| GET | `/metadata/{id}` | Retrieve DC metadata |
| GET | `/metadata` | List all metadata (paginated) |
| DELETE | `/metadata/{id}` | Delete metadata (cleanup) |

**Key Feature:** Immutability — Once registered, cannot be updated. Returns 409 on second registration.

### **routers/enrichment.py** ✅
**Status:** Complete (Skeleton)  
**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/enrichment/{id}/create` | Create proposals (from analysis-service) |
| GET | `/enrichment/{id}` | View proposals (for user review) |
| POST | `/enrichment/{id}/approve` | Submit accept/reject decisions |
| GET | `/enrichment/{id}/summary` | Get approval statistics |

### **services/dc_manager.py** ✅
**Status:** 80% Complete (Needs model integration)  
**Class:** `DCManager`  
**Methods:**

```python
DCManager.get_initial_data(db, instrumento_id)
  # Returns auto-filled fields for form initialization
  # Fields: creator, publisher, type, format, date, language

DCManager.register_dc(db, instrumento_id, request)
  # Registers all 13 Dublin Core fields
  # Enforces immutability
  # Updates instrument state to "metadata_registrado"

DCManager.get_dc(db, instrumento_id)
  # Retrieves DC metadata

DCManager.list_dc(db, skip=0, limit=20)
  # Lists all metadata with pagination

DCManager.delete_dc(db, instrumento_id)
  # Deletes metadata for cleanup
```

**13 Dublin Core Fields:**
1. **dc_title** (user) — Instrument title
2. **dc_creator** (auto) — User who registered
3. **dc_subject** (user) — Keywords/topics
4. **dc_description** (user) — Detailed description
5. **dc_publisher** (auto) — App name (Indagata)
6. **dc_date** (auto) — Registration date
7. **dc_type** (auto) — Instrument type (encuesta/entrevista/prueba_estandarizada)
8. **dc_format** (auto) — File extension
9. **dc_language** (auto) — "es" (Spanish)
10. **dc_coverage** (user) — Geographic/temporal coverage
11. **dc_rights** (user) — Usage rights
12. **dc_source** (user) — Original source
13. **dc_relation** (user) — Related instruments

### **services/enrichment_engine.py** ✅
**Status:** 50% Complete (Skeleton)  
**Class:** `EnrichmentEngine`  
**Methods:**

```python
EnrichmentEngine.create_proposals(db, instrumento_id, proposals)
  # Store enrichment proposals from LLM
  # proposals: List[dict] with tipo, valor, confianza, descripcion

EnrichmentEngine.get_proposals(db, instrumento_id, filter_status=None)
  # Retrieve proposals for user review
  # filter_status: "pendiente" | "aceptada" | "rechazada"

EnrichmentEngine.approve_proposals(db, instrumento_id, decisions)
  # Apply user decisions
  # decisions: {proposal_id: "aceptada" | "rechazada", ...}
  # Updates instrument state to "etl_aprobado"

EnrichmentEngine.get_summary(db, instrumento_id)
  # Get approval statistics
```

---

## 📊 Data Flow

### **Phase 1: Metadata Registration**
```
Frontend/Instrument-Service
    ↓
GET /metadata/{id}/init
    ↓ (returns pre-filled fields)
Display Form
    ↓
User enters 7 manual fields
    ↓
POST /metadata/{id}
    ↓ (with 7 user-provided fields)
DCManager.register_dc()
    ↓
Create MetadatosDC record in DB (13 fields total)
    ↓
Update InstrumentoProcesado.estado → "metadata_registrado"
    ↓
Return success response
```

### **Phase 2: Enrichment (After Analysis)**
```
Analysis-Service completes LLM processing
    ↓
POST /enrichment/{id}/create
    ↓ (with proposals from LLM)
EnrichmentEngine.create_proposals()
    ↓
Store proposals in DB (estado_decision = "pendiente")
    ↓
Return proposal count
```

### **Phase 3: Enrichment Approval**
```
Frontend displays proposals
    ↓
GET /enrichment/{id}
    ↓ (returns all proposals)
User reviews and decides
    ↓
POST /enrichment/{id}/approve
    ↓ (with accept/reject decisions)
EnrichmentEngine.approve_proposals()
    ↓
Update proposal states
    ↓
Materialize accepted enrichments
    ↓
Update InstrumentoProcesado.estado → "etl_aprobado"
    ↓
Return success
```

---

## ✅ Implementation Status

### Completed ✅
- [x] File structure created
- [x] `main.py` with full routing
- [x] `routers/health.py` with health checks
- [x] `routers/metadata.py` with CRUD endpoints
- [x] `routers/enrichment.py` with proposal endpoints
- [x] `services/dc_manager.py` core logic (80%)
- [x] `services/enrichment_engine.py` skeleton (50%)
- [x] All `__init__.py` files
- [x] Comprehensive documentation

### TODO 🔄
- [ ] **Integrate with shared models:**
  - [ ] Import `InstrumentoProcesado` from `shared.models`
  - [ ] Import `MetadatosDC` from `shared.models`
  - [ ] Create `MetadatosEnriquecidos` model if not exists
  
- [ ] **Complete enrichment_engine.py:**
  - [ ] Implement proposal creation with DB storage
  - [ ] Implement proposal retrieval with filtering
  - [ ] Implement materialization logic
  - [ ] Implement summary statistics

- [ ] **Error Handling:**
  - [ ] Add detailed validation errors
  - [ ] Add transaction rollback on failures
  - [ ] Add logging for debugging

- [ ] **Testing:**
  - [ ] Unit tests for DCManager
  - [ ] Unit tests for EnrichmentEngine
  - [ ] Integration tests with shared models
  - [ ] E2E tests through API

- [ ] **Optimization:**
  - [ ] Add caching for frequently-accessed metadata
  - [ ] Add database indexes on instrumento_id
  - [ ] Consider pagination for large enrichment lists

---

## 🔌 Inter-Service Communication

### Calls FROM instrument-service:
```
GET /metadata/{id}/init
→ Initialize metadata form

POST /metadata/{id}
→ Register Dublin Core metadata
```

### Calls FROM analysis-service:
```
POST /enrichment/{id}/create
→ Store enrichment proposals after LLM analysis
```

### Calls FROM frontend/visualization-service:
```
GET /metadata/{id}
→ Display metadata in instrument details

GET /enrichment/{id}
→ Show proposals for approval
```

---

## 🧪 Testing the Service

### Health Check
```bash
curl http://localhost:8003/health
# Expected: {"status": "ok", "service": "metadata-service"}

curl http://localhost:8003/health/ready
# Expected: {"ready": true, "service": "metadata-service", "checks": {"database": "ok"}}
```

### Swagger UI
```
http://localhost:8003/docs
```

### Register Metadata
```bash
curl -X POST http://localhost:8003/api/metadata/1 \
  -H "Content-Type: application/json" \
  -d '{
    "dc_title": "Student Satisfaction Survey",
    "dc_subject": ["education", "survey", "satisfaction"],
    "dc_description": "Annual survey for student satisfaction",
    "dc_coverage": "University A, 2024",
    "dc_rights": "CC-BY-4.0",
    "dc_creator": "admin",
    "dc_source": null,
    "dc_relation": null
  }'
```

---

## 🐳 Docker Build & Run

```bash
# Build just this service
docker compose build metadata-service

# Start with dependencies
docker compose up metadata-service postgres

# View logs
docker compose logs -f metadata-service

# Test endpoint
curl http://localhost:8003/health
```

---

## 📝 Next Steps

1. **Integrate with shared models** — Ensure all imports work correctly
2. **Complete enrichment_engine.py** — Implement proposal storage/retrieval
3. **Add database migrations** — Create enrichment tables if needed
4. **Write unit tests** — Test each service method
5. **E2E testing** — Test full workflow through all services

---

## 📞 Support

For detailed architecture and design decisions, see `IMPLEMENTATION_GUIDE.md`

For shared models and schemas, see `shared/models/` and `shared/schemas/`

For the complete workflow, see the main project README
