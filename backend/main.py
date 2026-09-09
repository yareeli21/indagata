from fastapi import FastAPI
#para controlar el envío de datos incorrectos a la API
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from fastapi import FastAPI
from app.routers.routers_cargar_instru import app as router_cargar_instru

app = FastAPI()

app.include_router(router_cargar_instru)