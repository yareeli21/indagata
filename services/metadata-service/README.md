# metadata-service (puerto 8003)

Garantiza que **todo instrumento tenga metadatos completos y aprobados por su
autor** antes de entrar al RAG.

1. **Dublin Core obligatorio** — los 13 campos de `metadatos_dc` (solo
   `dc_relation` es opcional).
2. **Metadatos del tipo** — completa los faltantes en
   `metadatos_enriquecidos_encuestas`, `_entrevistas` o `_pruebas`.
3. **Aprobación del autor** — al aprobar se genera el JSON estandarizado, el
   storage-service lo guarda, se persisten las tablas y se pide la ingesta al
   índice vectorial (colección `instrumentos`).

## Flujo

```
upload (instrument-service) ─► GET  /api/metadata/{id}/propuesta     Dublin Core propuesto
                               GET  /api/enrichment/{id}/propuesta   metadatos del tipo propuestos
                               POST /api/metadata/{id}/vista-previa  JSON estandarizado (no guarda)
                               POST /api/metadata/{id}/aprobar       autor aprueba → BD + JSON + RAG
analysis-service (KPIs) ─────► POST /api/metadata/{id}/finalizar     JSON con los KPIs aceptados
```

`{id}` es siempre `id_crudo` (PK de `raw_data`), el id que usa el frontend.

### ¿De dónde salen las propuestas?

El servicio lee el instrumento **a través del storage-service** (archivo limpio
si existe, si no el crudo) — nunca toca el disco — y `services/analizador.py`
extrae:

| Tipo | Se infiere |
|---|---|
| Encuesta (CSV/XLSX) | reactivos y su tipo (Likert, escala, opción múltiple, abierta), opciones, estadísticas por reactivo, nº de respondentes, duplicados y vacíos, dimensiones (encabezados `Bloque [ítem]`), carreras, palabras clave |
| Entrevista (PDF/DOCX/TXT) | preguntas (turnos del entrevistador, numeradas, con `?`), objetivo, metodología, institución |
| Prueba (PDF/DOCX/TXT) | reactivos y opciones, reactivos por sección, unidad de aprendizaje, ciclo escolar, grado, grupo, tipo de prueba, niveles de Bloom, nivel educativo |
| JSON v1 (demo) | su propio Dublin Core y metadatos |

Los campos interpretativos que quedan vacíos (objetivo, constructo, población…)
se piden al LLM local (Ollama) si `METADATA_USAR_LLM=true` o `?usar_llm=true`.
Si Ollama no responde, el autor los captura: el LLM nunca es requisito.
Cada valor propuesto indica su `origen`: `automatico`, `archivo`, `inferido`,
`llm` o `aprobado`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/metadata` | Listado paginado |
| GET | `/api/metadata/{id}/propuesta` | Dublin Core propuesto (o el aprobado) |
| POST | `/api/metadata/{id}/vista-previa` | JSON estandarizado + errores de validación |
| POST | `/api/metadata/{id}/aprobar` | Aprobación del autor (persistencia + ingesta) |
| POST | `/api/metadata/{id}/finalizar` | Añade al JSON los KPIs aceptados (`kpi_inferido`) |
| GET | `/api/metadata/{id}` | Metadatos registrados |
| DELETE | `/api/metadata/{id}` | Retira la aprobación (el instrumento sale del RAG) |
| GET | `/api/enrichment/campos/{tipo}` | Definición de campos de un tipo |
| GET | `/api/enrichment/{id}/propuesta` | Metadatos del tipo propuestos (o aprobados) |
| GET | `/api/enrichment/{id}` | Metadatos del tipo aprobados |

Todos exigen JWT (rol investigador o administrador). Proponer, aprobar,
finalizar y retirar: solo el autor del instrumento o un administrador.

## Estructura

```
metadata-service/
├── main.py
├── models.py                 DTOs HTTP (los ORM viven en shared/models)
├── dependencies.py           JWT
├── routers/  metadata.py · enrichment.py · health.py
└── services/
    ├── dc_manager.py         Dublin Core: propuesta, validación, upsert
    ├── enrichment_engine.py  metadatos del tipo: propuesta, tipado, upsert
    ├── campos.py             catálogo de campos (1:1 con 01_schema.sql)
    ├── analizador.py         lectura y análisis del instrumento
    ├── propuestas.py         heurísticas + LLM
    ├── aprobacion.py         aprobar / vista previa / finalizar / retirar
    ├── json_estandarizado.py JSON que se ingiere al RAG
    ├── storage_client.py     cliente del storage-service (token de servicio)
    └── llm_client.py         cliente de Ollama con degradación grácil
```

## Pruebas

```sh
cd services/metadata-service
python -m pytest tests
```

Usan SQLite en memoria y dobles del storage-service y de Ollama.

## Variables de entorno

`POSTGRES_*`, `SECRET_KEY` (la misma del api-gateway), `STORAGE_SERVICE_URL`,
`OLLAMA_HOST`, `OLLAMA_MODEL`, `METADATA_USAR_LLM` (default `true`),
`METADATA_LLM_TIMEOUT` (segundos, default 60), `APP_NAME`.
