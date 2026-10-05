"""API Gateway — punto de entrada FastAPI.

Expone, en esta tanda, el módulo de AUTENTICACIÓN:
  GET  /health            → estado del servicio
  POST /auth/login        → email + password → JWT
  GET  /auth/me           → usuario del token
  POST /auth/register     → alta de usuario (solo administrador)

Arranque:
  - Docker:  cwd=/app, con `shared/` copiado en /app/shared (ver Dockerfile).
  - Local:   `uvicorn main:app --port 8000` desde services/api-gateway.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Resolver `import shared` también en ejecución local (igual que los servicios).
if not (Path(__file__).resolve().parent / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.auth.routers import router as auth_router  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("api-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 API Gateway listo (auth JWT).")
    yield
    logger.info("🛑 API Gateway detenido.")


app = FastAPI(
    title="Indagata — API Gateway",
    description="Puerta de entrada: autenticación (JWT), y enrutamiento a los servicios.",
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
    return {"status": "ok", "service": "api-gateway"}


app.include_router(auth_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
