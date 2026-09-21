# Indagata - Sistema RAG para Instrumentos de Investigación

Sistema backend para carga, procesamiento y consulta de instrumentos de investigación educativa usando RAG (Retrieval-Augmented Generation).

---

## 🏗️ Arquitectura

```
indagata/
├── backend/               # FastAPI + servicios
│   ├── api/
│   │   ├── routers/      # Endpoints HTTP
│   │   ├── services/     # Lógica de negocio
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   └── dependencies/ # Autenticación y permisos
│   ├── services/         # Acople al SIS (sis_adapter) + cliente Ollama
│   ├── survey_intelligence/  # SIS: servicio de dominio (canónico → consolidado)
│   └── main.py           # Entry point
├── postgres/
│   ├── init/             # Schema + seed data
│   └── migrations/       # Migraciones SQL
├── storage/              # Archivos físicos
│   ├── raw/             # Archivos originales
│   ├── json/            # JSON consolidados
│   ├── sav/             # Archivos SPSS (encuestas)
│   ├── clean/          # Dataset limpio (encuestas)
│   ├── data/            # Caché de texto extraído (por hash) + cachés del SIS
│   └── temp/            # Temporales
├── frontend/             # Frontend (Jinja2 + estático)
└── .venv/               # Ambiente virtual Python

```

---

## 🚀 Inicio rápido

### **1. Pre-requisitos**

- Python 3.11+
- PostgreSQL (schema `tt_rag`)
- Ollama (modelo definido en `.env` → `OLLAMA_MODEL`)

### **2. Activar ambiente**

```powershell
cd c:\Users\yarel\Documents\indagata\indagata
.\.venv\Scripts\Activate
```

### **3. Iniciar PostgreSQL**

```powershell
# Como administrador
Start-Service -Name postgresql-x64-18
```

### **4. Iniciar backend**

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **5. Documentación API**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📋 Flujo de trabajo

### **Módulo: Carga de instrumentos**

**Endpoints (routers_carga.py):**

1. `POST /instrumentos/upload` → Subir archivo (+ codebook opcional en encuestas)
2. `GET /instrumentos/{id}/metadata/init` → Datos pre-poblados
3. `POST /instrumentos/{id}/metadata` → Registrar 7 campos DC
4. `POST /instrumentos/{id}/analyze` → El SIS analiza (Ollama) y persiste propuestas
5. `GET /instrumentos/{id}/etl/proposals` → Ver propuestas
6. `POST /instrumentos/{id}/approve/cleaning` → Decidir transformaciones (dataset limpio)
7. `POST /instrumentos/{id}/approve/enrichment` → **FINAL** - Metadatos + KPIs, genera JSON (y .SAV en encuestas)

**Estados:**
```
pendiente → metadata_registrado → etl_pendiente_limpieza
   → etl_pendiente_enriquecimiento → etl_aprobado
```

### **Módulo: Visualización**

**Endpoints (routers_visualizacion.py):**

1. `GET /kpis` → Catálogo de KPIs
2. `GET /instrumentos` → Listar todos (público)
3. `GET /instrumentos/{id}` → Detalle completo (público)
4. `GET /instrumentos/{id}/download?type=original|json|sav` → Descargar (público)
5. `DELETE /instrumentos/{id}` → Eliminar (solo propietario)

---

## 🔐 Sistema de permisos

### **Filosofía: RAG Colaborativo**

- ✅ **Lectura:** Todos los usuarios pueden ver y descargar cualquier instrumento
- ✅ **Escritura:** Solo el propietario puede aprobar ETL y eliminar
- ❌ **Sin edición:** Datos inmutables después de aprobar - eliminar y re-subir para cambiar

### **Tabla `permiso_instrumento`:**
- Define propietario de cada instrumento
- Se usa solo para validar escritura/eliminación

---

## 📊 Base de datos

### **Conexión:**
```
postgresql://postgres:ttaprobado@localhost:5432/aprende_rag
Schema: tt_rag
```

### **Tablas principales:**

**Maestras (persistentes):**
- `usuarios` - Usuarios del sistema
- `kpi` - Catálogo de indicadores (55)
- `kpi_variable` - Relaciones KPI-Variable (116)
- `variable` - Variables del sistema (91)

**Instrumentos (operacionales):**
- `instrumento_procesado` - Registro maestro
- `metadatos_dc` - 13 campos Dublin Core
- `kpi_inferido` - KPIs detectados por LLM
- `etl_propuesta` - Propuestas del LLM
- `metadatos_enriquecidos` - Metadatos adicionales
- `permiso_instrumento` - Propietarios
- `pipeline_ingesta_log` - Logs internos

---

## 🧹 Limpieza para testing

### **1. Limpiar base de datos:**

```powershell
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f postgres\migrations\04_limpiar_datos_prueba.sql
```

### **2. Limpiar archivos:**

```powershell
.\limpiar_storage.ps1
```

**Resultado:** Sistema limpio, IDs empiezan desde 1.

---

## 🤖 Configuración LLM

### **Modelo actual:** `llama3.2:3b`

```bash
# Verificar que está instalado
ollama list | grep llama3.2

# Si no está, instalarlo
ollama pull llama3.2:3b

# Iniciar Ollama
ollama serve
```

### **Configuración en `.env`:**
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

---

## 📝 Metadatos Dublin Core

### **13 campos estándar:**

**Autocompletados (6):**
- `dc_creator` → Usuario autenticado
- `dc_publisher` → Nombre de la app
- `dc_type` → Tipo de instrumento
- `dc_format` → Extensión del archivo
- `dc_date` → Fecha de registro
- `dc_language` → "es" (100% español)

**Manuales (7):**
- `dc_title` → Título del instrumento
- `dc_subject` → Temas (array de strings)
- `dc_description` → Descripción
- `dc_coverage` → Cobertura espacial/temporal
- `dc_rights` → Derechos de uso
- `dc_source` → Fuente original (opcional)
- `dc_relation` → Relación con otros (opcional)

**Eliminados:**
- ❌ `dc_contributor` - No aplica
- ❌ `dc_identifier` - Se usa `instrumento_id`

---

## 🗂️ Archivos generados

### **Estructura en `storage/`:**

```
storage/
├── raw/               # Archivos originales subidos
│   └── 1_encuesta_2024.xlsx
├── json/              # JSON consolidados (desde approve)
│   └── 1.json
├── sav/               # SPSS files (encuestas)
│   └── 1.sav
├── clean/             # Dataset limpio (encuestas)
│   └── 1_clean.csv
├── data/              # Caché de texto extraído (por hash) + cachés del SIS
│   └── {hash}.txt
└── temp/              # Temporales
```

### **JSON consolidado (generado en approve/enrichment):**

Es **puramente semántico** (insumo del RAG): NO incluye texto crudo, estados ni fechas de proceso.
Contiene el envoltorio común (`instrument_type`, `summary_humano`, `traceability`, `rag_hints`) y,
según el tipo, `unidades_semanticas` + `hallazgos_analiticos` + `kpis` (encuestas) o
`knowledge_entrevista` (entrevistas). Forma aproximada:

```json
{
  "instrumento_id": 1,
  "titulo": "...",
  "tipo_instrumento": "encuesta",
  "instrument_type": "encuesta",
  "schema_version": "sis-1.x.0",
  "metadata_dc": { "dc_title": "...", "dc_creator": "..." },
  "resumen": { "proposito_inferido": "..." },
  "unidades_semanticas": [ { "variable_id": "...", "constructo": "...", "texto": "..." } ],
  "kpis": [ { "kpi_id": 5, "nombre": "Deserción escolar", "score_inferencia": 0.85 } ],
  "hallazgos_analiticos": [ ... ],
  "summary_humano": { "que_se_analizo": "...", "que_se_encontro": "..." },
  "traceability": { "unidades": [ ... ] },
  "rag_hints": { "chunk_units": [ ... ], "embeddable_fields": [ ... ] },
  "generado_en": "..."
}
```

---

## 📚 Documentación adicional

- **API Endpoints:** `backend/api/routers/README.md`
- **PostgreSQL:** `postgres/README.md`
- **Changelog:** `CHANGELOG.md`
- **Migraciones:** `postgres/migrations/`

---

## 🔧 Troubleshooting

### **PostgreSQL no inicia:**
```powershell
# Verificar servicio
Get-Service -Name postgresql*

# Iniciar como admin
Start-Service -Name postgresql-x64-18
```

### **Ollama no responde:**
```bash
# Verificar que está corriendo
curl http://localhost:11434/api/tags

# Si no responde, iniciarlo
ollama serve
```

### **Error al importar:**
```powershell
# Eliminar archivos .pyc
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item

# Reiniciar servidor
# Ctrl+C y luego:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🚧 Roadmap

### **Completado ✅**
- [x] CRUD de instrumentos
- [x] Metadatos Dublin Core (13 campos)
- [x] ETL con LLM (llama3.2:3b)
- [x] KPIs inferidos automáticamente
- [x] JSON consolidado
- [x] Sistema de permisos (público + propietario)
- [x] Eliminación de visibilidad (todo público)

### **Pendiente 📋**
- [ ] Generación de archivos .SAV (encuestas)
- [ ] Vectorización (ChromaDB)
- [ ] Módulo RAG (consultas)
- [ ] Frontend (React)
- [ ] Autenticación JWT
- [ ] Tests automatizados

---

## 👥 Equipo

Desarrollado para gestión de instrumentos de investigación educativa.

**Stack:**
- Backend: FastAPI + SQLAlchemy + Pydantic
- BD: PostgreSQL 18
- LLM: Ollama (llama3.2:3b)
- Vector DB: ChromaDB (futuro)

---

## 📄 Licencia

Proyecto interno - Todos los derechos reservados.
