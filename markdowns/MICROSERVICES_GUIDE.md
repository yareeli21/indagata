# Indagata Microservices Restructuring Guide

## Current → Microservices Mapping

### **Current Structure:**
```
backend/
├── api/routers/
├── services/
├── models/
├── schemas/
└── main.py
```

### **New Microservices Structure:**

```
services/
├── api-gateway/
│   ├── main.py                    # FastAPI entry point
│   ├── routers/
│   │   ├── auth.py
│   │   ├── health.py
│   │   └── proxy.py               # Routes to other services
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── cors.py
│   │   └── logging.py
│   ├── dependencies/
│   ├── requirements.txt
│   └── Dockerfile (via docker-compose)
│
├── instrument-service/            # CRUD, upload, file parsing
│   ├── main.py
│   ├── routers/
│   │   ├── upload.py
│   │   ├── crud.py
│   │   └── state.py
│   ├── services/
│   │   ├── file_parser.py         # Parse .xlsx, .pdf, .docx
│   │   └── instrument_manager.py
│   ├── requirements.txt
│   └── models.py                  # From backend/models
│
├── analysis-service/              # LLM integration (Ollama)
│   ├── main.py
│   ├── routers/
│   │   └── analyze.py
│   ├── services/
│   │   ├── ollama_client.py       # LLM calls
│   │   ├── kpi_inferencer.py      # KPI extraction
│   │   └── proposal_generator.py
│   ├── prompts/                   # LLM prompts
│   ├── requirements.txt
│   └── models.py
│
├── metadata-service/              # Dublin Core, enrichment
│   ├── main.py
│   ├── routers/
│   │   ├── metadata.py
│   │   └── enrichment.py
│   ├── services/
│   │   ├── dc_manager.py          # Dublin Core CRUD
│   │   └── enrichment_engine.py
│   ├── requirements.txt
│   └── models.py
│
├── storage-service/               # File I/O, storage ops
│   ├── main.py
│   ├── routers/
│   │   ├── files.py               # Upload/download
│   │   └── index.py               # ChromaDB index
│   ├── services/
│   │   ├── file_manager.py
│   │   ├── chroma_indexer.py
│   │   └── cache_manager.py
│   ├── requirements.txt
│   └── models.py
│
└── visualization-service/         # Public queries, catalog
    ├── main.py
    ├── routers/
    │   ├── catalog.py
    │   ├── download.py
    │   └── kpis.py
    ├── services/
    │   ├── query_engine.py
    │   └── rag_service.py
    ├── requirements.txt
    └── models.py

shared/
├── models/
│   ├── __init__.py
│   ├── instrument.py              # SQLAlchemy ORM
│   ├── metadata.py
│   ├── kpi.py
│   ├── variable.py
│   └── permission.py
├── schemas/
│   ├── __init__.py
│   ├── instrument.py              # Pydantic DTOs
│   ├── metadata.py
│   ├── kpi.py
│   └── responses.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── validators.py
│   ├── constants.py
│   └── exceptions.py
├── db/
│   ├── __init__.py
│   ├── database.py                # SQLAlchemy setup
│   └── session.py
└── requirements.txt               # Shared dependencies

infrastructure/
├── postgres/
│   ├── init/
│   │   └── 00-init.sql            # Schema setup
│   └── migrations/
│       ├── 01-create-tables.sql
│       ├── 02-seed-kpis.sql
│       └── 03-seed-variables.sql
├── docker/
│   ├── Dockerfile.api-gateway
│   ├── Dockerfile.instrument-service
│   ├── Dockerfile.analysis-service
│   ├── Dockerfile.metadata-service
│   ├── Dockerfile.storage-service
│   ├── Dockerfile.visualization-service
│   └── Dockerfile.frontend
└── nginx/                         # Optional reverse proxy
    ├── nginx.conf
    └── Dockerfile

frontend/                          # React/Vite frontend
├── src/
├── public/
├── package.json
├── vite.config.js
└── index.html

storage/                           # Persistent volumes
├── raw/
├── json/
├── sav/
├── clean/
├── temp/
└── .gitkeep

chromadb/                          # Vector DB data
└── data/

postgres/                          # (Legacy - move to infrastructure/)
├── init/
└── migrations/
```

---

## **Migration Steps**

### **1. Prepare Directory Structure**

```bash
mkdir -p services/{api-gateway,instrument-service,analysis-service,metadata-service,storage-service,visualization-service}
mkdir -p shared/{models,schemas,utils,db}
mkdir -p infrastructure/{docker,postgres/{init,migrations}}
```

### **2. Split Backend Code**

From your current `backend/`:

- **api-gateway/** ← `api/routers/` (auth, health, proxy routes)
- **instrument-service/** ← `api/routers/routers_carga.py` + file handling
- **analysis-service/** ← `services/` + LLM client
- **metadata-service/** ← Dublin Core logic
- **storage-service/** ← File ops + ChromaDB
- **visualization-service/** ← `api/routers/routers_visualizacion.py`
- **shared/** ← `models/`, `schemas/`, `dependencies/`

### **3. Create Requirements Files**

Each service gets its own `requirements.txt` with ONLY needed deps:

**api-gateway/requirements.txt:**
```
fastapi==0.115.6
uvicorn[standard]==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
```

**analysis-service/requirements.txt:**
```
fastapi==0.115.6
uvicorn[standard]==0.30.0
langchain==0.3.0
langchain-ollama==0.1.0
sqlalchemy==2.0.25
psycopg[binary]==3.2.0
```

**storage-service/requirements.txt:**
```
fastapi==0.115.6
uvicorn[standard]==0.30.0
chromadb==0.5.0
langchain-chroma==0.1.0
sentence-transformers==3.0.0
```

(See docker-compose for each service's full list)

### **4. Inter-Service Communication**

Use HTTP via service names (Docker DNS):

```python
# In api-gateway/routers/proxy.py
async def proxy_to_service(service_name: str, endpoint: str):
    url = f"http://{service_name}:PORT/api{endpoint}"
    response = httpx.get(url)
    return response.json()
```

### **5. Health Checks**

Each service exposes `/health`:

```python
# In services/{service}/routers/health.py
@router.get("/health")
async def health():
    return {"status": "ok", "service": "analysis-service"}
```

### **6. Database Migrations**

Run migrations automatically on startup:

```python
# In shared/db/database.py
def init_db():
    """Run migrations and create tables"""
    Base.metadata.create_all(bind=engine)
    # Or use Alembic for advanced migrations
```

---

## **Docker Build & Run**

### **Build All Services:**
```bash
docker compose build
```

### **Start All Services:**
```bash
docker compose up -d
```

### **View Logs:**
```bash
docker compose logs -f api-gateway
docker compose logs -f analysis-service
```

### **Stop All:**
```bash
docker compose down
```

### **Cleanup (including volumes):**
```bash
docker compose down -v
```

---

## **Inter-Service Dependency Graph**

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (Port 8000)                      │
│            (Auth, CORS, Rate Limiting, Routing)                │
└─────────────────────────────────────────────────────────────────┘
    │              │              │              │
    ↓              ↓              ↓              ↓
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Instrument│  │ Analysis │  │Metadata  │  │ Storage  │
│Service   │  │ Service  │  │Service   │  │Service   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
    │              │              │              │
    └──────────────┴──────────────┴──────────────┘
                        │
                        ↓
            ┌─────────────────────────┐
            │   PostgreSQL (Shared)   │
            │   Redis (Cache)         │
            │   Ollama (LLM)          │
            │   ChromaDB (Vector DB)  │
            └─────────────────────────┘
```

---

## **Benefits of This Microservices Architecture**

✅ **Scalability:** Scale analysis-service independently if LLM processing is bottleneck
✅ **Resilience:** If storage-service down, other services keep running
✅ **Dev Velocity:** Teams can work on services in parallel
✅ **Tech Agility:** Replace analysis-service with Ollama API without touching other services
✅ **Testability:** Test each service in isolation
✅ **Observability:** Monitor each service's health independently
✅ **Cost Optimization:** Scale high-resource services (analysis) only when needed

---

## **Advanced: Kubernetes Ready**

After microservices are running locally, export to Kubernetes:

```bash
# Generate K8s manifests from docker-compose
docker compose convert > kubernetes/docker-stack.yml

# Or manually create Deployments + Services for each microservice
```

Each service becomes a Deployment + Service, sharing PostgreSQL, Redis, Ollama as StatefulSets.
