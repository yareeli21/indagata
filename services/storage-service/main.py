"""Storage Service — punto de entrada FastAPI.

Port: 8004

Autoridad de TODO el almacenamiento de Indagata:
  - Archivos: guarda el instrumento crudo tal cual lo subió el usuario (con su
    SHA-256), el archivo limpio, los JSON estandarizados (metadata / analysis) y
    los .sav; los sirve, los lee (tabla/texto) y los elimina.
  - Base vectorial: es el único escritor de la colección `instrumentos` de
    ChromaDB y de `documento_vectorizado` (ingesta al RAG de los instrumentos con
    metadatos aprobados).

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8004` desde services/storage-service.
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

from routers import files, health, index  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("storage-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara los directorios de almacenamiento al arrancar."""
    from services import file_manager

    file_manager.preparar_directorios()
    logger.info("🚀 storage-service listo. Raíz de storage: %s", file_manager.raiz())
    yield
    logger.info("🛑 storage-service detenido.")


app = FastAPI(
    title="Indagata — Storage Service",
    description=(
        "Autoridad de almacenamiento: archivos crudos/limpios/JSON/.sav y la base "
        "vectorial (colección `instrumentos` de ChromaDB)."
    ),
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
app.include_router(files.router)
app.include_router(index.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
