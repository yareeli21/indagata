# 🎓 Metadata Service - Building Guide Summary

## Where to Start

You now have a **complete skeleton** for the metadata-service. Here's the recommended approach:

---

## 📍 Current State

| Component | Status | Effort |
|-----------|--------|--------|
| **Structure** | ✅ Complete | Done |
| **Routers (endpoints)** | ✅ Complete | Done |
| **Health checks** | ✅ Complete | Done |
| **DC Manager logic** | ⚠️ 80% | 1-2 hours |
| **Enrichment Engine** | ⚠️ 50% | 2-3 hours |
| **Model integration** | ❌ TODO | 1 hour |
| **Testing** | ❌ TODO | 3-4 hours |

**Total remaining: 7-10 hours**

---

## 🎯 What Each File Does

### **Core Files (Already Complete)**

1. **main.py** ✅
   - Initializes FastAPI app
   - Loads all routers
   - Sets up database on startup
   - Ready to use—don't modify

2. **routers/health.py** ✅
   - `/health` — liveness probe
   - `/health/ready` — readiness probe
   - Used by Docker for health monitoring
   - Complete—don't modify

3. **routers/metadata.py** ✅
   - 5 endpoints for Dublin Core CRUD
   - Routes to `DCManager` for business logic
   - Complete—don't modify

4. **routers/enrichment.py** ✅
   - 4 endpoints for enrichment workflow
   - Routes to `EnrichmentEngine` for business logic
   - Complete—don't modify

### **Business Logic Files (Partial)**

5. **services/dc_manager.py** ⚠️ 80% Complete
   - Core Dublin Core registration logic
   - **Needs:** Import and test with shared models
   - **Effort:** 1-2 hours

6. **services/enrichment_engine.py** ⚠️ 50% Complete
   - Skeleton for enrichment proposals
   - **Needs:** Complete proposal storage/retrieval
   - **Effort:** 2-3 hours

---

## 📋 Step-by-Step Implementation

### **Step 1: Verify Everything Builds (30 mins)**

```bash
# Check files exist
ls -la services/metadata-service/

# Try building the service
docker compose build metadata-service

# Should succeed without errors
```

If build fails → Check logs and fix imports

### **Step 2: Test Basic Health (15 mins)**

```bash
# Start dependencies
docker compose up -d postgres redis

# Start metadata-service
docker compose up -d metadata-service

# Check health
curl http://localhost:8003/health
# Expected: {"status": "ok", "service": "metadata-service"}

curl http://localhost:8003/health/ready
# Expected: {"ready": true, ...}
```

If fails → Check database connectivity

### **Step 3: Verify Shared Model Integration (1 hour)**

**File:** `services/metadata-service/services/dc_manager.py`

Currently it has placeholder imports:
```python
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.metadatos_dc import MetadatosDC
```

**Action:**
1. Check `shared/models/` to confirm these exist
2. Run `python -c "from shared.models.instrumento_procesado import InstrumentoProcesado"` to verify
3. If import fails → Fix the import path
4. If module doesn't exist → Create it based on the models list you have

### **Step 4: Test Metadata Registration Endpoint (1 hour)**

**File:** `services/metadata-service/routers/metadata.py`

```bash
# With service running, test:

# 1. Get initial data (should work immediately)
curl http://localhost:8003/api/metadata/1/init

# 2. Register metadata
curl -X POST http://localhost:8003/api/metadata/1 \
  -H "Content-Type: application/json" \
  -d '{
    "dc_title": "Test Survey",
    "dc_subject": ["test"],
    "dc_description": "Test description",
    "dc_coverage": "Test",
    "dc_rights": "CC-BY",
    "dc_creator": "test",
    "dc_source": null,
    "dc_relation": null
  }'

# 3. Retrieve metadata
curl http://localhost:8003/api/metadata/1
```

If any fails → Check logs: `docker compose logs metadata-service`

### **Step 5: Complete Enrichment Engine (2-3 hours)**

**File:** `services/metadata-service/services/enrichment_engine.py`

Currently it's a skeleton. You need to:

1. **Create enrichment proposal storage:**
   ```python
   def create_proposals(db, instrumento_id, proposals):
       # TODO: Actually store proposals in DB
       # Create records for each proposal with estado_decision = "pendiente"
   ```

2. **Implement proposal retrieval:**
   ```python
   def get_proposals(db, instrumento_id, filter_status=None):
       # TODO: Query from DB
       # Filter by status if provided
   ```

3. **Implement approval logic:**
   ```python
   def approve_proposals(db, instrumento_id, decisions):
       # TODO: Update proposal estados_decision
       # TODO: Materialize accepted ones
       # TODO: Update instrument state
   ```

### **Step 6: Add Database Migrations (If needed)**

Check if enrichment tables exist:
```bash
psql -h localhost -U postgres -d indagata_db -c "\dt"
```

If enrichment tables missing → Create migrations in `infrastructure/postgres/migrations/`

### **Step 7: Write Unit Tests (3-4 hours)**

Create `tests/test_dc_manager.py` and `tests/test_enrichment_engine.py`

---

## 📁 File Reading Order

When building, read files in this order:

1. **main.py** — Understand app structure
2. **routers/health.py** — See endpoint pattern
3. **routers/metadata.py** — Learn CRUD pattern
4. **routers/enrichment.py** — Learn workflow pattern
5. **services/dc_manager.py** — Core business logic
6. **services/enrichment_engine.py** — Enrichment logic

---

## 💾 Database Model Dependencies

These **must exist** in `shared/models/`:

| Model | Purpose | File |
|-------|---------|------|
| `InstrumentoProcesado` | Instrument record | `shared/models/instrumento_procesado.py` |
| `MetadatosDC` | 13 DC fields | `shared/models/metadatos_dc.py` |
| `MetadatosEnriquecidos` | Enrichment proposals | ??? (check if exists) |
| `Usuario` | User record | `shared/models/usuario.py` |

**Action:** Verify all exist by checking the files list.

---

## 🧪 Testing Strategy

### Unit Tests
```bash
# Test DCManager in isolation
pytest tests/test_dc_manager.py

# Test EnrichmentEngine in isolation
pytest tests/test_enrichment_engine.py
```

### Integration Tests
```bash
# Test full workflow through API
pytest tests/test_integration.py
```

### Manual Testing
```bash
# Use Swagger UI
http://localhost:8003/docs

# Or use curl commands (examples below)
```

---

## 🔍 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'shared'` | Path not set | Add to `sys.path` in main.py ✅ (already done) |
| `No such table: metadatos_dc` | Table doesn't exist | Run migrations in `infrastructure/postgres/migrations/` |
| `Port 8003 already in use` | Service already running | `docker compose down` then restart |
| `Connection refused` | PostgreSQL not running | `docker compose up -d postgres` |
| `JSONDecodeError` | Response not JSON | Check `Content-Type: application/json` header |

---

## ✨ Success Criteria

- [x] All files created and organized
- [x] Service builds without errors
- [x] `/health` endpoint returns 200
- [ ] Can register metadata without errors
- [ ] Can retrieve registered metadata
- [ ] Can create enrichment proposals
- [ ] Can approve/reject enrichment
- [ ] Full workflow works end-to-end
- [ ] Tests pass

---

## 📞 Quick Reference

### Files by Purpose

**Entry Point:**
- `main.py` — App initialization

**HTTP Endpoints:**
- `routers/health.py` — Health checks
- `routers/metadata.py` — DC CRUD
- `routers/enrichment.py` — Enrichment workflow

**Business Logic:**
- `services/dc_manager.py` — DC registration
- `services/enrichment_engine.py` — Enrichment proposals

**Configuration:**
- `requirements.txt` — Dependencies
- `.env` (root) — Environment variables

**Documentation:**
- `README.md` — Service overview
- `IMPLEMENTATION_GUIDE.md` — Architecture details
- `FILE_STRUCTURE_GUIDE.md` — Visual guide
- **This file** — Building guide

---

## 🎯 Next Actions

1. **TODAY (2 hours):**
   - Build and test health endpoints
   - Verify shared model imports

2. **TOMORROW (4 hours):**
   - Complete enrichment_engine.py
   - Test metadata registration workflow

3. **NEXT DAY (2-3 hours):**
   - Write unit tests
   - Fix any issues found

4. **FINAL:**
   - E2E testing with full stack
   - Deploy to production

---

## 📚 Related Documentation

- `IMPLEMENTATION_GUIDE.md` — Detailed architecture
- `FILE_STRUCTURE_GUIDE.md` — Visual file descriptions
- `README.md` — Testing & deployment

---

**You're ready to go! Start with step 1 and work through systematically. Good luck! 🚀**
