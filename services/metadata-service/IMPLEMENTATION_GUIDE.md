# 📋 Metadata Service - Complete Implementation Guide

## Service Overview

**Purpose:** Manages all metadata operations for instruments  
**Port:** 8003  
**Responsibility:** Dublin Core metadata registration, enrichment, and retrieval  
**Interaction:** Central part of the instrument processing pipeline

---

## 📁 File Structure & Descriptions

### **1. `main.py` — FastAPI Entry Point**

**Purpose:** Service initialization and routing  
**Content:**
- FastAPI app configuration
- CORS middleware setup
- Router registration
- Lifespan management (startup/shutdown)
- Uvicorn entry point

**Key Components:**
```python
- Import logging setup
- Import database initialization
- Import all routers (health, metadata, enrichment)
- Create FastAPI instance with lifespan
- Add CORS middleware
- Include routers with prefixes
```

**When to modify:** When adding new routes or changing startup behavior

---

### **2. `requirements.txt` — Dependencies**

**Current (already complete):**
```
fastapi==0.115.6
uvicorn[standard]==0.30.0
sqlalchemy==2.0.25
psycopg[binary]==3.2.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
```

**Purpose:** Declare service-specific Python dependencies

**When to modify:** When adding new functionality (e.g., validation libraries)

---

### **3. `models.py` — SQLAlchemy ORM Models (Local)**

**Purpose:** Define metadata-specific database models  
**Content:**
- Model classes for this service's tables
- Relationships to shared models
- Validation rules at ORM level

**Models to include:**
- `MetadatosDC` — Dublin Core metadata (13 fields)
- `MetadatosEnriquecidos` — Enriched metadata (optional, contextual)
- Any local-only models for metadata operations

**Note:** Shared models live in `shared/models/`, not here. This file is for service-specific extensions only.

**When to modify:** When schema changes occur

---

### **4. `routers/__init__.py` — Router Module Exports**

**Purpose:** Make all routers accessible from `routers` package  
**Content:**
```python
from .health import router as health_router
from .metadata import router as metadata_router
from .enrichment import router as enrichment_router

__all__ = ["health_router", "metadata_router", "enrichment_router"]
```

**When to modify:** When adding a new router file

---

### **5. `routers/health.py` — Health Check Endpoints**

**Purpose:** Service liveness & readiness probes (Docker/K8s)  
**Content:**

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    """Liveness probe - simple status check"""
    return {"status": "ok", "service": "metadata-service"}

@router.get("/health/ready")
async def readiness():
    """Readiness probe - check dependencies (DB, etc.)"""
    # Test DB connection
    try:
        from shared.db import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"ready": True, "service": "metadata-service"}
    except Exception as e:
        return {"ready": False, "error": str(e)}, 503
```

**Endpoints:**
- `GET /health` — Always returns 200 if service is running
- `GET /health/ready` — Returns 200 only if DB is reachable

**When to modify:** When adding new dependencies to check

---

### **6. `routers/metadata.py` — Dublin Core CRUD Endpoints**

**Purpose:** Main API for metadata management  
**Content:**

**Endpoints to implement:**

```python
@router.post("/metadata")
async def register_metadata(instrumento_id: int, request: MetadataRequest):
    """
    Register Dublin Core metadata (13 fields).
    6 fields auto-completed, 7 fields from user input.
    Immutable: second call returns 409 Conflict.
    """

@router.get("/metadata/{instrumento_id}")
async def get_metadata(instrumento_id: int):
    """Retrieve Dublin Core metadata for an instrument"""

@router.get("/metadata/{instrumento_id}/init")
async def get_metadata_init(instrumento_id: int):
    """Get pre-populated fields for form initialization"""

@router.put("/metadata/{instrumento_id}")
async def update_metadata(instrumento_id: int, request: MetadataUpdateRequest):
    """Update specific metadata fields (if allowed)"""

@router.delete("/metadata/{instrumento_id}")
async def delete_metadata(instrumento_id: int):
    """Delete metadata (admin only, optional)"""
```

**Schemas needed:**
- `MetadataRequest` — Input schema (7 manual fields)
- `MetadataResponse` — Output schema (13 complete fields)
- `MetadataInitialData` — Pre-populated data for form

**Database operations:**
- Query `MetadatosDC` by `instrumento_id`
- Create/Read/Update/Delete operations
- Validate immutability rules

**When to modify:** When Dublin Core standard changes or new fields needed

---

### **7. `routers/enrichment.py` — Enriched Metadata Endpoints**

**Purpose:** Handle enriched metadata (post-analysis)  
**Content:**

**Endpoints:**

```python
@router.post("/enrichment/{instrumento_id}")
async def create_enrichment(instrumento_id: int, request: EnrichmentRequest):
    """
    Create enriched metadata after analysis.
    Stores additional context inferred by LLM.
    """

@router.get("/enrichment/{instrumento_id}")
async def get_enrichment(instrumento_id: int):
    """Retrieve enriched metadata"""

@router.put("/enrichment/{instrumento_id}")
async def approve_enrichment(instrumento_id: int, request: ApprovalRequest):
    """Approve/reject enriched metadata proposals"""
```

**Schemas:**
- `EnrichmentRequest` — Enriched fields (inferred by analysis-service)
- `ApprovalRequest` — Accept/reject decisions
- `EnrichmentResponse` — Complete enrichment data

**When to modify:** When adding more enrichment dimensions

---

### **8. `services/__init__.py` — Service Module Exports**

**Purpose:** Make all business logic accessible  
**Content:**
```python
from .dc_manager import DCManager
from .enrichment_engine import EnrichmentEngine

__all__ = ["DCManager", "EnrichmentEngine"]
```

**When to modify:** When adding new service classes

---

### **9. `services/dc_manager.py` — Dublin Core Business Logic**

**Purpose:** Core metadata CRUD operations and validation  
**Content:**

**Class: `DCManager`**

```python
class DCManager:
    """Manages all Dublin Core metadata operations"""
    
    @staticmethod
    def register_dc(db, instrumento_id, request):
        """
        Register 13 Dublin Core fields.
        
        Auto-filled (6):
        - dc_creator (from user)
        - dc_publisher (from config)
        - dc_type (from instrumento.tipo_instrumento)
        - dc_format (from file extension)
        - dc_date (from now)
        - dc_language ("es")
        
        User input (7):
        - dc_title
        - dc_subject
        - dc_description
        - dc_coverage
        - dc_rights
        - dc_source
        - dc_relation
        """
        # 1. Validate immutability
        # 2. Get user/instrumento info
        # 3. Create MetadatosDC record
        # 4. Update instrument state to "metadata_registrado"
        # 5. Return success response
    
    @staticmethod
    def get_dc(db, instrumento_id):
        """Retrieve DC metadata"""
        
    @staticmethod
    def get_initial_data(db, instrumento_id):
        """Get pre-populated fields for frontend form"""
        # Return auto-filled values (read-only)
        # Allow title to be editable
```

**Responsibilities:**
- Validate all 13 fields match DC standard
- Auto-populate 6 fields
- Enforce immutability (1x registration per instrument)
- Update instrument state
- Return properly formatted responses

**When to modify:** When DC schema or validation rules change

---

### **10. `services/enrichment_engine.py` — Enrichment Processing**

**Purpose:** Handle enriched metadata proposals and approvals  
**Content:**

**Class: `EnrichmentEngine`**

```python
class EnrichmentEngine:
    """Manages enriched metadata proposals and approvals"""
    
    @staticmethod
    def create_enrichment_proposals(db, instrumento_id, sis_result):
        """
        Called by analysis-service after LLM processing.
        Stores enriched metadata proposals in DB.
        
        Enriched fields might include:
        - domain_inferred (detected subject area)
        - quality_score (data quality assessment)
        - coverage_notes (additional coverage info)
        - recommendations (improvement suggestions)
        """
        # 1. Parse SIS enrichment output
        # 2. Create MetadatosEnriquecidos records
        # 3. Store with estado_decision = "pendiente"
    
    @staticmethod
    def get_enrichment_proposals(db, instrumento_id):
        """Retrieve all enrichment proposals"""
        
    @staticmethod
    def approve_enrichment(db, instrumento_id, decisions):
        """
        Apply user decisions to enrichment proposals.
        Accept/reject each proposed enrichment.
        
        decisions: {
            "proposal_id": "aceptada",
            "proposal_id": "rechazada",
            ...
        }
        """
        # 1. Validate all proposals have decisions
        # 2. Update estado_decision for each
        # 3. Materialize accepted proposals
        # 4. Update instrument state
```

**Responsibilities:**
- Store LLM-generated enrichment proposals
- Track approval status
- Persist accepted enrichments
- Update instrument workflow state

**When to modify:** When enrichment dimensions change

---

## 🔄 Data Flow Through Metadata Service

### **Step 1: Register Metadata (POST /metadata)**
```
User Input (7 fields)
        ↓
    API Endpoint (routers/metadata.py)
        ↓
    DCManager.register_dc() (services/dc_manager.py)
        ↓
    Validate + Auto-fill 6 fields
        ↓
    Create MetadatosDC record in DB
        ↓
    Update InstrumentoProcesado.estado → "metadata_registrado"
        ↓
    Return response with all 13 fields
```

### **Step 2: Analyze (called by analysis-service)**
```
Analysis Service completes
        ↓
    Call POST /enrichment/{instrumento_id}
        ↓
    EnrichmentEngine.create_enrichment_proposals()
        ↓
    Store proposals with estado_decision = "pendiente"
        ↓
    Return proposal summary
```

### **Step 3: Approve Enrichment (POST /enrichment/{id})**
```
User decisions on enriched fields
        ↓
    API Endpoint (routers/enrichment.py)
        ↓
    EnrichmentEngine.approve_enrichment()
        ↓
    Update proposal states (aceptada/rechazada)
        ↓
    Materialize accepted enrichments
        ↓
    Update InstrumentoProcesado.estado → "etl_pendiente_enriquecimiento"
        ↓
    Return approval summary
```

---

## 📊 Database Models (from `shared/models/`)

### **MetadatosDC**
```python
{
    id: int (PK)
    instrumento_id: int (FK)
    dc_title: str              # Auto: from request
    dc_creator: str            # Auto: user
    dc_subject: list[str]      # User input
    dc_description: str        # User input
    dc_publisher: str          # Auto: APP_NAME
    dc_date: date              # Auto: today
    dc_type: str               # Auto: instrumento.tipo
    dc_format: str             # Auto: file extension
    dc_language: str           # Auto: "es"
    dc_coverage: str           # User input
    dc_rights: str             # User input
    dc_source: str             # User input (optional)
    dc_relation: str           # User input (optional)
    creado_en: datetime        # Auto: now
    actualizado_en: datetime   # Auto: now
}
```

### **MetadatosEnriquecidos** (if exists)
```python
{
    id: int (PK)
    instrumento_id: int (FK)
    tipo_propuesta: str        # "domain", "quality", "coverage", etc.
    contenido: str             # Enriched value
    estado_decision: str       # "pendiente", "aceptada", "rechazada"
    confianza: float           # LLM confidence (0-1)
    creado_en: datetime
}
```

---

## 🔌 Inter-Service Communication

### **From Instrument Service**
```
→ GET /metadata/{id}/init  [before registering DC]
→ POST /metadata           [register DC fields]
```

### **From Analysis Service**
```
→ POST /enrichment/{id}    [after LLM analysis]
→ GET /enrichment/{id}     [check proposals]
```

### **From Visualization Service**
```
→ GET /metadata/{id}       [fetch for display]
→ GET /enrichment/{id}     [fetch enriched data]
```

---

## ✅ Implementation Checklist

- [ ] Create complete `main.py` with all imports and routers
- [ ] Create `routers/health.py` with health checks
- [ ] Create `routers/metadata.py` with Dublin Core CRUD
- [ ] Create `routers/enrichment.py` with enrichment endpoints
- [ ] Create `services/dc_manager.py` with core logic
- [ ] Create `services/enrichment_engine.py` with proposals
- [ ] Create all `__init__.py` files
- [ ] Create Pydantic schemas in `shared/schemas/` (if needed)
- [ ] Test locally: `docker compose build metadata-service`
- [ ] Test health: `curl http://localhost:8003/health`
- [ ] Test endpoints with Swagger: `http://localhost:8003/docs`

---

## 🚀 Quick Start Template

**Use these as base templates when creating files.**

See detailed implementations below.
