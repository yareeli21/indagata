# app/routers/__init__.py
from api.routers.routers_carga import router as router_carga
from api.routers.routers_visualizacion import router as router_visualizacion

__all__ = ["router_carga", "router_visualizacion"]
