"""Analysis Service — punto de entrada FastAPI.

Expone el módulo de VECTORIZACIÓN e inferencia de KPIs:
  GET  /health                       → estado del servicio
  POST /vectorizacion/propuestas     → proponer KPIs por similitud
  POST /vectorizacion/confirmar      → enriquecer el JSON con los KPIs aceptados
  POST /vectorizacion/kpis/reindex   → reindexar la colección de KPIs

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8002` desde services/analysis-service.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Resolver `import shared` también en ejecución local (ver instrument-service).
if not (Path(__file__).resolve().parent / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.vectorization.routers import espacio, health, kpis, vectorizacion  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("analysis-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from shared.db.core.config import settings

    logger.info(
        "🚀 analysis-service listo. Chroma=%s:%s modelo=%s",
        settings.CHROMA_HOST,
        settings.CHROMA_PORT,
        settings.EMBEDDING_MODEL,
    )
    yield
    logger.info("🛑 analysis-service detenido.")


app = FastAPI(
    title="Indagata — Analysis Service",
    description="Vectorización e inferencia de KPIs por similitud semántica (Chroma).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(vectorizacion.router)
app.include_router(espacio.router)
app.include_router(kpis.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
