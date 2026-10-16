"""Knowledge Service — punto de entrada FastAPI.

Port: 8009

Construye, a partir del instrumento ya limpio y con metadatos aprobados, los
artefactos de conocimiento que alimentan la asociación de KPIs y el RAG:
  1. Perfil semántico: solo lo que describe el instrumento (título, objetivo,
     temas, población, preguntas por sección). Es lo único que se usa para
     asociar KPIs. Se muestra en «Aprobar metadatos».
  2. Documento final (fases siguientes): respuestas interpretadas por respondente,
     resúmenes precalculados y relación KPI ↔ pregunta. Se muestra en «Guardar».

Todo se versiona en `tt_rag.version_conocimiento` (una fila por versión).
El JSON técnico de metadata-service no se toca: sigue en storage-service.

Arranque:
  - Docker:  cwd=/app, con `shared/` montado en /app/shared.
  - Local:   `uvicorn main:app --port 8009` desde services/knowledge-service.
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

from routers import documento, health, perfil  # noqa: E402
from services import VERSION_SERVICIO  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Indagata — Knowledge Service",
    description=(
        "Perfil semántico, interpretación de respuestas y documento final de los "
        "instrumentos (insumo de la asociación de KPIs y del RAG)."
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
app.include_router(perfil.router)
app.include_router(documento.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
