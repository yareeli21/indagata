# main.py
"""
Punto de entrada de la aplicación FastAPI — Indagata.

Registra dos routers sin prefijo; cada endpoint declara su ruta completa:
  routers_carga.py          → wizard de carga (upload, metadata, etl, ingesta)
  routers_visualizacion.py  → consulta (kpis, instrumentos, detalle, download, delete)

Detalle de endpoints: api/routers/README.md. Visión general: backend/README.md.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.routers_carga import router as router_carga
from api.routers.routers_visualizacion import router as router_visualizacion

app = FastAPI(
    title="Indagata API",
    version="1.0.0",
    description="Sistema de gestión y consulta de instrumentos de investigación educativa.",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En producción: reemplazar con el origen del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(router_carga,         tags=["carga-instrumentos"])
app.include_router(router_visualizacion, tags=["visualizacion-instrumentos"])


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event() -> None:
    print("Indagata API iniciada.")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    print("Indagata API detenida.")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "ok", "service": "Indagata API"}

if __name__ == "__main__":
    # Arranque directo por consola (equivalente a: uvicorn main:app --reload).
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
