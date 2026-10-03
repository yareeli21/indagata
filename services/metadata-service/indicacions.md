### **Priority 6: Testing & Validation (2-3 hours)**

- [ ] Build each service: `docker compose build <service>`
- [ ] Start infrastructure: `docker compose up postgres redis chromadb ollama`
- [ ] Test each service independently: `curl http://localhost:800X/health`
- [ ] Test inter-service communication from api-gateway
- [ ] Run database migrations
- [ ] Test full workflow: upload → analyze → visualize




### Phase A: Setup (1 hour)
- [ ] Create `.env` from `.env.example`
- [ ] Verify all directories exist
- [ ] Check file permissions

### Phase B: Complete Entry Points (3 hours)
- [ ] Create `instrument-service/main.py`
- [ ] Create `analysis-service/main.py`
- [ ] Create `metadata-service/main.py`
- [ ] Create `storage-service/main.py`
- [ ] Create `visualization-service/main.py`

### Phase C: Fix Imports (4 hours)
- [ ] Update imports in `routers_carga.py`
- [ ] Update imports in `routers_visualizacion.py`
- [ ] Update imports in all service files
- [ ] Update imports in shared models/schemas

### Phase D: Organize Code (5 hours)
- [ ] Create `services/*/routers/__init__.py` files
- [ ] Move services to appropriate directories
- [ ] Create `shared/utils/` files
- [ ] Create all missing `__init__.py` files
- [ ] Update all relative imports

### Phase E: Build & Test (3 hours)
- [ ] `docker compose build`
- [ ] `docker compose up -d`
- [ ] Test all `/health` endpoints
- [ ] Test database connectivity
- [ ] Test inter-service communication
- [ ] Run sample requests

---

## 🚀 Quick Start Template for Each Service

Use this as a template for missing `main.py` files:

```python
"""
{Service Name} - FastAPI Entry Point
Port: {PORT}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

# Import routers
from routers import health  # Add more as needed
# from routers import business_logic

logger = logging.getLogger(__name__)

SERVICE_NAME = "{SERVICE_NAME}"
PORT = {PORT}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    logger.info(f"🚀 {SERVICE_NAME} starting...")
    yield
    logger.info(f"🛑 {SERVICE_NAME} shutting down...")

app = FastAPI(
    title=f"Indagata {SERVICE_NAME}",
    description=f"{SERVICE_NAME} microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
# app.include_router(business_logic.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
```

---

1. Use absolute imports in all files (easier to track)
2. Never import from one service to another directly; use HTTP via api-gateway
3. Keep `shared/` lightweight; only truly common code goes there
4. Add `__all__` to each `__init__.py` for clarity
5. Use `pydantic.BaseSettings` (from `pydantic-settings`) in shared config