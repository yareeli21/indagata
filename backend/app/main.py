"""
Entrypoint de la interfaz web (FastAPI + Jinja2).

Para correr en desarrollo, desde interfaz/:
    uvicorn backend.main:app --reload

Luego abre: http://127.0.0.1:8000
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings

from app.routers import (
    login, 
    kpis,
    instrumentos,
    chat, 
    cargar
)

#aplicación fastAPI

app= FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

#ARCHIVOS ESTÁTICOS
print("STATIC_DIR:", settings.STATIC_DIR)

app.mount(
    "/static",
    StaticFiles(directory=settings.STATIC_DIR),
    name="static"
)

#TEMPLATES HTML

templates=Jinja2Templates(
    directory=settings.TEMPLATES_DIR
)

app.state.templates=templates
app.state.nombre_proyecto = settings.APP_NAME

#ROUTERS

app.include_router(login.router)
app.include_router(kpis.router)
app.include_router(instrumentos.router)
app.include_router(chat.router)
app.include_router(cargar.router)

#ruta de pruebaa

@app.get("/")
async def root(request: Request):
    return {
        "mensaje": f"{settings.APP_NAME} funcionando",
        "entorno": settings.APP_ENV
    }