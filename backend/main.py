from fastapi import Request, FastAPI
#para controlar el envío de datos incorrectos a la API
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles


app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "frontend" / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "frontend" / "landing" / "templates")#osea las carpetas donde van a estar los templates
)

@app.get("/", response_class=HTMLResponse)
def root(request:Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html"
        )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard