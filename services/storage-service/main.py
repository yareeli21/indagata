"""Storage Service — punto de entrada FastAPI.

Port: 8004

Autoridad de artefactos: recibe los archivos (JSON de metadata/analysis y
binarios raw/sav/temp), decide dónde guardarlos (ruteo por tipo) y devuelve
dónde quedaron guardados, con clave versionada estable.

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8004` desde services/storage-service.
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
# en la raíz del repo: services/storage-service/main.py -> parents[2].
if not (Path(__file__).resolve().parent / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.routers import almacenamiento, health  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("storage-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara los directorios de almacenamiento al arrancar."""
    from shared.db.core.config import settings

    for directorio in (
        settings.raw_path_abs,
        settings.json_path_abs,
        settings.sav_path_abs,
        settings.temp_path_abs,
        settings.json_path_abs / "_index",
    ):
        directorio.mkdir(parents=True, exist_ok=True)
    logger.info("🚀 storage-service listo. JSON_PATH=%s", settings.json_path_abs)
    yield
    logger.info("🛑 storage-service detenido.")


app = FastAPI(
    title="Indagata — Storage Service",
    description="Autoridad de artefactos: persiste JSON (metadata/analysis) y binarios (raw/sav/temp).",
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
app.include_router(almacenamiento.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
