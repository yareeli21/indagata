from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
import requests
import json
import io
from datetime import datetime
import uuid

app = FastAPI(
    title="Servicio de Procesamiento de Pruebas Estandarizadas",
    description="API para extraer metadatos enriquecidos y limpiar datasets para RAG usando Ollama."
)

OLLAMA_URL = "http://localhost:11434/api/generate"
# Puedes cambiar a "mistral" según el modelo que tengas corriendo en Ollama
OLLAMA_MODEL = "llama3.2:3b" 

def limpiar_y_estandarizar(df: pd.DataFrame) -> pd.DataFrame:
    """Proceso de limpieza previo a la ingesta en RAG."""
    # Estandarizar nombres de columnas (minúsculas, sin espacios extra)
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
    # Eliminar filas y columnas completamente vacías
    df = df.dropna(how='all').dropna(axis=1, how='all')
    # Limpiar espacios en blanco en celdas de texto
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
    # Rellenar valores nulos de texto con una cadena vacía para evitar errores en el RAG
    df = df.fillna("")
    return df

@app.post("/procesar-prueba")
async def procesar_prueba(file: UploadFile = File(...)):
    # 1. Leer el archivo
    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Usa .csv o .xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo el archivo: {str(e)}")

    # 2. Limpieza y estandarización del dataset
    df_cleaned = limpiar_y_estandarizar(df)

    # 3. Extraer una muestra representativa para el LLM (primeras 10 filas para no saturar el contexto)
    muestra_datos = df_cleaned.head(10).to_dict(orient="records")
    nombres_columnas = list(df_cleaned.columns)

    # 4. Prompt para Ollama forzando la extracción de los metadatos requeridos
    prompt = f"""
    Eres un analista de datos experto en educación. Analiza el siguiente esquema de columnas y la muestra de datos de una prueba estandarizada.
    Extrae, infiere o genera los metadatos solicitados. 
    
    Columnas del dataset: {nombres_columnas}
    Muestra de datos: {json.dumps(muestra_datos, ensure_ascii=False)}

    Responde ÚNICAMENTE con un objeto JSON válido con la siguiente estructura y claves exactas. Si no puedes inferir un dato, usa "No especificado".
    {{
        "Fecha_de_aplicacion": "",
        "Institucion": "",
        "Nombre_de_prueba": "",
        "Area_general": "",
        "Idioma": "Español",
        "Campus": "",
        "Grado": "",
        "Grupo": "",
        "Ciclo_escolar": "",
        "Tipo_de_prueba": "",
        "Modalidad": "",
        "Version": "",
        "Subareas": [],
        "Competencias": [],
        "Unidad_de_aprendizaje": "",
        "Mapeo_de_reactivos_por_seccion": "",
        "Taxonomia_Bloom": "",
        "Nivel_educativo": "",
        "Objetivo_de_evaluacion": "",
        "Id_prueba": "",
        "Range_Prueba_estandarizada": "",
        "Creador": "",
        "Descripcion": ""
    }}
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1 # Temperatura baja para mayor consistencia estructural
        }
    }

    # 5. Llamada al LLM
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        llm_result = response.json()
        metadatos = json.loads(llm_result["response"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar con Ollama: {str(e)}")

    # 6. Enriquecer campos obligatorios que el LLM pudo omitir
    metadatos["Id_prueba"] = metadatos.get("Id_prueba") or str(uuid.uuid4())
    if not metadatos.get("Fecha_de_aplicacion") or metadatos.get("Fecha_de_aplicacion") == "No especificado":
        metadatos["Fecha_de_aplicacion"] = datetime.now().isoformat()

    # Guardar temporalmente el dataset limpio listo para el RAG
    # df_cleaned.to_csv("datos_limpios_rag.csv", index=False)

    return {
        "status": "success",
        "message": "Archivo procesado, limpiado y metadatos generados.",
        "file_shape": df_cleaned.shape,
        "metadatos_enriquecidos": metadatos
    }