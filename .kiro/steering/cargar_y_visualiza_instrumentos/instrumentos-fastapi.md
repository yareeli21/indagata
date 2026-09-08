---
inclusion: manual
---

# Instrumentos de Investigación — Diseño FastAPI
**Versión:** 1.1  
**Fecha:** Agosto 2026  
**Alcance:** Diseño de modelos ORM, schemas Pydantic, services, routers y dependencias. Sin código productivo — únicamente estructura, contratos y decisiones de diseño.

---

## 1. Qué cambia, por qué y qué problema resuelve

### El estado actual

El módulo `cargar_instru` existe en el repositorio pero está vacío: un router con un único endpoint de prueba y tres archivos (`schemas.py`, `services.py`, `modules.py`) completamente vacíos. No hay modelos ORM, no hay lógica de negocio y no hay autenticación.

### Lo que este diseño construye

Este documento define la estructura completa de los cinco archivos Python del módulo, alineada con:
- Cuatro estados de pipeline: `recibido`, `limpio`, `estandarizado`, `vectorizado` (más `error`). Sin estado `catalogado`.
- Dos actores de usuario: Investigador y Administrador. Sin rol Colaborador ni Lector.
- Visibilidad por defecto: `publico`. Sin permisos individuales por usuario.
- 13 campos Dublin Core obligatorios en la carga. Sin metadatos en borrador.
- JSON canónico generado automáticamente al completar la estandarización (inferencia KPI). Sin endpoint `/catalogar`.
- `pipeline_limpieza_log` es exclusivamente interna del pipeline. La interfaz no la consulta.
- Archivo `.sav` solo para encuestas, desde `estandarizado`.
- Filtros de catálogo: texto, tipo, visibilidad, autor, rango de fechas. Sin filtro de estado.

### Problema principal que resuelve

La ausencia de estructura hace que cualquier lógica tienda a mezclarse en los routers. Este diseño establece responsabilidades claras: los routers solo coordinan request/response, los services contienen la lógica, los models mapean la BD y los schemas validan contratos HTTP.

---

## 2. `models.py` — Modelos SQLAlchemy

**Ubicación:** `backend/cargar_instru/models.py`

**Qué cambia:** Archivo vacío → modelos ORM completos alineados con el esquema revisado.

**Por qué:** SQLAlchemy necesita clases Python que mapeen las tablas. Sin modelos no hay ORM.

**Problema que resuelve:** Queries tipadas, relaciones declarativas, sin SQL crudo disperso en el código.

### Modelos a definir

#### `InstrumentoProcesado`

Mapea `tt_rag.instrumento_procesado`.

Columnas que el modelo debe incluir:
- `instrumento_id` — PK autoincremental
- `nombre` — VARCHAR(255), obligatorio
- `tipo_instrumento` — VARCHAR(30), CHECK (`encuesta` | `entrevista` | `prueba_estandarizada`), obligatorio
- `plataforma` — VARCHAR(50), nullable
- `ruta_json` — TEXT, nullable (ruta al JSON canónico; existe desde estado `estandarizado`)
- `ruta_sav` — TEXT, nullable (ruta al `.sav`; solo encuestas, desde `estandarizado`)
- `ruta_texto_limpio` — TEXT, nullable (ruta al texto limpio en `storage/data/`)
- `estado` — VARCHAR(50), CHECK con los 5 valores: `recibido`, `limpio`, `estandarizado`, `vectorizado`, `error`
- `visibilidad` — VARCHAR(10), CHECK (`publico` | `privado`), **default `publico`**
- `version` — INTEGER, default 1
- `schema_version` — VARCHAR(10), default '1.0'
- `error_detalle` — TEXT, nullable
- `fecha_procesamiento` — TIMESTAMP, server_default NOW() (se actualiza en cada cambio de estado)
- `creado_en` — TIMESTAMP, server_default NOW() (fecha de creación, nunca cambia)

Relaciones:
- `raw_versions` → lista de `RawData` (cascade delete)
- `permiso` → `PermisoInstrumento` (cascade delete, uno a uno porque solo hay un propietario)
- `logs_limpieza` → lista de `PipelineLimpiezaLog` (cascade delete)

> **Sin `metadatos_borrador`:** los metadatos Dublin Core son obligatorios al cargar y se persisten directamente en el JSON canónico. No hay fase de borrador.

#### `RawData`

Mapea `tt_rag.raw_data`. Sin cambios estructurales, pero el modelo debe reflejar que la unicidad de `hash_md5` es por `(hash_md5, usuario_id)` y no global.

Columnas:
- `raw_data_id` — PK
- `instrumento_id` — FK → instrumento_procesado (cascade delete)
- `usuario_id` — FK → usuarios
- `subido` — TIMESTAMP, server_default NOW()
- `tipo_de_instrumento` — VARCHAR(30), obligatorio
- `raw_archivo` — TEXT, obligatorio (ruta relativa al archivo en `storage/raw/`)
- `nombre_original` — TEXT, obligatorio
- `tipo_mime` — VARCHAR(100), nullable
- `tamano_bytes` — BIGINT, obligatorio
- `hash_md5` — VARCHAR(32), nullable

#### `PermisoInstrumento`

Tabla nueva. Registra quién es el propietario de cada instrumento.

**Diseño simplificado:** Solo el rol `propietario` existe. La visibilidad del instrumento (público/privado) cubre el control de lectura; esta tabla cubre el control de escritura.

Columnas:
- `permiso_id` — PK
- `instrumento_id` — FK → instrumento_procesado (cascade delete)
- `usuario_id` — FK → usuarios (cascade delete)
- `rol` — VARCHAR(20), CHECK solo permite `'propietario'`
- `otorgado_en` — TIMESTAMP, server_default NOW()
- UNIQUE(instrumento_id, usuario_id)

#### `PipelineLimpiezaLog`

Tabla nueva. Trazabilidad y lock optimista del pipeline de limpieza.

Columnas:
- `log_id` — PK
- `instrumento_id` — FK → instrumento_procesado (cascade delete)
- `iniciado_en` — TIMESTAMP, server_default NOW()
- `finalizado_en` — TIMESTAMP, nullable
- `resultado` — VARCHAR(20), CHECK (`en_proceso` | `exitoso` | `error`)
- `extractor_usado` — VARCHAR(50), nullable
- `modelo_llm` — VARCHAR(100), nullable
- `prompt_version` — VARCHAR(20), nullable
- `tokens_entrada` — INTEGER, nullable
- `tokens_salida` — INTEGER, nullable
- `latencia_ms` — INTEGER, nullable
- `error_mensaje` — TEXT, nullable

#### `Usuario`

Modelo de **solo lectura** para este módulo. La gestión de usuarios es responsabilidad del módulo de autenticación.

Columnas mínimas:
- `usuario_id` — PK
- `usuario` — VARCHAR(50)
- `password_hash` — VARCHAR(255)
- `creado_en` — TIMESTAMP

---

## 3. `schemas.py` — Schemas Pydantic

**Ubicación:** `backend/cargar_instru/schemas.py`

**Qué cambia:** Archivo vacío → schemas completos de entrada y salida.

**Por qué:** Pydantic valida los datos antes de que lleguen a los services, garantiza serialización correcta y genera la documentación automática en Swagger.

**Problema que resuelve:** Sin schemas todo sería `dict` sin tipado ni validación.

### Tipos base (Literals)

```
TipoInstrumento = "encuesta" | "entrevista" | "prueba_estandarizada"
EstadoPipeline  = "recibido" | "limpio" | "estandarizado" | "vectorizado" | "error"
Visibilidad     = "publico" | "privado"
```

> Sin `"catalogado"` en `EstadoPipeline`. Sin `RolPermiso` como tipo público — el único rol es `propietario` y es interno al sistema.

### Schemas de entrada (request bodies)

#### `InstrumentoCreate`

Para `POST /instrumentos`. Contiene el archivo (como `UploadFile` en el router, no en el schema), los datos básicos y los 13 metadatos Dublin Core obligatorios. Es el schema central de la carga.

Campos de datos básicos:
- `nombre: str` — min_length=1, max_length=255
- `tipo_instrumento: TipoInstrumento`
- `visibilidad: Visibilidad` — **default `"publico"`**

Los 13 campos Dublin Core (todos `str`, salvo `dc_subject` que es `list[str]`):
- `dc_title: str` — obligatorio, min_length=1
- `dc_creator: str` — obligatorio
- `dc_subject: list[str]` — obligatorio, min_length=1 (al menos un elemento)
- `dc_description: str` — obligatorio
- `dc_publisher: str` — obligatorio
- `dc_contributor: str` — obligatorio
- `dc_date: str` — obligatorio (ej. "2023", "2023-1", "2023-08")
- `dc_type: str` — obligatorio (coincide con `tipo_instrumento`)
- `dc_format: str` — obligatorio (ej. "PDF", "DOCX")
- `dc_identifier: str` — obligatorio (ej. "IND-ENC-042")
- `dc_language: str` — obligatorio (ej. "es", "en")
- `dc_coverage: str` — obligatorio
- `dc_rights: str` — obligatorio

Campos Dublin Core opcionales (pueden enviarse en el mismo request o actualizarse después):
- `dc_source: str | None` — default None
- `dc_relation: str | None` — default None

**Nota de diseño:** Este schema se recibe vía `multipart/form-data`. Los campos Dublin Core se envían como campos de texto del formulario, no como JSON anidado. Pydantic los valida después de que FastAPI los extrae del formulario.

#### `MetadatosEspecificoEncuesta`

Para el bloque `especifico` de encuestas. Opcional en la carga inicial.
- `n_items_total: int | None`
- `escala_respuesta: str | None`
- `metodologia_aplicacion: str | None`
- `tasa_respuesta: float | None`
- `dimensiones: list[dict] = []`
- `limitaciones: list[str] = []`

#### `MetadatosEspecificoEntrevista`

- `tipo_entrevista: str | None`
- `n_preguntas_guia: int | None`
- `duracion_estimada: str | None`
- `guion_tematico: list[dict] = []`
- `perfil_entrevistados: str | None`
- `tecnica_analisis: str | None`
- `limitaciones: list[str] = []`

#### `MetadatosEspecificoPrueba`

- `n_reactivos_total: int | None`
- `areas_competencia: list[dict] = []`
- `escala_calificacion: str | None`
- `normas_referencia: str | None`
- `poblacion_normativa: str | None`
- `coeficiente_confiabilidad: float | None`
- `validez: str | None`
- `limitaciones: list[str] = []`

#### `MetadatosUpdate`

Para `PATCH /instrumentos/{id}/metadatos`. Permite actualizar los metadatos después de la carga. Todos los campos son opcionales — solo se actualizan los enviados.

Campos Dublin Core actualizables (todos `str | None`):
- `dc_title`, `dc_creator`, `dc_subject`, `dc_description`, `dc_publisher`
- `dc_contributor`, `dc_date`, `dc_type`, `dc_format`, `dc_identifier`
- `dc_language`, `dc_coverage`, `dc_rights`, `dc_source`, `dc_relation`

Campos adicionales:
- `especifico: MetadatosEspecificoEncuesta | MetadatosEspecificoEntrevista | MetadatosEspecificoPrueba | None`
- `objetivo: str | None` — campo de contexto no cubierto por Dublin Core
- `periodo_fin: str | None` — complemento temporal no cubierto por Dublin Core

#### `VisibilidadUpdate`

Para `PATCH /instrumentos/{id}/visibilidad`.
- `visibilidad: Visibilidad`

### Schemas de salida (response bodies)

#### `CargaArchivoResponse`

Respuesta de `POST /instrumentos` y `POST /instrumentos/{id}/versiones`.
- `instrumento_id: int`
- `version: int`
- `estado: EstadoPipeline` — siempre `"recibido"` al crear
- `visibilidad: Visibilidad`
- `mensaje: str`

#### `InstrumentoResumen`

Para listados. No incluye metadatos semánticos ni rutas de disco.
- `instrumento_id: int`
- `nombre: str`
- `tipo_instrumento: TipoInstrumento`
- `estado: EstadoPipeline`
- `visibilidad: Visibilidad`
- `version: int`
- `creado_en: datetime`
- `propietario: str | None` — nombre de usuario del propietario

#### `InstrumentoDetalle`

Para el endpoint de detalle. Extiende `InstrumentoResumen`.
- Hereda todos los campos de `InstrumentoResumen`
- `ruta_json: str | None` — None si estado es `recibido` o `limpio` (JSON no existe aún)
- `ruta_sav: str | None` — None si no existe o el tipo no es encuesta
- `schema_version: str | None`
- `fecha_procesamiento: datetime`
- `metadatos_canonicos: dict | None` — leído del JSON en disco; None si estado es `recibido` o `limpio`
- `error_detalle: str | None` — mensaje amigable; solo cuando estado = `error`. No se expone información técnica del pipeline.

> La tabla `pipeline_limpieza_log` no alimenta ningún campo de este schema.

#### `VersionInfo`

Para el historial de versiones.
- `raw_data_id: int`
- `nombre_original: str`
- `tipo_mime: str | None`
- `tamano_bytes: int`
- `subido: datetime`
- `numero_version: int`

#### `FiltrosInstrumento`

Parámetros de query para `GET /instrumentos`. No es un body — se declara con `Query(...)` en el router.
- `q: str | None` — búsqueda de texto libre en nombre
- `tipo_instrumento: TipoInstrumento | None`
- `propietario: str | None` — nombre de usuario
- `visibilidad: Visibilidad | None`
- `fecha_desde: date | None` — filtra `creado_en >= fecha_desde`
- `fecha_hasta: date | None` — filtra `creado_en <= fecha_hasta`
- `solo_propios: bool` — default `False`
- `skip: int` — default 0, ge=0
- `limit: int` — default 20, ge=1, le=100

> Sin campo `estado` en los filtros. El estado es información operativa del pipeline, no un criterio de búsqueda para los investigadores.

---

## 4. `services.py` — Lógica de negocio

**Ubicación:** `backend/cargar_instru/services.py`

**Qué cambia:** Archivo vacío → services completos con la lógica del módulo.

**Por qué:** La lógica en los routers es imposible de testear y de mantener.

**Problema que resuelve:** Separación clara entre coordinación HTTP (routers) y lógica de negocio (services).

### `InstrumentoService`

Orquesta el ciclo de vida del instrumento desde la perspectiva del usuario.

| Método | Descripción | Observaciones de diseño |
|---|---|---|
| `cargar_instrumento(db, usuario_id, nombre, tipo, visibilidad, dc_fields, archivo_bytes, nombre_original, tipo_mime)` | Crea el registro completo del instrumento con metadatos DC, guarda el archivo crudo. | Valida los 13 campos DC. Calcula hash. Verifica duplicado. INSERT instrumento_procesado con `estado='recibido'` y `visibilidad` recibida (default `publico`). INSERT raw_data. INSERT permiso_instrumento (rol=`propietario`). No crea JSON. |
| `actualizar_metadatos(db, instrumento_id, usuario_id, metadatos_update)` | Actualiza metadatos DC y/o específicos del instrumento. | Verifica propiedad. Si el JSON existe (estado != `recibido`): actualiza el JSON en disco. Si estado = `vectorizado` o `estandarizado`: resetea a `limpio`. |
| `obtener_instrumento(db, instrumento_id, usuario_id)` | Devuelve el detalle del instrumento. | Verifica acceso (público o propietario). Lee el JSON del disco si existe y lo adjunta. |
| `listar_instrumentos(db, usuario_id, filtros)` | Lista instrumentos accesibles con filtros. | Query: `visibilidad='publico' OR usuario_id=propietario`. Aplica filtros de texto, tipo, propietario, rango de fechas. No lee JSONs del disco. |
| `obtener_ruta_descarga(db, instrumento_id, usuario_id)` | Devuelve (ruta_absoluta, nombre_original) del archivo más reciente. | Verifica acceso. |
| `obtener_ruta_json(db, instrumento_id, usuario_id)` | Devuelve la ruta del JSON canónico. | Verifica acceso. Lanza 404 si `ruta_json` es null (instrumento aún en `recibido`). |
| `obtener_ruta_sav(db, instrumento_id, usuario_id)` | Devuelve la ruta del `.sav`. | Verifica acceso. Lanza 404 si no existe. Lanza 422 si el tipo no es `encuesta`. |
| `eliminar_instrumento(db, instrumento_id, usuario_id)` | Elimina el instrumento y todos sus artefactos. | Verifica propiedad. Elimina archivos del disco. DELETE en cascada desde PostgreSQL. |
| `cargar_nueva_version(db, instrumento_id, usuario_id, archivo_bytes, nombre_original, tipo_mime)` | Sube nueva versión del archivo. | Verifica propiedad. Verifica que el hash sea distinto. INSERT raw_data. Incrementa `version`. Elimina JSON del disco. Resetea `estado='recibido'`. |
| `listar_versiones(db, instrumento_id, usuario_id)` | Lista el historial de versiones del archivo. | Verifica acceso. Ordena por `raw_data_id`. |
| `cambiar_visibilidad(db, instrumento_id, usuario_id, visibilidad)` | Actualiza `visibilidad` en PostgreSQL. | Verifica propiedad. |

### `ArchivoService`

Operaciones de disco para archivos físicos.

| Método | Descripción |
|---|---|
| `guardar_archivo(contenido: bytes, directorio: Path, nombre_unico: str) → Path` | Escribe en disco. |
| `calcular_hash_md5(contenido: bytes) → str` | Hex digest del MD5. |
| `generar_nombre_unico(instrumento_id: int, extension: str) → str` | Genera `{id}_{timestamp}_{uuid8}{ext}`. |
| `eliminar_archivo(ruta: Path) → None` | Silencioso si no existe. |
| `leer_archivo(ruta: Path) → bytes` | Lanza error si no existe. |

### `JsonCanonicoService`

Gestiona el JSON canónico en disco. Lo usan tanto el módulo de gestión (para actualizaciones del usuario) como el pipeline de limpieza (para creación).

| Método | Descripción |
|---|---|
| `crear_json(instrumento_id, tipo, dc_fields, especifico, bloque_limpieza) → Path` | Crea el JSON canónico completo. Deriva el bloque `contexto` a partir de `dc_fields`. Solo se llama una vez por ciclo de vida (desde el pipeline de limpieza). |
| `leer_json(instrumento_id) → dict | None` | Deserializa el JSON. Devuelve None si no existe. |
| `actualizar_bloques(instrumento_id, metadatos_update: MetadatosUpdate) → Path` | Merge parcial: reescribe solo los bloques enviados. Nunca toca `limpieza`, `kpis_inferidos`, `unidades_semanticas`. |
| `eliminar_json(instrumento_id) → None` | Elimina el archivo del disco. Se llama al recibir nueva versión. |
| `exportar_metadatos_para_chroma(instrumento_id) → dict` | Extrae los campos que van como metadatos de filtrado en ChromaDB. |

Toda escritura al JSON es atómica: write-to-temp → `os.replace()`. Previene JSON corruptos ante fallos.

### `PermisoService`

Gestión simplificada del propietario.

| Método | Descripción |
|---|---|
| `crear_permiso_propietario(db, instrumento_id, usuario_id) → PermisoInstrumento` | Se llama automáticamente al crear el instrumento. |
| `es_propietario(db, instrumento_id, usuario_id) → bool` | Verifica si el usuario es el propietario. |
| `puede_acceder(db, instrumento, usuario_id) → bool` | True si el instrumento es público OR si el usuario es su propietario. |

> El método `otorgar_permiso` y `revocar_permiso` del diseño anterior se eliminan. No existen otros roles.

---

## 5. `routers_cargar_instru.py` — Endpoints FastAPI

**Qué cambia:** Stub con un endpoint → router completo.

**Prefijo base:** `/route_instru` (ya definido en `main.py`, no cambiar)

### Tabla de endpoints

| Método | Ruta | Handler | Descripción |
|---|---|---|---|
| POST | `/instrumentos` | `cargar_instrumento` | Cargar nuevo instrumento con metadatos DC obligatorios |
| GET | `/instrumentos` | `listar_instrumentos` | Listar instrumentos accesibles (con filtros) |
| GET | `/instrumentos/propios` | `listar_propios` | Listar solo los del investigador autenticado |
| GET | `/instrumentos/{id}` | `obtener_instrumento` | Detalle del instrumento |
| PATCH | `/instrumentos/{id}/metadatos` | `actualizar_metadatos` | Editar metadatos DC y/o específicos |
| PATCH | `/instrumentos/{id}/visibilidad` | `cambiar_visibilidad` | Cambiar acceso público/privado |
| GET | `/instrumentos/{id}/descargar` | `descargar_archivo` | Descargar archivo original |
| GET | `/instrumentos/{id}/json` | `descargar_json` | Descargar JSON canónico |
| GET | `/instrumentos/{id}/sav` | `descargar_sav` | Descargar `.sav` (solo encuestas desde `estandarizado`) |
| DELETE | `/instrumentos/{id}` | `eliminar_instrumento` | Eliminar instrumento |
| POST | `/instrumentos/{id}/versiones` | `nueva_version` | Subir nueva versión del archivo |
| GET | `/instrumentos/{id}/versiones` | `listar_versiones` | Historial de versiones |

> **Eliminados respecto al diseño anterior:** `/catalogar`, `/permisos` (GET, POST, DELETE). No existen en este diseño.

### Decisiones de diseño

**Carga de archivos:** `multipart/form-data`. El archivo como `UploadFile`, los 13 campos DC como `Form(...)`. FastAPI los extrae individualmente del formulario y Pydantic los valida.

**Validación de los 13 campos DC en la carga:** La validación ocurre en el endpoint antes de cualquier operación de disco o base de datos. Si falta algún campo, se devuelve `422` con la lista de campos faltantes. No se guarda nada si la validación falla.

**Descarga de artefactos:** Los tres endpoints de descarga devuelven `FileResponse` con `Content-Disposition: attachment`. No leen el archivo en memoria — `FileResponse` lo transmite en streaming.

**Endpoint `/sav`:** Además de verificar que el archivo existe, verifica que el instrumento es de tipo `encuesta`. Si el tipo es `entrevista` o `prueba_estandarizada`, devuelve `422` con el mensaje "Este instrumento no genera archivo .sav". Si es encuesta pero no está en estado `estandarizado` o superior, devuelve `404` "El archivo .sav no está disponible aún".

**Listados sin conteo total:** `GET /instrumentos` devuelve una lista plana con paginación por `skip`/`limit`. No devuelve conteo total en esta versión.

### Códigos de respuesta

| Situación | Código |
|---|---|
| Creación exitosa | 201 |
| Lectura / actualización exitosa | 200 |
| Eliminación exitosa | 204 |
| No autenticado | 401 |
| Sin permiso de escritura (no es propietario) | 403 |
| Instrumento no encontrado | 404 |
| Artefacto no generado aún (JSON en `recibido`, SAV no listo) | 404 con mensaje descriptivo |
| Archivo duplicado (mismo hash del mismo usuario) | 409 |
| Archivo idéntico al subir nueva versión | 409 |
| Campos DC faltantes en la carga | 422 con lista de campos |
| Tipo no soporta `.sav` (no es encuesta) | 422 con mensaje descriptivo |
| Error de validación Pydantic | 422 |

---

## 6. `dependencies.py` — Dependencias FastAPI

**Ubicación:** `backend/cargar_instru/dependencies.py`

**Qué cambia:** Archivo nuevo (no existe actualmente).

**Por qué:** Centraliza autenticación y autorización en un lugar reutilizable, evitando duplicación y garantizando comportamiento consistente en todos los endpoints.

**Problema que resuelve:** Sin este archivo, la lógica de autenticación se repetiría en cada handler.

### Dependencias a definir

#### `get_current_user`

**Firma conceptual:** `(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) → Usuario`

Decodifica el JWT, extrae el `usuario_id`, consulta el usuario en la BD. Lanza `401` si el token es inválido, expirado o el usuario no existe.

Usada en: todos los endpoints.

#### `puede_acceder_o_403`

**Firma conceptual:** `(instrumento_id: int, usuario_actual: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) → InstrumentoProcesado`

Obtiene el instrumento (lanza 404 si no existe). Verifica que sea público OR que el usuario sea su propietario. Lanza 403 si ninguna condición se cumple. Devuelve el instrumento listo para usar en el handler.

Usada en: GET detalle, GET descargar, GET json, GET sav, GET versiones.

#### `verificar_propietario`

**Firma conceptual:** `(instrumento: InstrumentoProcesado = Depends(puede_acceder_o_403), usuario_actual: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) → InstrumentoProcesado`

Verifica que el usuario sea el propietario del instrumento (consulta `permiso_instrumento`). Lanza 403 si no lo es. Devuelve el instrumento.

Usada en: PATCH metadatos, PATCH visibilidad, POST versiones, DELETE.

> Reemplaza al patrón de fábrica `verificar_rol("propietario")` del diseño anterior. Como solo existe un rol, una función directa es más clara.

#### `get_instrumento_o_404`

**Firma conceptual:** `(instrumento_id: int, db: Session = Depends(get_db)) → InstrumentoProcesado`

Obtiene el instrumento por ID. Lanza 404 si no existe. No verifica permisos.

Usada en: como base interna por las otras dependencias.

---

## 7. Relación entre los archivos

```
routers_cargar_instru.py
    │  inyecta
    ├─► dependencies.py ──► models.py
    │
    │  llama a
    ├─► services.py ──► models.py
    │               └─► schemas.py
    │
    │  valida entrada / serializa salida
    └─► schemas.py
```

Los modelos no importan nada del módulo. Los schemas solo importan tipos Python. Los services importan modelos y schemas. Los routers importan services, schemas y dependencies.

---

## 8. Nota sobre `modules.py`

El archivo `modules.py` actualmente vacío en el repositorio no tiene rol en esta arquitectura. Se recomienda:

- **Opción preferida:** renombrarlo a `models.py` o eliminarlo y crear `models.py` nuevo. Sigue la convención estándar de FastAPI/SQLAlchemy.
- **Alternativa:** mantenerlo como archivo de constantes del dominio (ej. los nombres de los 13 campos DC obligatorios como lista, las estrategias de extracción por MIME).

---

## 9. Qué no va en este módulo

| Responsabilidad | Dónde debe ir |
|---|---|
| Login / emisión de JWT | Módulo de autenticación (separado) |
| Cambio de estado del pipeline | Solo el sistema (token de servicio o proceso interno) |
| Ejecución del pipeline de limpieza | `pipeline_limpieza/orchestrator.py` |
| Inferencia de KPIs | Pipeline de estandarización (módulo futuro) |
| Generación de embeddings | Pipeline de vectorización (módulo futuro) |
| Consulta RAG | Módulo RAG (módulo futuro) |
