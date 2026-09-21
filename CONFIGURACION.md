# 🔧 Configuración y Conexiones - Indagata

Guía completa de todas las configuraciones, conexiones y servicios externos del sistema.

---

## 📋 Índice

1. [Variables de entorno (.env)](#-variables-de-entorno-env)
2. [PostgreSQL](#-postgresql)
3. [Ollama (LLM)](#-ollama-llm)
4. [FastAPI](#-fastapi)
5. [Archivos de configuración](#-archivos-de-configuración)
6. [Troubleshooting](#-troubleshooting)

---

## 🌍 Variables de entorno (.env)

### **Ubicación:** `backend/.env`

```ini
# ══════════════════════════════════════════════════════════════
# BASE DE DATOS - PostgreSQL
# ══════════════════════════════════════════════════════════════
POSTGRES_DB=aprende_rag          # Nombre de la base de datos
POSTGRES_USER=postgres            # Usuario de PostgreSQL
POSTGRES_PASSWORD=ttaprobado      # Contraseña
POSTGRES_HOST=localhost           # Host (local sin Docker)
POSTGRES_PORT=5432                # Puerto estándar PostgreSQL

# ══════════════════════════════════════════════════════════════
# APLICACIÓN - FastAPI
# ══════════════════════════════════════════════════════════════
APP_NAME=Indagata                 # Nombre de la aplicación
APP_ENV=development               # Ambiente: development | production
DEBUG=True                        # Modo debug (True en desarrollo)

# ══════════════════════════════════════════════════════════════
# LLM - Ollama (Para análisis de los instrumentos y generación de respuestas)
# ══════════════════════════════════════════════════════════════
OLLAMA_HOST=http://localhost:11434   # URL del servidor Ollama
OLLAMA_MODEL=llama3.2:3b o Mistral7B           # Modelos a utilizar

# ══════════════════════════════════════════════════════════════
# ALMACENAMIENTO - Rutas de archivos
# ══════════════════════════════════════════════════════════════
RAW_PATH=storage/raw              # Archivos originales subidos
JSON_PATH=storage/json            # JSON consolidados generados
SAV_PATH=storage/sav              # Archivos SPSS (solo para encuestas, se van a construir durante el proceso del análisis del instrumento)
TEMP_PATH=storage/temp            # Archivos temporales
DATA_PATH=storage/data            # Texto limpio extraído

# ══════════════════════════════════════════════════════════════
# VECTOR DB - ChromaDB (futuro)
# ══════════════════════════════════════════════════════════════
CHROMA_PATH=storage/chromadb      # Base de datos vectorial

# ══════════════════════════════════════════════════════════════
# SEGURIDAD
# ══════════════════════════════════════════════════════════════
SECRET_KEY=vamos_a_poner_una_llavesota   # Clave secreta para JWT (cambiar en producción)

# ══════════════════════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════════════════════
LOG_LEVEL=INFO                    # Nivel de logging: DEBUG | INFO | WARNING | ERROR
```

### **🔒 Seguridad:**

⚠️ **NUNCA subir `.env` a Git** - Ya está en `.gitignore`

✅ **En producción:**
- Cambiar `SECRET_KEY` por una clave segura: `openssl rand -hex 32`
- Cambiar `DEBUG=False`
- Usar contraseñas fuertes para `POSTGRES_PASSWORD`
- Restringir `allow_origins` en CORS

---

## 🐘 PostgreSQL

### **1. Archivo de configuración**

**Ubicación:** `backend/api/core/config.py`

```python
class AppSettings(BaseSettings):
    # Campos de .env
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    
    @property
    def DATABASE_URL(self) -> str:
        """Genera la URL de conexión PostgreSQL"""
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

settings = AppSettings()  # Singleton
```

### **2. Conexión con SQLAlchemy**

**Ubicación:** `backend/api/database/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.core.config import settings

# Motor de conexión
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,           # True para ver SQL en logs
    future=True
)

# Factory de sesiones
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### **3. Uso en endpoints**

```python
from api.dependencies.dependencies_instrumentos import DBSession

@router.get("/instrumentos")
def listar(db: DBSession):
    # db es una sesión de SQLAlchemy
    instrumentos = db.query(InstrumentoProcesado).all()
    return instrumentos
```

### **4. Verificar conexión**

```powershell
# Conectar manualmente
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag

# Desde Python (en ambiente activado)
python -c "from backend.api.database.database import engine; print(engine.url)"
```

### **5. Configuración PostgreSQL**

```sql
-- Ver conexiones activas
SELECT * FROM pg_stat_activity WHERE datname = 'aprende_rag';

-- Ver configuración
SHOW max_connections;
SHOW shared_buffers;
```

---

## 🤖 Ollama (LLM)

### **1. Instalación**

```bash
# Windows (PowerShell como admin)
winget install Ollama.Ollama

# O descargar desde: https://ollama.com/download
```

### **2. Descargar modelo**

```bash
# Modelo actual: llama3.2:3b (2.0GB)
ollama pull llama3.2:3b

# Verificar modelos instalados
ollama list
```

### **3. Iniciar servidor Ollama**

```bash
# Opción 1: Iniciar manualmente
ollama serve

# Opción 2: Se inicia automáticamente después de instalación
# Verificar que está corriendo:
curl http://localhost:11434/api/tags
```

### **4. Cliente HTTP en el proyecto**

**Ubicación:** `backend/services/ollama_client.py`

```python
import httpx
from api.core.config import settings

def enviar_mensaje_chat(
    system_prompt: str,
    historial: list[dict],
    timeout: float = 300.0
) -> str:
    """
    Envía mensajes a Ollama y retorna respuesta.
    
    Args:
        system_prompt: Instrucciones del sistema
        historial: [{"role": "user", "content": "..."}]
        timeout: Timeout en segundos (default: 5min)
    
    Returns:
        Respuesta del LLM como string
    """
    mensajes = [
        {"role": "system", "content": system_prompt}
    ] + historial
    
    respuesta = httpx.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": settings.OLLAMA_MODEL,
            "messages": mensajes,
            "stream": False,
        },
        timeout=timeout,
    )
    respuesta.raise_for_status()
    return respuesta.json()["message"]["content"]
```

### **5. Servicio LLM (lógica de negocio)**

**Ubicación:** `backend/services/llm_service.py`

```python
from services.ollama_client import enviar_mensaje_chat

def generar_propuestas_etl(
    instrumento_id: int,
    texto_extraido: str,
    metadatos_dc: MetadatosDC
) -> list[dict]:
    """
    Genera propuestas de mejora para un instrumento.
    
    Returns:
        Lista de propuestas en formato:
        [
          {
            "tipo": "transformacion",
            "descripcion": "...",
            "accion_sugerida": "...",
            "justificacion": "...",
            "impacto_esperado": "...",
            "valor_original": null,
            "valor_propuesto": "..."
          }
        ]
    """
    system_prompt = _SYSTEM_PROMPT_ETL
    historial = [
        {"role": "user", "content": f"Texto: {texto_extraido[:3000]}"}
    ]
    
    respuesta = enviar_mensaje_chat(system_prompt, historial, timeout=300.0)
    return _parsear_propuestas_json(respuesta)
```

### **6. Configuración del modelo**

```bash
# Ver información del modelo
ollama show llama3.2:3b

# Parámetros configurables en futuro (Modelfile):
# - temperature (creatividad)
# - top_p (diversidad)
# - num_ctx (tamaño de contexto)
```

### **7. Verificar funcionamiento**

```bash
# Test simple
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Hola, ¿funcionas?",
  "stream": false
}'

# Desde Python
python -c "from backend.services.ollama_client import enviar_mensaje_chat; print(enviar_mensaje_chat('Eres un asistente.', [{'role': 'user', 'content': 'Hola'}]))"
```

### **8. Modelos alternativos**

Si `llama3.2:3b` es muy lento o inconsistente:

```bash
# Opciones más ligeras:
ollama pull phi3:latest          # 2.3GB - Rápido pero menos preciso
ollama pull gemma2:2b           # 1.6GB - Muy rápido

# Opciones más pesadas (mejor calidad):
ollama pull qwen2.5:latest      # 4.7GB - Mejor JSON
ollama pull mistral:latest      # 4.4GB - Balanceado

# Cambiar en .env:
OLLAMA_MODEL=qwen2.5:latest
```

---

## 🚀 FastAPI

### **1. Punto de entrada**

**Ubicación:** `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Indagata API",
    version="1.0.0",
    description="Sistema de gestión de instrumentos educativos."
)

# CORS (permitir frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # En producción: ["https://tu-dominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(router_carga)
app.include_router(router_visualizacion)
```

### **2. Iniciar servidor**

```powershell
# Desde backend/
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Parámetros:
# --reload    : Recarga automática en cambios
# --host      : 0.0.0.0 permite conexiones externas
# --port      : Puerto (default: 8000)
# --workers N : Múltiples workers (producción)
```

### **3. URLs importantes**

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| Documentación interactiva (Swagger) | http://localhost:8000/docs |
| Documentación alternativa (ReDoc) | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| Health check | http://localhost:8000/ |

### **4. Configuración de producción**

```bash
# Con Gunicorn (múltiples workers)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300

# Con systemd (servicio en Linux)
# Ver: /etc/systemd/system/indagata.service
```

---

## 📁 Archivos de configuración

### **Resumen de archivos clave:**

| Archivo | Propósito | Conexiones |
|---------|-----------|------------|
| `backend/.env` | Variables de entorno | PostgreSQL, Ollama, Rutas |
| `backend/api/core/config.py` | Clase de configuración | Lee .env, genera DATABASE_URL |
| `backend/api/database/database.py` | Conexión SQLAlchemy | PostgreSQL (engine + sessions) |
| `backend/services/ollama_client.py` | Cliente HTTP Ollama | Ollama API |
| `backend/services/llm_service.py` | Lógica LLM | Usa ollama_client |
| `backend/main.py` | Entry point FastAPI | Registra routers, CORS |

### **Flujo de configuración:**

```
.env (variables)
  ↓
config.py (lee .env, genera DATABASE_URL)
  ↓
database.py (crea engine con DATABASE_URL)
  ↓
dependencies.py (inyecta sesiones DB en endpoints)
  ↓
routers (usan DBSession)
```

---

## 🔍 Troubleshooting

### **PostgreSQL no conecta**

```powershell
# 1. Verificar que el servicio está corriendo
Get-Service -Name postgresql*

# 2. Iniciar si está detenido
Start-Service -Name postgresql-x64-18

# 3. Verificar puerto
netstat -an | Select-String "5432"

# 4. Probar conexión manual
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -c "SELECT 1;"

# 5. Ver logs de PostgreSQL
# Windows: C:\Program Files\PostgreSQL\18\data\log\
```

### **Ollama no responde**

```bash
# 1. Verificar que está corriendo
curl http://localhost:11434/api/tags

# 2. Ver procesos
tasklist | findstr ollama

# 3. Iniciar manualmente
ollama serve

# 4. Verificar modelo instalado
ollama list | grep llama3.2

# 5. Si falta, descargarlo
ollama pull llama3.2:3b

# 6. Test simple
curl http://localhost:11434/api/generate -d '{"model":"llama3.2:3b","prompt":"Test","stream":false}'
```

### **FastAPI no inicia**

```powershell
# 1. Verificar ambiente virtual activado
Get-Command python | Select-Object Source
# Debe apuntar a .venv

# 2. Reinstalar dependencias
pip install -r requirements.txt

# 3. Verificar puerto libre
netstat -an | Select-String "8000"

# 4. Iniciar en otro puerto
uvicorn main:app --reload --port 8001

# 5. Ver logs detallados
uvicorn main:app --reload --log-level debug
```

### **Error de importación**

```powershell
# 1. Limpiar cache
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse

# 2. Verificar PYTHONPATH
$env:PYTHONPATH

# 3. Reinstalar en modo editable
pip install -e .
```

### **Timeout en LLM**

```python
# En backend/services/ollama_client.py, aumentar timeout:
def enviar_mensaje_chat(
    system_prompt: str,
    historial: list[dict],
    timeout: float = 600.0,  # Aumentar a 10 minutos
) -> str:
    ...
```

---

## 🔗 Conexiones en resumen

### **Diagrama de arquitectura:**

```
┌─────────────────┐
│   Frontend      │
│   (React)       │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   FastAPI       │ ◄─── main.py (puerto 8000)
│   (Backend)     │
└────┬───────┬────┘
     │       │
     │       └──────────────┐
     │                      │
     ▼                      ▼
┌──────────────┐   ┌───────────────┐
│ PostgreSQL   │   │   Ollama      │
│ puerto 5432  │   │ puerto 11434  │
└──────────────┘   └───────────────┘
     │                      │
     │ SQL                  │ HTTP
     │                      │
     ▼                      ▼
┌──────────────┐   ┌───────────────┐
│ tt_rag.*     │   │ llama3.2:3b   │
│ (tablas)     │   │ (modelo LLM)  │
└──────────────┘   └───────────────┘
```

### **Puertos utilizados:**

| Servicio | Puerto | Protocolo |
|----------|--------|-----------|
| FastAPI | 8000 | HTTP |
| PostgreSQL | 5432 | TCP |
| Ollama | 11434 | HTTP |
| ChromaDB (futuro) | 8001 | HTTP |

---

## 📚 Referencias

- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLAlchemy:** https://www.sqlalchemy.org/
- **Pydantic:** https://docs.pydantic.dev/
- **Ollama:** https://ollama.com/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **httpx:** https://www.python-httpx.org/

---

## ✅ Checklist de configuración inicial

- [ ] PostgreSQL instalado y corriendo (puerto 5432)
- [ ] Base de datos `aprende_rag` creada
- [ ] Schema `tt_rag` aplicado (`postgres/init/01_schema.sql`)
- [ ] Seed data cargado (`postgres/init/02_seed.sql`)
- [ ] Ollama instalado
- [ ] Modelo `llama3.2:3b` descargado
- [ ] Ollama corriendo (puerto 11434)
- [ ] Ambiente virtual Python creado (`.venv`)
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Archivo `.env` configurado en `backend/`
- [ ] FastAPI inicia correctamente (`uvicorn main:app --reload`)
- [ ] Documentación accesible: http://localhost:8000/docs

---

**Última actualización:** 2026-09-03


---

## 🧹 Limpieza automática de caché

> Consolidado desde el antiguo `CACHE_LIMPIEZA.md`.

### ¿Qué es el caché?

En `storage/data/` se guardan archivos `.txt` con el texto extraído de cada instrumento (nombrados por hash de contenido). Esto evita re-procesar PDFs/DOCX cada vez. Con el tiempo se acumulan archivos que ya no se usan; el script de limpieza elimina los más viejos que N días.

### Limpieza manual

```powershell
# Eliminar archivos más viejos que 90 días (default)
.\limpiar_cache_antiguedad.ps1

# Personalizar retención (ej: 60 días)
.\limpiar_cache_antiguedad.ps1 -DiasRetencion 60
```

### Limpieza automática (Task Scheduler)

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File C:\Users\yarel\Documents\indagata\indagata\limpiar_cache_antiguedad.ps1" `
    -WorkingDirectory "C:\Users\yarel\Documents\indagata\indagata"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
Register-ScheduledTask -TaskName "IndagataLimpiezaCache" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Limpia archivos de cache antiguos en Indagata (>90 dias)"
```

Gestión de la tarea:

```powershell
Get-ScheduledTask -TaskName "IndagataLimpiezaCache"        # verificar
Start-ScheduledTask -TaskName "IndagataLimpiezaCache"      # ejecutar ahora
Unregister-ScheduledTask -TaskName "IndagataLimpiezaCache" -Confirm:$false  # eliminar
```

### Política de retención

| Configuración | Días | Uso recomendado |
|---------------|------|-----------------|
| Conservadora | 180 | Producción con mucho espacio |
| Estándar | 90 | Recomendado para la mayoría |
| Agresiva | 30 | Entornos con poco espacio |

**Nota:** el script NO elimina el caché de un instrumento que todavía existe en BD y tiene menos de N días desde su última modificación.

### Política de eliminación de instrumentos

Al eliminar un instrumento se **conserva** su caché de texto (opción A). Razón: reutilización si se vuelve a subir el mismo archivo (el hash es rápido, la extracción es lenta); la limpieza por antigüedad se encarga del resto. El log de limpieza se escribe en `storage/data/limpieza.log`.
