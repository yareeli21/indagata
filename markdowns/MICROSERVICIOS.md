# Microservicios de Indagata: qué hace cada uno

Estado actual de la rama `pruebas`. Indagata gestiona y consulta instrumentos de investigación
educativa (encuestas, entrevistas y pruebas estandarizadas). Una investigadora sube un instrumento y
lo limpia de forma asistida. Después aprueba sus metadatos y acepta los KPIs sugeridos. Al final, el
instrumento queda disponible para el catálogo, los tableros de KPIs y el chat RAG.

El sistema tiene **9 servicios FastAPI** (Python), un **frontend** (React) y la infraestructura
(PostgreSQL, ChromaDB, Ollama y Redis). Todos los servicios comparten una base de datos (esquema
`tt_rag`) y un paquete de Python común, `shared/`.

> Para levantar la aplicación, consulta [LEVANTAR_LA_APP.md](LEVANTAR_LA_APP.md).

---

## 1. Vista general

```
                 Navegador (localhost:3000)
                         │
            ┌────────────┴─────────────┐
            ▼                          ▼
     api-gateway :8006          analysis-service :8002   (el frontend lo llama directo)
            │
  ┌─────────┼──────────┬──────────────┬──────────────┬───────────────┐
  ▼         ▼          ▼              ▼              ▼               ▼
instrument cleaning  metadata     knowledge     visualization    storage
  :8001     :8007     :8003         :8009          :8005          :8004
     │         │         │             │              │               │
     └─────────┴─────────┴──────┬──────┴──────────────┴───────────────┘
                                ▼
          PostgreSQL (tt_rag) · ChromaDB · Ollama (LLM local) · Redis
```

- **Todo pasa por el gateway**, salvo analysis-service, al que el frontend llama de forma directa.
- **storage-service es el único que guarda archivos.** Los demás servicios le piden leer o escribir
  con un *token de servicio*.
- **Se usa un solo JWT para todo.** El gateway lo emite y cada servicio lo valida con la misma
  `SECRET_KEY`.
- **El identificador común** de un instrumento en todos los servicios es `id_crudo`, la llave
  primaria de `raw_data`.

### Pasos del asistente «Subir instrumento» y servicio que atiende cada uno

| # | Paso | Servicio | Qué ocurre |
|---|---|---|---|
| 1 | Archivo | instrument-service → storage-service | Se sube el archivo respondido, el instrumento original y, en pruebas, la clave (opcional). Se detecta el formato y se guarda el crudo sin cambios. |
| 2 | Limpieza | cleaning-service | Fase automática, luego fase asistida (la investigadora decide) y después la confirmación. Genera el CSV limpio, el reporte y la estadística. |
| 3 | Dublin Core | metadata-service | Propone los 13 campos Dublin Core a partir de la limpieza confirmada. |
| 4 | Metadatos del tipo | metadata-service | Campos propios de cada tipo de instrumento (encuesta, entrevista o prueba). |
| 5 | Aprobar metadatos | metadata-service + knowledge-service | Se aprueban los metadatos y se genera y aprueba el **perfil semántico**. |
| 6 | KPIs sugeridos | analysis-service | KPIs sugeridos por similitud con el perfil, con su evidencia y justificación. La investigadora los acepta o los rechaza. |
| 7 | Guardar | knowledge-service + metadata-service | Se genera y publica el **documento final** y se guarda el instrumento con sus KPIs. |

---

## 2. Servicios

### 2.1 api-gateway (puerto 8006 → 8000)
**Es la puerta de entrada del frontend.**
- **Autenticación.** `POST /auth/login`, `GET /auth/me` y `POST /auth/register` (este último solo
  para administradores). Emite el JWT, que dura 60 minutos.
- **Proxy.** Reenvía la ruta tal cual, según su prefijo, sin renombrarla ni envolver la respuesta:

| Prefijo | Servicio destino |
|---|---|
| `/instrumentos/*` | instrument-service |
| `/limpieza/*` | cleaning-service |
| `/api/metadata/*`, `/api/enrichment/*` | metadata-service |
| `/conocimiento/*` | knowledge-service |
| `/visualizacion/*`, `/rag/*` | visualization-service (`/rag/chat` responde por SSE) |
| `/almacenamiento/*` | storage-service (solo administradores) |

- **Código:** `services/api-gateway/main.py` y `proxy/proxy.py`. Cada prefijo registra la ruta base y
  la ruta `{path:path}`, para evitar la redirección 307 de FastAPI.

### 2.2 instrument-service (8001)
**Recibe los archivos (paso 1).**
- **Formatos:** detecta el tipo de archivo (CSV, Excel, SPSS, TXT, DOCX o PDF) y lo convierte a una
  forma tabular o de documento. Los lectores viven en `shared/parsing/`, porque cleaning-service
  también los usa.
- **Guardado:** entrega los bytes originales a storage-service y registra el instrumento en `raw_data`.
- **Rutas:**
  - `POST /instrumentos/upload` recibe el archivo respondido, el original y la clave.
  - `GET /instrumentos` lista los instrumentos.
  - `GET /instrumentos/{id}` devuelve uno.
  - `DELETE /instrumentos/{id}` lo elimina.
  - `GET /instrumentos/kpis/catalogo` devuelve el catálogo de KPIs.

### 2.3 cleaning-service (8007), nuevo
**Limpieza asistida (paso 2).** No modifica el archivo crudo: cada vez que se repite la limpieza se
crea una versión nueva.
- **Fase automática.** Un motor por tipo de instrumento (`services/motores/`). Los motores son
  funciones puras, sin red ni base de datos:
  - **Encuestas:** detecta el tipo de cada columna, homologa vacíos y «No sé», detecta ítems
    invertidos, columnas ajenas y respuestas en línea recta, y aplica escalas Likert.
  - **Pruebas estandarizadas:** detecta el tipo de reactivo (opción múltiple, verdadero/falso,
    escala, Sí/No o numérico), valida respuestas y encuentra duplicados. Si no hay clave, **propone
    una** y la investigadora debe confirmarla.
  - **Entrevistas:** limpia el ruido de la transcripción, identifica hablantes (P1…/R1 se agrupan en
    P y R), separa los bloques de cada entrevistado (`RESPONDENTE: …`) y sugiere el rol de cada hablante.
- **Fase asistida.** Presenta *hallazgos* con opciones y una sugerencia. Algunos son obligatorios.
- **Confirmación.** Escribe el CSV limpio (separado por `;`, UTF-8 con BOM) en storage-service como
  artefacto `clean` y el `reporte_limpieza` en `tt_rag.limpieza_ejecucion`. También actualiza
  `instrumento_procesado.ruta_de_archivo_limpio`.
- **Estadística por tipo** (`services/motores/estadistica.py`):
  - **Encuesta:** descriptivos y α de Cronbach por bloque.
  - **Prueba:** KR-20, dificultad, discriminación y puntajes.
  - **Entrevista:** respuestas por pregunta, por entrevistado y por rol.

  Además genera un resumen en lenguaje natural («En pocas palabras», `resumen.py`).
- **Rutas** (todas con el prefijo `/limpieza/{id_crudo}/ejecuciones`):
  - `POST` (vacío) ejecuta la fase automática.
  - `GET /actual` devuelve la versión vigente.
  - `GET /{version}` devuelve una versión concreta.
  - `PATCH /{version}/decisiones` guarda decisiones parciales.
  - `POST /{version}/confirmar` confirma la limpieza.
  - `GET /{version}/vista-final` devuelve la vista final.
- **Reglas editables sin tocar código:** `config/limpieza.yaml` y `shared/config/escalas_likert.yaml`.
- **Documentación:** `services/cleaning-service/README.md` y `markdowns/METRICAS_LIMPIEZA.md`.

### 2.4 metadata-service (8003)
**Metadatos (pasos 3, 4, 5 y 7).**
- **Propuesta.** `GET /api/metadata/{id}/propuesta` propone los 13 campos Dublin Core con
  heurísticas. Parte de la **última limpieza confirmada** (`services/desde_limpieza.py`). Si el
  instrumento es nuevo y no tiene una limpieza confirmada, responde 409; la variable
  `METADATA_EXIGIR_LIMPIEZA` controla esa exigencia. Si `METADATA_USAR_LLM` está activa, Ollama
  completa los campos interpretativos. Cuando Ollama no responde, el servicio sigue funcionando sin él.
- **Metadatos del tipo.** `GET /api/enrichment/campos/{tipo}` y `GET /api/enrichment/{id}`.
- **Aprobación.**
  - `POST /api/metadata/{id}/vista-previa` muestra cómo quedaría sin guardar nada.
  - `POST /api/metadata/{id}/aprobar` (autora o administrador) guarda `metadatos_dc` y
    `metadatos_enriquecidos_*`, guarda el JSON técnico estandarizado en storage-service y dispara la
    ingesta al RAG.
- **Finalizar.** `POST /api/metadata/{id}/finalizar` agrega los KPIs aceptados al JSON.
- **Otras rutas:** `GET /api/metadata` lista, `GET /api/metadata/{id}` consulta y
  `DELETE /api/metadata/{id}` retira la aprobación.

### 2.5 knowledge-service (8009), nuevo
**Perfil semántico y documento final (pasos 5 y 7).** Usa una sola tabla,
`tt_rag.version_conocimiento`, con una fila por versión. Los estados son `perfil_aprobado` →
`kpis_confirmados` → `borrador` → `vigente`. Cuando se publica una versión nueva, la anterior pasa a
`reemplazado`.
- **Perfil semántico.** Describe el instrumento: título, objetivo, temas, población y preguntas por
  sección. No incluye métricas ni respuestas, y es **lo único** que se usa para asociar KPIs. Se
  arma con plantillas deterministas, sin LLM.
  - `POST /conocimiento/{id}/perfil/vista-previa` lo genera sin guardarlo.
  - `POST /conocimiento/{id}/perfil` lo aprueba.
  - `GET /conocimiento/{id}/perfil` lo consulta.
- **Documento final.** Es el JSON pensado para el RAG: las respuestas de cada respondente,
  interpretadas, y la relación entre KPI y preguntas. Hay uno por tipo:
  - **Encuesta:** respondentes con sus respuestas interpretadas.
  - **Prueba:** alumnos con aciertos, puntaje y la dificultad de cada reactivo.
  - **Entrevista** (esquema 2.0): preguntas e intercambios pregunta-respuesta por entrevistado.

  Se valida contra un JSON Schema (`esquemas/`), se eliminan los datos personales y se guarda en
  storage-service como artefacto `documento` con su SHA-256.
  - `POST /conocimiento/{id}/documento` lo genera.
  - `GET /conocimiento/{id}/documento` devuelve la vista.
  - `GET /conocimiento/{id}/documento/json` devuelve el JSON completo.
  - `POST /conocimiento/{id}/documento/{version}/publicar` lo publica.
- **Pendiente:** el documento final todavía **no se ingesta en ChromaDB**. El chat RAG sigue usando el
  JSON técnico que se ingesta al aprobar. La tabla en formato largo `respuesta_interpretada` queda
  para la etapa del RAG.
- **Documentación:** `services/knowledge-service/README.md` y
  `markdowns/JSON_FINALES_RAG_Y_ESTADISTICA.md`.

### 2.6 analysis-service (8002)
**KPIs y embeddings (paso 6).** El frontend lo llama directo, no a través del gateway.
- **Modelo de embeddings:** `paraphrase-multilingual-mpnet-base-v2` (768 dimensiones). Se guarda en
  caché en el volumen `hf_cache`. La imagen instala torch solo para CPU.
- **Asociación de KPIs por perfil (flujo actual).** Se generan embeddings del perfil general y de cada
  pregunta, y se comparan con la colección `kpis` de ChromaDB, que este servicio **solo lee**. El
  resultado es un puntaje por KPI, las preguntas que lo sustentan y una justificación breve. Esa
  justificación es la única pieza generada con LLM, y si el LLM falla se usa una plantilla. La
  investigadora puede editarla.
  - `POST /vectorizacion/perfil/propuestas` devuelve los KPIs sugeridos.
  - `POST /vectorizacion/perfil/confirmar` guarda los aceptados y los rechazados.
- **Rutas anteriores y de mantenimiento:**
  - `POST /vectorizacion/propuestas` y `/confirmar` (flujo anterior, por *summary*).
  - `POST /vectorizacion/kpis/reindex`.
  - `GET /vectorizacion/summary/{id}`.
  - `GET /vectorizacion/espacio`.
  - `GET /vectorizacion/kpis/catalogo`.
- **Scripts:**
  - `scripts/seed_kpis.py` carga el catálogo de KPIs desde `infrastructure/postgres/seed/kpis_ampliados.csv`.
  - `scripts/comparar_kpis.py` compara el método nuevo con el anterior.

### 2.7 storage-service (8004, solo interno)
**Es el dueño de todos los archivos** y el **único que escribe** en la colección `instrumentos` de
ChromaDB y en `documento_vectorizado`.
- **Versionado.** Guarda artefactos versionados `<tipo>/<id>/<versión>__<nombre>` con un hash
  SHA-256, que se verifica al descargar. Los tipos son `raw`, `clean`, `json` y `documento`, entre otros.
- **Ingesta al RAG.** Parte el JSON aprobado en *chunks* (`encabezado`, uno por `pregunta` y
  `contenido`), cada uno con metadatos para filtrar, y deja el instrumento con estado `vectorizado`.
- **Rutas de archivos** (prefijo `/almacenamiento`):
  - `POST /json` y `POST /archivo` guardan.
  - `GET /artefactos` lista y `GET /descarga` descarga.
  - `GET /tabla` y `GET /texto` devuelven el contenido.
  - `DELETE /archivo` elimina.
  - `GET /estadisticas` da las estadísticas de almacenamiento.
- **Rutas del índice** (prefijo `/almacenamiento/indice`):
  - `.../instrumentos/{id}` para ingestar, consultar o retirar un instrumento.
  - `GET /colecciones`.
- Los archivos viven en la carpeta `storage/` del repositorio, montada en el contenedor.

### 2.8 visualization-service (8005)
**Consulta.** Solo lee la base de datos y ChromaDB; la única escritura es en `rag_log`.
- **Catálogo:**
  - `GET /visualizacion/catalogo` lista con filtros y facetas.
  - `GET /visualizacion/catalogo/{id}` devuelve la ficha.
  - `GET /visualizacion/investigadores`.
- **Tableros de KPIs:** `GET /visualizacion/kpis/catalogo` y `/kpis/resumen`, y qué preguntas miden
  cada KPI (los chunks `pregunta` más cercanos al vector del KPI).
- **Descargas:** `GET /visualizacion/descargas/{id}`, en formato crudo, JSON o `.sav` (SPSS).
- **Espacio vectorial:** `GET /visualizacion/espacio/mapa`, `/vecinos/{tipo}/{ref}` y `POST /buscar`.
- **Chat RAG:** `POST /rag/chat` (SSE) responde con Ollama a partir de los chunks recuperados.
  `num_ctx` se mantiene pequeño para caber en una GPU de 4 GiB. `POST /rag/index` asegura la ingesta.

### 2.9 frontend (3000), `pixel-perfect-pixel/`
- **Tecnologías:** TanStack Start, Vite, React 19, Tailwind 4 y shadcn/Radix.
- **Acceso a datos:** todo pasa por `src/api/` (`client.ts` con `pedir()`). Nunca llama a
  storage-service directo.
- **Código por funcionalidad** (`src/features/`): upload (el asistente de 7 pasos, la limpieza y el
  conocimiento), instruments, kpis, chat, espacio y otras.
- **Rutas:** `src/routes/`. `routeTree.gen.ts` se genera solo y no se edita a mano.

### 2.10 chroma-viewer (8085)
Visor web de solo lectura de los embeddings de ChromaDB (proyección PCA 2D). Es independiente y no
toca ningún otro servicio.

---

## 3. Piezas compartidas e infraestructura

| Pieza | Qué contiene |
|---|---|
| `shared/db/core/config.py` | Configuración única (`settings`) que se lee del `.env` raíz |
| `shared/db/core/domain_constants.py` | Vocabularios cerrados: tipos de instrumento, estados y decisiones |
| `shared/models/`, `shared/schemas/` | ORM SQLAlchemy y DTO Pydantic, en espejo 1:1 de `01_schema.sql` |
| `shared/auth/` | JWT, contraseñas, roles (`investigador`, `administrador`) y tokens de servicio |
| `shared/parsing/` | Lectores de archivos compartidos por instrument-service y cleaning-service |
| `shared/config/escalas_likert.yaml` | Escalas Likert compartidas por cleaning-service y knowledge-service |
| PostgreSQL (5432) | Esquema `tt_rag`. La fuente de verdad es `infrastructure/postgres/init/01_schema.sql`. Tablas nuevas: `limpieza_ejecucion` y `version_conocimiento`. |
| ChromaDB (8008 → 8000) | Colecciones `kpis`, `summary_instrument` e `instrumentos` |
| Ollama (11434) | LLM local (`llama3.2:3b`): metadatos interpretativos, justificación de KPIs y chat |
| Redis (6379) | Usado por el gateway |

## 4. Pruebas automatizadas

Cada servicio tiene sus pruebas en `services/<servicio>/tests/` (pytest). Usan SQLite en memoria y
versiones simuladas de ChromaDB y de los embeddings, así que no necesitan Docker. Resultados actuales:

| Servicio | Pruebas |
|---|---|
| cleaning-service | 101 |
| knowledge-service | 88 |
| visualization-service | 25 |
| metadata-service | 21 |
| storage-service | 19 |
| analysis-service | 13 |

Cómo ejecutarlas: ver [LEVANTAR_LA_APP.md](LEVANTAR_LA_APP.md#9-opcional-ejecutar-las-pruebas-automatizadas).
