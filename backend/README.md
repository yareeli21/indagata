# Indagata — Backend

API REST (FastAPI) para **gestión y consulta de instrumentos de investigación educativa**.
Cada instrumento (encuesta, entrevista, prueba estandarizada) recorre un wizard: se sube,
se documenta con metadatos Dublin Core, se analiza con el **Survey Intelligent System (SIS)**,
se aprueban las propuestas en dos fases (limpieza y enriquecimiento) y se genera un JSON
consolidado listo para el RAG.

> Para el detalle de cada endpoint y cómo probarlos en Postman, ver
> [`api/routers/README.md`](api/routers/README.md).

---

## Arquitectura por capas

```
routers      → HTTP: definen endpoints, validan entrada/salida con schemas
   │
dependencies → Autenticación y control de acceso (inyectadas con Depends)
   │
services     → Lógica de negocio
   ├── api/services/   → BD, orquestación del pipeline, disco
   └── services/       → adaptador del SIS (sis_adapter) + cliente Ollama
   │
survey_intelligence  → Survey Intelligent System (SIS): servicio interno de dominio.
   │                    Instrumento → JSON canónico → JSON consolidado (hexagonal, aislado)
models       → ORM SQLAlchemy (tablas del schema tt_rag en PostgreSQL)
```

**Regla clave:** nada en `api/services/` habla con Ollama directamente. El análisis vive
en el **SIS** (`survey_intelligence/`), que se consume por un único punto de acople:
`services/sis_adapter.py` (implementa el `LLMPort` del SIS sobre `services/ollama_client.py`).
`EtlService.analyze` en `services_carga.py` lo invoca con `from services import sis_adapter`.

> `services/llm_service.py` contiene un camino de análisis por prompts **legacy** del flujo
> ETL antiguo; el flujo vigente pasa por el SIS. Se conserva mientras se decide su destino
> (su parser robusto de JSON podría reutilizarse).

### Estructura de carpetas

```
backend/
├── main.py                    # Punto de entrada FastAPI (registra routers, CORS)
├── requirements.txt
├── api/
│   ├── core/                  # config.py (settings/.env) + security.py (hash de password)
│   ├── database/              # base.py (Base declarativa) + database.py (engine, get_db)
│   ├── models/                # models_instrumentos.py — todos los modelos ORM
│   ├── schemas/               # schemas_carga.py + schemas_visualizacion.py (Pydantic)
│   ├── dependencies/          # dependencies_instrumentos.py — auth y acceso
│   ├── services/              # services_carga.py, services_visualizacion.py, services_compartidos.py
│   └── routers/               # routers_carga.py + routers_visualizacion.py
├── services/                  # sis_adapter.py (acople al SIS) + ollama_client.py (HTTP a Ollama)
│                              #   + llm_service.py (legacy del flujo ETL antiguo)
└── survey_intelligence/       # SIS: facade + contracts + engine + pipeline + ports + export
```

---

## El pipeline (flujo de estados)

El campo `estado` de `instrumento_procesado` controla el avance. El backend rechaza
con **409** cualquier salto de paso.

```
pendiente
   │ POST /instrumentos/upload                       (Paso 1)
metadata_registrado
   │ POST /instrumentos/{id}/metadata                (Paso 2)
   │ POST /instrumentos/{id}/analyze                 (Paso 3 — SIS, requiere Ollama)
etl_pendiente_limpieza
   │ POST /instrumentos/{id}/approve/cleaning        (Paso 4a — transformaciones)
etl_pendiente_enriquecimiento
   │ POST /instrumentos/{id}/approve/enrichment      (Paso 4b — metadatos + KPIs)
etl_aprobado   ← estado final del módulo de carga; genera JSON consolidado (+ .SAV en encuestas)
```

> El paso `analyze` es **reanalizable**: puede repetirse desde `metadata_registrado` o
> `etl_pendiente_limpieza` (borra el análisis previo, no duplica).
>
> **Funcionalidad futura (no implementada aún):** el módulo de vectorización tomará
> instrumentos en `etl_aprobado` y los llevará a `vectorizado` vía un nuevo endpoint
> `POST /instrumentos/{id}/vectorize`. El endpoint `POST /instrumentos/ingesta` está
> comentado como reserva para ese módulo — **no es código muerto**.
>
> Detalle de cada endpoint: [`api/routers/README.md`](api/routers/README.md).

---

## Modelos ORM (schema `tt_rag`)

`InstrumentoProcesado` es la tabla central; las demás apuntan a ella por FK.

| Modelo | Tabla | Rol |
|---|---|---|
| `Usuario` | `usuarios` | Propietario (solo lectura para resolver nombre) |
| `InstrumentoProcesado` | `instrumento_procesado` | Registro maestro: `estado` + rutas de artefactos |
| `MetadatosDC` | `metadatos_dc` | 13 campos Dublin Core (Paso 2) |
| `EtlPropuesta` | `etl_propuesta` | Propuestas del LLM (Pasos 3 y 4) |
| `MetadatosEnriquecidos` | `metadatos_enriquecidos` | Enriquecimiento aprobado (Paso 4) |
| `KpiInferido` | `kpi_inferido` | KPIs aceptados (FK a `kpi.kpi_id`) |
| `PermisoInstrumento` | `permiso_instrumento` | Control de acceso (propietario) |
| `PipelineIngestaLog` | `pipeline_ingesta_log` | Log interno, nunca expuesto por la API |

La tabla `kpi` es de catálogo (la referencia `kpi_inferido`); no la gestiona esta API.

---

## Metadatos Dublin Core (Paso 2)

Son 13 campos. El backend **autocompleta 6** y el usuario **captura 7**.

| Autocompletados (6) | Origen |
|---|---|
| `dc_creator` | usuario autenticado |
| `dc_publisher` | configuración institucional (`APP_NAME`) |
| `dc_type` | `tipo_instrumento` |
| `dc_format` | extensión del archivo |
| `dc_date` | fecha de registro |
| `dc_language` | `"es"` por defecto |

| Captura manual (7) | Notas |
|---|---|
| `dc_title` | obligatorio; se inicializa con el nombre del instrumento |
| `dc_subject` | lista de strings, al menos 1 |
| `dc_description` | obligatorio |
| `dc_coverage` | obligatorio |
| `dc_rights` | obligatorio |
| `dc_source` | opcional |
| `dc_relation` | opcional |

`GET /instrumentos/{id}/metadata/init` devuelve los 6 autocompletados + `dc_title_sugerido`
para pre-poblar el formulario. `POST /instrumentos/{id}/metadata` recibe solo los 7 manuales
(el `instrumento_id` va en la URL, no en el body). Registrar metadatos es **inmutable**:
un segundo intento devuelve 409.

---

## Autenticación

> **Estado actual: MODO DESARROLLO.** `get_current_user` en
> `api/dependencies/dependencies_instrumentos.py` devuelve un usuario fijo
> (`_DEV_USER_ID = 1`) sin pedir token. Ese usuario debe existir en `tt_rag.usuarios`.
>
> El bloque de **autenticación real (JWT)** y `api/core/security.py` (hash de contraseñas)
> ya están escritos pero inactivos. **No son código muerto: son funcionalidad futura**
> pendiente de integración, que se activará junto con `POST /auth/token`.

Las dependencias de acceso ya están listas y se inyectan por tipo:

| Tipo anotado | Verifica | Usado en |
|---|---|---|
| `UsuarioActual` | Usuario actual (hoy: fijo; futuro: JWT) | Todos |
| `DBSession` | Sesión SQLAlchemy | Todos |
| `InstrumentoAcceso` | Instrumento público **o** propietario | Lectura (detalle, download) |
| `InstrumentoProp` | Solo propietario | Escritura (ETL, approve, ingesta, delete) |

### Activar el login real (pendiente)

1. Borrar la función `get_current_user` del bloque **MODO DESARROLLO** (y la constante `_DEV_USER_ID`).
2. Descomentar el bloque **AUTENTICACIÓN REAL** (ya escrito, solo hay que quitar los `#`): valida el JWT con `settings.SECRET_KEY`.
3. No tocar nada más: los tipos anotados y los endpoints ya están preparados para el token.
4. Crear un router de auth con `POST /auth/token` que reciba usuario+contraseña, valide con `verificar_password()` de `core/security.py` y devuelva un JWT firmado.

En ese momento, en Postman se hará primero `POST /auth/token` y el token se enviará en el
header `Authorization: Bearer {{token}}`.

---

## Cómo arrancar

Requisitos: Python 3.11+, PostgreSQL con el schema `tt_rag`, y Ollama (solo para el Paso 3).

```powershell
# Desde backend/, con el entorno virtual del proyecto
c:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

| Servicio | URL | Verificar |
|---|---|---|
| Backend | http://localhost:8000 | `GET /` → `{"status":"ok"}` |
| Swagger UI | http://localhost:8000/docs | Documentación interactiva |
| PostgreSQL | — | El backend arranca sin error de conexión |
| Ollama | http://localhost:11434 | `"Ollama is running"` (solo Paso 3) |

La conexión a BD se configura con `settings.DATABASE_URL` (ver `api/core/config.py` y `.env`).
El modelo LLM se define en el `.env` (`OLLAMA_MODEL`); descargarlo con `ollama pull <modelo>`.
