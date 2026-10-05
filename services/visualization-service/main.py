"""Visualization Service — FastAPI entry point.

Port: 8005

STUB: this is a health-only placeholder so the service builds and starts.
The real visualization logic (charts, aggregations, dashboard data) is
pending implementation. Only GET /health is exposed.

Mirrors the style of services/api-gateway/main.py.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("visualization-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 visualization-service listo (stub health-only).")
    yield
    logger.info("🛑 visualization-service detenido.")


app = FastAPI(
    title="Indagata — Visualization Service",
    description="Visualización de resultados (STUB health-only, pendiente de implementación).",
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


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "visualization-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
