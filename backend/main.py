from fastapi import FastAPI
#para controlar el envío de datos incorrectos a la API
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from cargar_instru.routers_cargar_instru import app as routers_cargar_instru


class Item(BaseModel): #se crea una clase item que se hereda de basemodel
    name: str
    age: int

app = FastAPI()

app.add_middleware( 
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers_cargar_instru, prefix="/route_instru", tags=["route"])

#todo se va a abrir en el puerto 
#8000

#cada vez que llegue un método de HTTP pasará primero por un middleware para validar ciertas cosas
@app.middleware("http")
async def add_custom_header(request, call_next):
    response = await call_next(request)
    response.headers['X-Custom-Header'] = 'CustomeValue'
    return response
#los métodos para iniciar y terminar la aplicación

@app.on_event("startup")
async def startup_event():
    print("inicianding app")

@app.on_event("shutdown")
async def shutdown_event():
    print("terminanding app")

@app.get('/')
async def read_root():
    return {"message": "holisss, probanding FastAPI"}

#método para usar la clase item, validar
@app.post('/items')
async def create_item(item: Item): #el parámetro quiere decir que se crea un ítem
    return {'item':item, 'name':item.name, 'age':item.age} #es como validar que los valores que ingresa el usuario efectivamente son válidos

connected_clients=[]
@app.websocket("/ws/data")
async def websocket_data(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)
