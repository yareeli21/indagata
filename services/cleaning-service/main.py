"""Cleaning Service — punto de entrada FastAPI.

Port: 8007

Limpia los instrumentos recién subidos antes de pasar a metadatos:
  1. Fase automática (según el tipo: encuesta, entrevista o prueba estandarizada).
  2. Fase asistida: presenta hallazgos con una opción sugerida; decide el investigador.
  3. Genera el CSV limpio (vía storage-service) y el reporte_limpieza (JSONB en
     `tt_rag.limpieza_ejecucion`).

El archivo crudo nunca se modifica: cada ejecución lo vuelve a leer y cada
repetición de la limpieza crea una versión nueva.

Arranque:
  - Docker:  cwd=/app, con `shared/` montado en /app/shared.
  - Local:   `uvicorn main:app --port 8007` desde services/cleaning-service.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Resolver `import shared` también en ejecución local (en Docker vive en /app/shared).
if not (Path(__file__).resolve().parent / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routers import health, limpieza  # noqa: E402
from services import VERSION_SERVICIO  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Indagata — Cleaning Service",
    description=(
        "Limpieza de instrumentos (encuestas, entrevistas y pruebas estandarizadas): "
        "fase automática, fase asistida por el investigador, CSV limpio versionado y "
        "reporte_limpieza."
    ),
    version=VERSION_SERVICIO,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(limpieza.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
