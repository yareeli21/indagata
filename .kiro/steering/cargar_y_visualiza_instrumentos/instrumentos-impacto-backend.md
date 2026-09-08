---
inclusion: manual
---

# Instrumentos de Investigación — Impacto en el Backend Existente
**Versión:** 1.2  
**Fecha:** Agosto 2026  
**Alcance:** Estado actual del código y la base de datos, cambios aplicados y pendientes, decisiones de diseño relevantes para la implementación.

---

## 1. Estado actual del backend

### 1.1 Estructura de archivos

La estructura de carpetas del proyecto sigue una organización por tipo de archivo dentro de cada módulo funcional. Cada pantalla o grupo de pantallas tiene sus propios archivos en cada carpeta.

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          ✓ EXISTE — paths de storage, variables de entorno
│   │   ├── security.py        ✓ EXISTE — hashing con bcrypt
│   │   └── ollama_client.py   ✓ EXISTE — cliente base para Ollama
│   └── database/
│       ├── base.py            ✓ EXISTE — DeclarativeBase de SQLAlchemy
│       └── database.py        ✓ EXISTE — engine síncrono, SessionLocal, get_db
│
├── routers/
│   └── instrumentos.py        ✓ GENERADO — endpoints de las 4 pantallas
│
├── schemas/
│   └── instrumentos.py        ✓ GENERADO — schemas Pydantic de entrada y salida
│
├── models/
│   └── instrumentos.py        ✓ GENERADO — modelos ORM (InstrumentoProcesado, RawData, etc.)
│
├── services/
│   └── instrumentos.py        ✓ GENERADO — lógica de negocio
│
├── dependencies/
│   └── instrumentos.py        ✓ GENERADO — get_current_user, puede_acceder, verificar_propietario
│
├── pipeline_limpieza/         ⬜ PENDIENTE — módulo interno del pipeline
│   ├── orchestrator.py
│   ├── extractor.py
│   ├── llm_cleaner.py
│   ├── json_writer.py
│   └── prompts/
│       └── limpieza_v1.txt
│
└── main.py                    ✓ EXISTE — registrar routers y startup del pipeline
```

> Nota: los archivos generados en la sesión anterior están en `cargar_instru/`. Cuando se reorganice a la estructura por carpetas, cada archivo se mueve a su carpeta correspondiente y se ajustan los imports. El contenido lógico es idéntico; solo cambia la ruta de importación.

### 1.2 Archivos Python generados para las pantallas de instrumentos

| Archivo | Ubicación actual | Ubicación destino | Estado |
|---|---|---|---|
| `models.py` | `cargar_instru/models.py` | `models/instrumentos.py` | ✓ Generado |
| `schemas.py` | `cargar_instru/schemas.py` | `schemas/instrumentos.py` | ✓ Generado |
| `dependencies.py` | `cargar_instru/dependencies.py` | `dependencies/instrumentos.py` | ✓ Generado |
| `services.py` | `cargar_instru/services.py` | `services/instrumentos.py` | ✓ Generado |
| `routers_cargar_instru.py` | `cargar_instru/routers_cargar_instru.py` | `routers/instrumentos.py` | ✓ Generado |

### 1.3 Centralización en `main.py`

Todos los routers se registran en `main.py`. Para las pantallas de instrumentos:

```python
# main.py (fragmento relevante)
from routers.instrumentos import app as router_instrumentos

app.include_router(router_instrumentos, prefix="/route_instru", tags=["instrumentos"])
```

Para múltiples módulos futuros el patrón se repite. La convención es:
- Prefijo `/route_{modulo}` para los endpoints de usuario.
- Tag descriptivo para la documentación en Swagger.
- El router de cada módulo se importa desde `routers/{modulo}.py`.

El pipeline de limpieza se inicializa en el evento `startup`:

```python
@app.on_event("startup")
async def startup_event():
    from pipeline_limpieza.orchestrator import LimpiezaOrchestrator
    orchestrator = LimpiezaOrchestrator()
    asyncio.create_task(orchestrator.run_polling_loop())
```

---

## 2. Estado de la base de datos

### 2.1 `instrumento_procesado` — estado actual en `01_schema.sql`

✓ **Aplicados en el schema:**
- `tipo_instrumento VARCHAR(30) NOT NULL` con CHECK correcto
- `estado` con CHECK de 5 valores: `recibido`, `limpio`, `estandarizado`, `vectorizado`, `error`
- `visibilidad VARCHAR(10) NOT NULL DEFAULT 'publico'` con CHECK
- `version INTEGER NOT NULL DEFAULT 1`
- `schema_version VARCHAR(10) DEFAULT '1.0'`
- `ruta_texto_limpio TEXT`
- `error_detalle TEXT`
- `creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`
- Eliminada columna `metadatos JSONB`

⚠️ **Verificar al aplicar:** el DEFAULT del estado era `'ingresado'` en la versión anterior. Confirmar que quede `'recibido'`.

### 2.2 `raw_data` — estado actual

✓ **Aplicado:**
- Eliminada restricción `UNIQUE` global sobre `hash_md5`.
- Creado `CREATE UNIQUE INDEX uidx_raw_data_hash_usuario ON raw_data (hash_md5, usuario_id) WHERE hash_md5 IS NOT NULL`.

**Decisión de diseño — sin historial de versiones:**
El sistema no mantiene historial de archivos. Cada instrumento tiene exactamente un archivo físico en `storage/raw/`. Al reemplazar el archivo:
- El archivo anterior se elimina del disco.
- El registro `raw_data` existente se actualiza (no se crea uno nuevo).
- El JSON canónico y el .sav se eliminan.
- El estado regresa a `recibido`.

Esto simplifica `raw_data` de "tabla de historial" a "tabla de archivo actual". La columna `version` en `instrumento_procesado` queda como contador de reemplazos (para auditoría interna), sin exponerse en la interfaz.

**Endpoints eliminados por esta decisión:**
- ~~`GET /instrumentos/{id}/versiones`~~ — no existe historial
- ~~`GET /instrumentos/{id}/versiones/{raw_id}/descargar`~~ — no existe historial

### 2.3 `permiso_instrumento` — estado actual

✓ **Aplicado en el schema:**
- Tabla creada con `rol VARCHAR(20) CHECK (rol = 'propietario')`.
- **`UNIQUE (instrumento_id, usuario_id)` aplicado como constraint inline** en la definición de la tabla.

La sintaxis correcta en PostgreSQL es:

```sql
CREATE TABLE IF NOT EXISTS permiso_instrumento (
    ...
    UNIQUE (instrumento_id, usuario_id),
    ...
);
```

Esto se diferencia de `CREATE UNIQUE INDEX` en que el UNIQUE constraint crea implícitamente un índice único y además permite que sea referenciado como constraint nombrado. Es la forma recomendada para restricciones de integridad de negocio.

### 2.4 `pipeline_limpieza_log` — estado actual

✓ **Aplicado en el schema:**
- Tabla creada con CHECK correcto: `CHECK (resultado IN ('en_proceso', 'exitoso', 'error'))`.
- Índice parcial para lock optimista: `WHERE resultado = 'en_proceso'`.
- Columna `segmentos INTEGER` agregada para rastrear divisiones de texto largo.

**Nota sobre el CHECK anterior (incorrecto):** `CHECK('propietario')` y `CHECK('en_proceso', 'exitoso', 'error')` no son SQL válido. Un CHECK sobre una columna debe referenciar esa columna: `CHECK(col = 'valor')` o `CHECK(col IN (...))`. El schema actual tiene la sintaxis correcta.

---

## 3. Cambios pendientes en `01_schema.sql` al aplicar al contenedor

El schema revisado es un reemplazo completo del archivo. Al aplicarlo sobre el contenedor PostgreSQL existente hay que considerar:

1. Si la BD tiene datos, no se puede simplemente correr `01_schema.sql` — hay que usar `ALTER TABLE` incrementales o destruir y recrear el contenedor.
2. En desarrollo: destruir el contenedor PostgreSQL y recrearlo con el nuevo schema es lo más limpio.
3. En producción: usar migraciones (Alembic u otro).

Para desarrollo con Docker:
```bash
docker compose down -v        # elimina el volumen con los datos
docker compose up -d postgres # recrea con el schema nuevo
```

---

## 4. Proceso de actualización de metadatos — impacto en todo el sistema

Cuando el investigador edita metadatos (Dublin Core, contexto, específico), el impacto depende del estado actual del instrumento:

| Estado al editar | Qué cambia en la BD | Qué cambia en disco | Qué cambia en ChromaDB |
|---|---|---|---|
| `recibido` | `nombre` si dc_title cambió | Nada (JSON no existe aún) | Nada (no hay chunks) |
| `limpio` | `nombre` si dc_title cambió | Nada (JSON no existe aún) | Nada (no hay chunks) |
| `estandarizado` | `nombre` si dc_title cambió, `fecha_procesamiento` | JSON canónico actualizado en disco (merge parcial) | Nada (aún no hay chunks activos) |
| `vectorizado` | `nombre`, `fecha_procesamiento`, `estado → 'estandarizado'` | JSON canónico actualizado en disco | Chunks marcados `activo = FALSE` en `documento_vectorizado`. El pipeline re-vectoriza con el JSON actualizado. |

**El principio es siempre el mismo: el sistema siempre refleja lo más reciente.** No hay versiones de metadatos. Si se edita algo, lo anterior deja de existir.

---

## 5. `config.py` — cambios aplicados

✓ **Aplicados:**
- `DATA_PATH: str` y propiedad `data_path_abs`
- `LIMPIEZA_VENTANA_CHARS: int = 1000`
- `LIMPIEZA_SOLAPE_CHARS: int = 150`
- `LIMPIEZA_INTERVALO_SEGUNDOS: int = 30`
- `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60`

---

## 6. `requirements.txt` — cambios pendientes

| Biblioteca | Estado | Por qué |
|---|---|---|
| `python-docx>=1.1.0` | ⬜ Pendiente de agregar | Extracción de texto de archivos `.docx` |
| `pyreadstat>=1.2.0` | ⬜ Pendiente de agregar | Generación de archivos `.sav` (SPSS) para encuestas |

---

## 7. Tabla resumen de estado

| Componente | Estado | Pendiente |
|---|---|---|
| `01_schema.sql` | ✓ Reescrito completo | Aplicar al contenedor PostgreSQL |
| `config.py` | ✓ Actualizado | — |
| `models/instrumentos.py` | ✓ Generado | Mover a carpeta `models/` |
| `schemas/instrumentos.py` | ✓ Generado | Mover a carpeta `schemas/` |
| `dependencies/instrumentos.py` | ✓ Generado | Mover a carpeta `dependencies/` |
| `services/instrumentos.py` | ✓ Generado | Ajustar: eliminar historial de versiones |
| `routers/instrumentos.py` | ✓ Generado | Ajustar: eliminar endpoints de versiones |
| `requirements.txt` | ⬜ Pendiente | Agregar python-docx y pyreadstat |
| `main.py` | ⬜ Pendiente | Registrar routers, inicializar pipeline |
| `pipeline_limpieza/` | ⬜ Pendiente | Crear módulo completo |
