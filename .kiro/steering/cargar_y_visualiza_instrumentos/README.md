# Módulo: Carga y Visualización de Instrumentos

**Última actualización:** 2026-09-20

## 📋 Descripción

Módulo completo para gestión de instrumentos de investigación educativa:
- **Carga:** Wizard (upload → metadata → analyze (SIS) → approve/cleaning → approve/enrichment)
- **Visualización:** Catálogo, detalle, descarga y eliminación

> El análisis lo ejecuta el **SIS** (`survey_intelligence/`), invocado por `services/sis_adapter.py`.
> Ver `backend/ARCHITECTURE_AUDIT_REPORT.md` para el detalle del backend.

---

## 🏗️ Arquitectura

### **Clean Architecture:**

```
Presentación (Routers)
    ↓
Aplicación (Services)
    ↓
Dominio (Models + Schemas)
    ↓
Infraestructura (Database + LLM)
```

### **Archivos clave:**

| Capa | Archivos | Responsabilidad |
|------|----------|----------------|
| **Routers** | `routers_carga.py`<br>`routers_visualizacion.py` | Endpoints HTTP, validación de entrada |
| **Services** | `services_carga.py`<br>`services_visualizacion.py` | Lógica de negocio |
| **Models** | `models_instrumentos.py` | Modelos SQLAlchemy (BD) |
| **Schemas** | `schemas_carga.py`<br>`schemas_visualizacion.py` | Modelos Pydantic (API) |
| **Dependencies** | `dependencies_instrumentos.py` | Autenticación, permisos |
| **SIS / LLM** | `services/sis_adapter.py`<br>`services/ollama_client.py`<br>`survey_intelligence/` | Análisis con el SIS sobre Ollama |

---

## 🚀 Flujo de endpoints

### **Módulo Carga (flujo vigente):**

```
1. POST /instrumentos/upload
   ↓ (archivo + tipo_instrumento, + codebook opcional en encuestas)
   Estado: pendiente

2. GET /instrumentos/{id}/metadata/init
   ↓ (devuelve 6 campos autocompletados)

3. POST /instrumentos/{id}/metadata
   ↓ (7 campos manuales)
   Estado: metadata_registrado

4. POST /instrumentos/{id}/analyze
   ↓ (el SIS analiza y persiste propuestas; reanalizable)
   Estado: etl_pendiente_limpieza

5. GET /instrumentos/{id}/etl/proposals
   ↓ (ver propuestas generadas)

6. POST /instrumentos/{id}/approve/cleaning
   ↓ (decidir transformaciones; genera dataset limpio)
   Estado: etl_pendiente_enriquecimiento

7. POST /instrumentos/{id}/approve/enrichment
   ↓ (decidir metadatos + KPIs; genera JSON consolidado y .SAV en encuestas)
   Estado: etl_aprobado ✅ FINAL
```

> El endpoint `POST /instrumentos/ingesta` está comentado (reservado para el módulo de vectorización futuro).

### **Módulo Visualización (5 endpoints):**

```
1. GET /kpis
   → Catálogo de indicadores (55 KPIs)
   
2. GET /instrumentos
   → Lista instrumentos (acceso público)
   Filtros: tipo, KPI, búsqueda, fechas
   
3. GET /instrumentos/{id}
   → Detalle completo (acceso público)
   
4. GET /instrumentos/{id}/download?type=original|json|sav
   → Descargar archivos (acceso público)
   
5. DELETE /instrumentos/{id}
   → Eliminar (solo propietario)
```

---

## 🔐 Sistema de permisos

### **Filosofía: RAG Colaborativo**
- ✅ **Lectura:** Todos pueden ver/descargar cualquier instrumento
- ✅ **Escritura:** Solo propietario puede aprobar ETL y eliminar
- ❌ **Edición:** Datos inmutables → eliminar y re-subir

### **Funciones de autorización:**

```python
# dependencies_instrumentos.py

def puede_acceder_o_403(...) -> InstrumentoProcesado:
    """Lectura: siempre permite (todo público)"""
    return instrumento

def verificar_propietario(...) -> InstrumentoProcesado:
    """Escritura: valida permiso en BD"""
    permiso = db.query(PermisoInstrumento).filter(...).first()
    if permiso is None:
        raise HTTPException(403)
    return instrumento
```

---

## 📊 Metadatos Dublin Core

### **13 campos estándar:**

| Campo | Origen | Descripción |
|-------|--------|-------------|
| `dc_title` | Manual | Título del instrumento |
| `dc_creator` | Auto | Usuario autenticado |
| `dc_subject` | Manual | Temas (array) |
| `dc_description` | Manual | Descripción |
| `dc_publisher` | Auto | Nombre de la app |
| `dc_date` | Auto | Fecha de registro |
| `dc_type` | Auto | Tipo de instrumento |
| `dc_format` | Auto | Extensión del archivo |
| `dc_language` | Auto | "es" (100% español) |
| `dc_coverage` | Manual | Cobertura espacial/temporal |
| `dc_rights` | Manual | Derechos de uso |
| `dc_source` | Manual (opcional) | Fuente original |
| `dc_relation` | Manual (opcional) | Relación con otros |

**Eliminados:**
- ❌ `dc_contributor` - No aplica
- ❌ `dc_identifier` - Se usa `instrumento_id`

---

## 🤖 Análisis con el SIS

### **Proceso (endpoint `analyze`):**

```
# services_carga.py → EtlService.analyze()  (host)

1. Extraer texto (solo documentos: entrevista/prueba)
   api/services/extraction/ (dispatch por formato, con caché por hash)

2. Construir el request y ejecutar el SIS
   services/sis_adapter.build_request(...) → build_service(db) → service.process(request)
   El SIS (survey_intelligence/) corre S1..S10 sobre Ollama.

3. Persistir el resultado (transaccional, idempotente)
   carga_sis_mapping._persistir_propuestas_sis / _persistir_improvements
   tabla: etl_propuesta (estado: pendiente); improvement_opportunity

4. Estado → etl_pendiente_limpieza
```

### **Tipos de propuestas:**

1. **transformacion:** limpieza estructural (drop_columns, normalize_scale) — se deciden en `approve/cleaning`.
2. **metadato_enriquecido:** cara semántica de cada variable — se decide en `approve/enrichment`.
3. **kpi_sugerido:** KPIs del catálogo inferidos por el SIS — se decide en `approve/enrichment`.

> Nota: `services/llm_service.py` ya NO realiza el análisis ETL (era el flujo antiguo, retirado).
> Hoy solo conserva contratos futuros del RAG. El análisis vive en el SIS.

---

## 📁 Estructura de archivos

```
storage/
├── raw/                # Archivos originales subidos
│   └── 1_encuesta.xlsx
├── data/               # Caché de texto extraído (por hash) + cachés del SIS
│   └── {hash}.txt
├── json/               # JSON consolidado (desde approve)
│   └── 1.json
├── sav/                # SPSS files (futuro, solo encuestas)
│   └── 1.sav
└── temp/               # Temporales (vacío actualmente)
```

---

## 🗄️ Base de datos

### **Tablas principales:**

| Tabla | Descripción |
|-------|-------------|
| `instrumento_procesado` | Registro maestro (sin visibilidad) |
| `metadatos_dc` | 13 campos Dublin Core |
| `kpi_inferido` | KPIs detectados/aceptados |
| `etl_propuesta` | Propuestas del LLM |
| `metadatos_enriquecidos` | Campos adicionales (JSONB) |
| `permiso_instrumento` | Propietarios |
| `pipeline_ingesta_log` | Logs internos |

### **Estados del pipeline:**

```
pendiente → metadata_registrado → etl_pendiente_limpieza
   → etl_pendiente_enriquecimiento → etl_aprobado
```

**Estado final actual:** `etl_aprobado`

**Futuro:** `vectorizado` (cuando se implemente el RAG principal / ChromaDB)

---

## 🔧 Configuración

### **Variables de entorno (.env):**

```ini
# PostgreSQL
POSTGRES_DB=aprende_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=ttaprobado
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Rutas
RAW_PATH=storage/raw
JSON_PATH=storage/json
SAV_PATH=storage/sav
DATA_PATH=storage/data
TEMP_PATH=storage/temp

# Seguridad
SECRET_KEY=vamos_a_poner_una_llavesota
```

Ver más: `CONFIGURACION.md`

---

## 📚 Documentación relacionada

- **API Endpoints:** `backend/api/routers/README.md`
- **Configuración completa:** `CONFIGURACION.md`
- **Changelog:** `CHANGELOG.md`
- **PostgreSQL:** `postgres/README.md`

---

## ✅ Cambios recientes (2026-09-03)

### **Eliminado sistema de visibilidad:**
- ❌ Campo `visibilidad` eliminado de BD y código
- ✅ Todo es público (RAG colaborativo)
- ✅ Permisos solo para escritura/eliminación

### **Metadatos consolidados:**
- ❌ Eliminados: `dc_contributor`, `dc_identifier`
- ✅ 13 campos DC estándar
- ✅ 6 autocompletados + 7 manuales

### **JSON consolidado:**
- ✅ Generado automáticamente en approve()
- ✅ Guardado en `storage/json/{id}.json`
- ✅ Ruta actualizada en BD

---

## 🚧 Pendiente (Roadmap)

- [ ] Generación de archivos .SAV (encuestas)
- [ ] Vectorización (ChromaDB)
- [ ] Módulo RAG (consultas)
- [ ] Frontend (React)
- [ ] Autenticación JWT activa
- [ ] Tests automatizados
