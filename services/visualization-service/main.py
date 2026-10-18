"""Visualization Service — punto de entrada FastAPI.

Port: 8005

Muestra la información de forma amigable para el investigador:
  - Catálogo del acervo con filtros y facetas, fichas e investigadores.
  - KPIs: catálogo, resumen del acervo, dashboards y QUÉ PREGUNTAS de cada
    instrumento miden cada KPI.
  - Instrumentos relacionados de otros autores.
  - Descargas (crudo / JSON / .sav) con la regla de propiedad.
  - Chat RAG sobre los instrumentos de la investigación o de todo el sistema.
  - Espacio vectorial explicable: KPIs, instrumentos y chunks en 2D (PCA).

Es de solo lectura sobre la BD y ChromaDB (salvo `rag_log`); la ingesta la hace
el storage-service.

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8005` desde services/visualization-service.
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

from routers import catalog, download, espacio, health, kpis, noticias, rag  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("visualization-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from shared.db.core.config import settings

    logger.info(
        "🚀 visualization-service listo. OLLAMA=%s CHROMA=%s:%s storage=%s",
        settings.OLLAMA_HOST,
        settings.CHROMA_HOST,
        settings.CHROMA_PORT,
        settings.STORAGE_SERVICE_URL,
    )
    if os.getenv("ESPACIO_PRECALENTAR", "true").lower() == "true":
        # Carga el modelo de embeddings y precalcula el espacio vectorial en segundo
        # plano, para que la primera visita al mapa no espere esa carga (~40 s en CPU).
        import threading

        from services.espacio import mapa

        threading.Thread(target=mapa.precalentar, name="precalentar-espacio", daemon=True).start()
    yield
    logger.info("🛑 visualization-service detenido.")


app = FastAPI(
    title="Indagata — Visualization Service",
    description="Catálogo, KPIs, relaciones, descargas y chat RAG sobre los instrumentos.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(health.router)
app.include_router(catalog.router)
app.include_router(kpis.router)
app.include_router(download.router)
app.include_router(rag.router)
app.include_router(espacio.router)
app.include_router(noticias.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
