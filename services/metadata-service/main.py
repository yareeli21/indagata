"""Metadata Service — punto de entrada FastAPI.

Port: 8003

Responsabilidad: que TODO instrumento tenga metadatos completos y aprobados por
su autor antes de entrar al RAG.
  1. Dublin Core obligatorio (tabla metadatos_dc, 13 campos).
  2. Metadatos específicos del tipo (metadatos_enriquecidos_encuestas /
     _entrevistas / _pruebas), completando los faltantes a partir del contenido.
  3. Aprobación del autor → JSON estandarizado (guardado en storage-service) e
     ingesta al índice vectorial.

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8003` desde services/metadata-service.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Resolver `import shared` también en ejecución local (en Docker vive en /app/shared).
if not (Path(__file__).resolve().parent / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routers import enrichment, health, metadata  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("metadata-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from shared.db.core.config import settings

    logger.info(
        "🚀 metadata-service listo. storage=%s LLM=%s (%s)",
        settings.STORAGE_SERVICE_URL,
        settings.OLLAMA_MODEL if settings.METADATA_USAR_LLM else "desactivado",
        settings.OLLAMA_HOST,
    )
    yield
    logger.info("🛑 metadata-service detenido.")


app = FastAPI(
    title="Indagata — Metadata Service",
    description="Dublin Core obligatorio, metadatos por tipo de instrumento y aprobación del autor.",
    version="2.0.0",
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
app.include_router(metadata.router)
app.include_router(enrichment.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
