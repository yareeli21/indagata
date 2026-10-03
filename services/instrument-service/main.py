"""Instrument Service — punto de entrada FastAPI.

Microservicio de CARGA de instrumentos. Expone:
  GET  /health                     → estado del servicio
  POST /instrumentos/upload        → sube el instrumento + archivo original

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8001` desde services/instrument-service.
             Para que `import shared` resuelva en local, se añade la raíz del
             repo a sys.path si el paquete `shared` no está ya disponible.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ── Resolver import de `shared` también en ejecución local ────────────────────
# En Docker `shared` vive en /app/shared (misma cwd). En local, el paquete está
# en la raíz del repo: services/instrument-service/main.py -> parents[2].
if not (Path(__file__).resolve().parent / "shared").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.routers import health, upload  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("instrument-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara el almacenamiento de archivos crudos al arrancar."""
    from shared.db.core.config import settings

    settings.raw_path_abs.mkdir(parents=True, exist_ok=True)
    logger.info("🚀 instrument-service listo. RAW_PATH=%s", settings.raw_path_abs)
    yield
    logger.info("🛑 instrument-service detenido.")


app = FastAPI(
    title="Indagata — Instrument Service",
    description="Carga de instrumentos: subida, identificación de tipo y registro en RAW DATA.",
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
app.include_router(upload.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
