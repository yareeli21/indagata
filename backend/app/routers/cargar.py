# app/routers/cargar.py
"""
Router: Cargar instrumento
"""
from fastapi import APIRouter, Request, Form, Query, UploadFile, File, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.services import cargar_service, metadatos_service, limpieza_service, metadatos_enriquecidos_service
from app.core.ollama_client import enviar_mensaje_chat




router = APIRouter(tags=["cargar"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/cargar", response_class=HTMLResponse)
async def ver_formulario_carga(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/cargar_instrumento/cargar_instrumento.html",
        {
            "titulo": "Cargar instrumento",
            "instrumentos_cargados": cargar_service.obtener_instrumentos_cargados(db),
        },
    )


@router.get("/cargar/datasets", response_class=HTMLResponse)
async def filtrar_datasets(
    request: Request,
    tipo: str = Query("todos"),
    fecha: str = Query(""),
    db: Session = Depends(get_db),
):
    """Devuelve solo el fragmento de datasets filtrados, para fetch."""
    return templates.TemplateResponse(
        request,
        "pages/cargar_instrumento/_datasets_originales.html",
        {"instrumentos_cargados": cargar_service.obtener_instrumentos_cargados(db, tipo, fecha)},
    )


@router.post("/cargar")
async def procesar_carga(
    nombre: str = Form(...),
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contenido = await archivo.read()
    resultado = cargar_service.procesar_carga(db, nombre, tipo, contenido, archivo.filename)
    return JSONResponse(resultado)


@router.delete("/cargar/{instrumento_id}")
async def eliminar_instrumento_endpoint(instrumento_id: int, db: Session = Depends(get_db)):
    eliminado = cargar_service.eliminar_instrumento(db, instrumento_id)
    if not eliminado:
        return JSONResponse({"ok": False, "error": "No encontrado."}, status_code=404)
    return JSONResponse({"ok": True})

@router.get("/cargar/{instrumento_id}/metadatos", response_class=HTMLResponse)
async def ver_formulario_metadatos(
    request: Request, instrumento_id: int, db: Session = Depends(get_db)
):
    """Muestra el formulario de metadatos base (Nivel 1) recién subido el instrumento."""
    valores_iniciales = metadatos_service.obtener_valores_iniciales(db, instrumento_id)
    return templates.TemplateResponse(
        request,
        "pages/cargar_instrumento/_metadatos_base.html",
        {
            "titulo": "Metadatos del instrumento",
            "instrumento_id": instrumento_id,
            "valores_iniciales": valores_iniciales,
        },
    )


@router.post("/cargar/{instrumento_id}/metadatos")
async def guardar_metadatos(
    instrumento_id: int,
    titulo: str = Form(...),
    institucion_responsable: str = Form(...),
    objetivo: str = Form(...),
    tipo_instrumento: str = Form(...),
    periodo_inicio: str = Form(...),
    periodo_fin: str = Form(...),
    idioma: str = Form("es"),
    poblacion_alcance: str = Form(...),
    palabras_clave: str = Form(""),  # texto separado por comas, se convierte a lista
    institucion_publica: str = Form(""),
    condiciones_uso: str = Form(""),
    formato_archivo: str = Form(""),
    plataforma_origen: str = Form(""),
    instrumentos_relacionados: str = Form(""),
    db: Session = Depends(get_db),
):
    datos_formulario = {
        "titulo": titulo,
        "institucion_responsable": institucion_responsable,
        "objetivo": objetivo,
        "tipo_instrumento": tipo_instrumento,
        "periodo_inicio": periodo_inicio,
        "periodo_fin": periodo_fin,
        "idioma": idioma,
        "poblacion_alcance": poblacion_alcance,
        "palabras_clave": [p.strip() for p in palabras_clave.split(",") if p.strip()],
        "institucion_publica": institucion_publica or None,
        "condiciones_uso": condiciones_uso or None,
        "formato_archivo": formato_archivo or None,
        "plataforma_origen": plataforma_origen or None,
        "instrumentos_relacionados": [
            i.strip() for i in instrumentos_relacionados.split(",") if i.strip()
        ],
    }

    resultado = metadatos_service.guardar_metadatos_base(db, instrumento_id, datos_formulario)

    if not resultado["ok"]:
        return JSONResponse(resultado, status_code=422)
    return JSONResponse(resultado)

@router.get("/cargar/{instrumento_id}/metadatos/valores-iniciales")
async def valores_iniciales_metadatos(instrumento_id: int, db: Session = Depends(get_db)):
    return JSONResponse(metadatos_service.obtener_valores_iniciales(db, instrumento_id))


# --- Limpieza automática (stub) ---
@router.post("/cargar/{instrumento_id}/limpieza-automatica")
async def limpieza_automatica_endpoint(instrumento_id: int, db: Session = Depends(get_db)):
    resultado = limpieza_service.aplicar_limpieza_automatica(db, instrumento_id)
    if not resultado["ok"]:
        return JSONResponse(resultado, status_code=404)
    return JSONResponse(resultado)


# --- Limpieza asistida (chat real con Ollama) ---
@router.post("/cargar/{instrumento_id}/limpieza-asistida/chat")
async def limpieza_asistida_chat(instrumento_id: int, historial: list[dict] = Body(...), db: Session = Depends(get_db)):
    try:
        system_prompt = limpieza_service.construir_prompt_sistema_limpieza(db, instrumento_id)
        respuesta = enviar_mensaje_chat(system_prompt, historial)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
    return JSONResponse({"ok": True, "respuesta": respuesta})


@router.post("/cargar/{instrumento_id}/limpieza-asistida")
async def limpieza_asistida_guardar(instrumento_id: int, cuerpo: dict = Body(...), db: Session = Depends(get_db)):
    resultado = limpieza_service.guardar_limpieza_asistida(db, instrumento_id, cuerpo.get("historial"))
    return JSONResponse(resultado)


# --- Metadatos enriquecidos (chat real con Ollama) ---
@router.post("/cargar/{instrumento_id}/metadatos/chat")
async def metadatos_chat(instrumento_id: int, historial: list[dict] = Body(...), db: Session = Depends(get_db)):
    try:
        system_prompt = metadatos_enriquecidos_service.construir_prompt_sistema(db, instrumento_id)
        respuesta = enviar_mensaje_chat(system_prompt, historial)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
    return JSONResponse({"ok": True, "respuesta": respuesta})


@router.post("/cargar/{instrumento_id}/metadatos-enriquecidos")
async def metadatos_enriquecidos_guardar(instrumento_id: int, cuerpo: dict = Body(...), db: Session = Depends(get_db)):
    resultado = metadatos_enriquecidos_service.guardar_metadatos_enriquecidos(db, instrumento_id, cuerpo.get("historial"))
    return JSONResponse(resultado)