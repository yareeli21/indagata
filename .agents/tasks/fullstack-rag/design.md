# Diseño técnico — Front/Back completo + RAG (rama `pruebas`)

Artefacto de diseño para unir el frontend con el backend, implementar
`storage-service` y `visualization-service` (el servicio RAG), cablear el
`api-gateway`, y de-mockear la capa `src/api/*` del frontend sin tocar la UI.

Todas las rutas de este documento son **relativas al worktree**
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag`. Toda la
interfaz, textos de dominio y mensajes al usuario permanecen en español.

> **Esta es la 3.ª iteración.** La 2.ª cerró los hallazgos de la 1.ª, pero la
> revisión de la 2.ª (`design-review.md` / `design-review.json`) detectó **2 HIGH
> + 3 MEDIUM + 2 NIT**: dos afirmaciones presentadas como "verificadas" eran
> **falsas contra el repo** y una de ellas rompía el entregable central (el RAG).
> Esta iteración las corrige tras **verificar directamente los archivos del
> worktree** (`storage/raw/inst_01.v1.json`, `services/metadata-service/*`,
> `docker-compose.yml`, `delete.py`/`upload.py`, `config.py`, `types/index.ts`).
> Cambios principales de esta tanda:
> 1. **[HIGH 1]** El esquema real del JSON de instrumento SÍ existe en el repo
>    (`storage/raw/inst_XX.v1.json`) y es `instrument.*` / `metadata.dublin_core`
>    / `metadata.survey_specific` / `design_reference.kpi_hints`. Se reescribe el
>    contrato de extracción (§2.3, §4.2) contra ese esquema real, con un test que
>    exige `chunks > 0` sobre `inst_01.v1.json`.
> 2. **[HIGH 2]** `metadata-service` **está implementado** (`main.py` + routers
>    reales en `/api/metadata/*` y `/api/enrichment/*`). Se corrige §5.2 y el
>    supuesto; se decide con base en el estado real (§2.3b, §5.2).
> 3. **[MED 3]** Se fija la correspondencia real `inst_XX ↔ id_crudo` y un paso de
>    **seed** verificable para la demo, más el fallback de `sources.py` a
>    `storage/raw/inst_<n>.v*.json` (§2.8, §4.2).
> 4. **[MED 4]** `GET /instrumentos` y `GET /instrumentos/{id}` usan
>    `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` y el frontend los llama con
>    `{auth:true}` (§6, §8.1), con nota sobre `AUTH_DEV_MODE`.
> 5. **[MED 5]** Se fija el YAML EXACTO del `visualization-service` copiando los
>    envs/`depends_on`/`hf_cache` de `analysis-service` (§7).
> 6. **[NIT 6]** Map campo a campo DTO→`Instrumento` descartando `idProcesado`
>    (§8.1).
> 7. **[NIT 7]** El proxy reenvía el path tal cual (`/instrumentos/*`,
>    `/almacenamiento/*`, `/rag/*`) y se eliminan los ejemplos en inglés (§5.2).
>
> Las respuestas puntuales a cada hallazgo están al final (§12). Las decisiones de
> la 2.ª iteración que la revisión confirmó correctas (id canónico `id_crudo`,
> firma ampliada de `enviarMensaje`, re-tipado de `ModeloLLM`, `query(where=None)`
> aditivo, proxy transparente, localStorage para investigaciones, chunking) se
> mantienen sin cambios.

---

## 1. Visión general

El objetivo demostrable: el investigador selecciona instrumentos para una
investigación, los "junta" (se indexan en un vector store por investigación),
abre el chat y hace preguntas que un LLM local (Ollama `llama3.2:3b`) responde
**fundamentado** en los fragmentos recuperados de esos instrumentos, citando sus
fuentes. Alrededor de ese flujo central se cierra la cadena de artefactos:
`storage-service` como autoridad de archivos/JSON y `api-gateway` como única
puerta HTTP del frontend.

Decisiones transversales que fijan el resto del diseño:

- **Stack bloqueado (no se cambia tras aprobación):** Python 3.11 + FastAPI +
  Pydantic v2 / pydantic-settings para los servicios; `httpx` async para llamadas
  entre servicios y a Ollama; `chromadb` (HttpClient) como vector store;
  `sentence-transformers` (modelo `settings.EMBEDDING_MODEL`, 768-dim,
  `normalize_embeddings=True`) para embeddings; Ollama en `settings.OLLAMA_HOST`
  con `settings.OLLAMA_MODEL`. Frontend: React + TanStack Router + TypeScript con
  el helper `pedir()` de `src/api/client.ts`. Ningún servicio nuevo introduce
  ORM/DB salvo que ya lo tenga disponible por `shared`.
- **Reutilización obligatoria:** `visualization-service` NO reimplementa
  embeddings ni cliente Chroma. Copia el patrón de
  `services/analysis-service/app/vectorization/core/embeddings.py` y
  `.../chroma_client.py`. Como los servicios no comparten código de aplicación
  entre carpetas `services/*` (solo comparten `shared/`), se **duplica** ese par
  de módulos dentro de `visualization-service`. `embeddings.py` se copia 1:1.
  `chroma_client.py` se copia **conservando firmas salvo una extensión aditiva
  documentada**: `query(...)` recibe un parámetro opcional `where: dict | None =
  None` (ver §4.3, resuelve hallazgo 6). Se anota en cada archivo el origen y la
  desviación. (Alternativa considerada: promover a `shared/` — se descarta esta
  tanda porque obligaría a tocar analysis-service; deuda técnica anotada.)
- **El gateway devuelve respuestas transparentes:** hoy `proxy_request` envuelve
  todo en `{status_code, body}`, lo que rompe `pedir()` (espera el JSON de
  dominio directo con el status HTTP real). Se corrige para devolver el cuerpo
  del upstream tal cual con su código de estado (§5.1).
- **`analysis-service` (:8002) se sigue llamando directo** desde el frontend
  (`ANALYSIS_URL`), como ya hace `espacio.ts`. El gateway NO proxea
  `/vectorizacion/*`.

### 1.1 Mapa de flujo

```
Frontend (pixel-perfect-pixel)
  │  pedir(API_URL/...)                    pedir(ANALYSIS_URL/...)  (directo)
  ▼                                         ▼
api-gateway :8000  ──proxy──►  instrument-service :8001   analysis-service :8002
  │                           storage-service :8004
  │                           (metadata-service :8003 → implementado /api/*;
  │                            NO proxeado en esta tanda por alcance, §5.2)
  └──proxy──►  visualization-service :8005  ──►  Chroma (HttpClient)  +  Ollama
                                            ──►  lee ./storage (volumen) / storage-service
```

---

## 2. Contratos de identidad y de artefactos (resuelve la ambigüedad central)

El frontend trabaja con **ids string** (`Instrumento.id`, `FuenteChat.instrumentoId`,
`Investigacion.id`). El instrument-service trabaja con **enteros**: `id_crudo` (PK
de `raw_data`, padre) e `id_instrumento` (PK de `instrumento_procesado`, hija).

### 2.1 Id canónico de instrumento (resuelve hallazgo 2)

**Decisión: `Instrumento.id` del frontend == `str(id_crudo)`.** Se elige
`id_crudo` (no `id_instrumento`) por una razón concreta y verificada: el único
endpoint de borrado existente (`services/instrument-service/app/routers/
delete.py`) es `DELETE /instrumentos/{id_crudo}` y keya por `id_crudo`. Hacer que
el id canónico sea `id_crudo` permite que `eliminarInstrumento(id)` →
`DELETE ${API_URL}/instrumentos/${id}` apunte al registro correcto **sin añadir
endpoints nuevos de borrado**. `raw_data` es además la tabla padre que porta
`tipo_instrumento`, `nombre_archivo`, `id_owner` y `fecha_carga` — justo los
datos base del instrumento.

Consecuencias (consistentes en todo el diseño):

- `GET /instrumentos` y `GET /instrumentos/{id}` devuelven `id = str(id_crudo)`.
  El DTO incluye **además** `id_instrumento` (como `idProcesado`, informativo) por
  si una etapa futura lo necesita, pero el `id` canónico que viaja en
  `Instrumento.id` es `id_crudo`.
- `DELETE /instrumentos/{id}` del gateway reenvía ese `id_crudo` al endpoint real
  existente. No se crea `DELETE /instrumentos/por-instrumento/...`.
- `IndexRequest.instrumentoIds` y `ChatRequest.instrumentoIds` son `str(id_crudo)`.
  El visualization-service los usa como clave para localizar artefactos JSON (§4.2)
  y como valor de metadata `instrumentoId` en Chroma.
- `FuenteChatOut.instrumentoId` = ese mismo `str(id_crudo)`.

### 2.2 `investigacionId`

El frontend genera hoy ids como `res-<timestamp>` en `crearInvestigacion`. Se
mantiene como **clave opaca**: el backend NO valida su estructura, solo la sanea
para nombrar la colección Chroma (`investigacion_<slug>`, §4.3).

### 2.3 Fuente de verdad de los metadatos de dominio (resuelve hallazgo 1)

**Hecho verificado (DB):** `instrumento_procesado` tiene SOLO `id_instrumento`,
`id_crudo`, `ruta_de_archivo_limpio`, `ruta_json`, `estado`,
`fecha_procesamiento`, `fecha_aprobado`. `raw_data` tiene SOLO `id_crudo`,
`id_owner`, `tipo_instrumento`, `nombre_archivo`, `raw_archivo`,
`raw_archivo_original`, `fecha_carga`. **No existe** `titulo`, `nivel`, `anio`,
`reactivos`, `descripcion`, `kpis` ni `etiquetas` como columnas directas.

**Hecho verificado (artefactos reales en el repo) — corrige la premisa falsa de
la 2.ª iteración.** Existen 21 JSON concretos y versionados en
`storage/raw/inst_01.v1.json` … `inst_21.v1.json`. Su esquema real (verificado
leyendo `inst_01.v1.json`) es:

```jsonc
{
  "instrument_id": "inst_01",
  "schema_version": "1.0",
  "instrument": {
    "title": "Calidad académica y condiciones de aprendizaje",
    "objective": "Explorar cómo percibe el estudiantado ...",
    "dimensions_explored": ["Exigencia y selección académica", "..."],
    "sections": [{
      "section_id": "s1", "name": "Reactivos del módulo",
      "questions": [{ "question_id": "q1", "text": "...", "type": "likert_1_5",
                      "options": ["1 Nada claro", "..."], "scale_min": 1, "scale_max": 5 }]
    }]
  },
  "metadata": {
    "dublin_core": { "dc:title": "...", "dc:description": "...", "dc:subject": "...",
                     "dc:type": "Dataset", "dc:date": "2026-10-01", "dc:language": "es",
                     "dc:coverage": "Estudiantes universitarios, México...", ... },
    "survey_specific": { "poblacion_objetivo": "...", "n_respondentes": 250,
                         "constructo_principal": "...", "dimensiones": ["..."],
                         "palabras_clave": ["calidad académica", "..."], ... }
  },
  "design_reference": { "kpi_hints": ["Accreditation Status and Rankings",
                                      "Average Class Size", "Student-to-Teacher Ratio", ...] },
  "respondents": [{ "respondent_id": "r_0001", "demographics": {...}, "answers": {...} }]
}
```

> **Ninguna** de las claves que la 2.ª iteración extraía (`json["texto"]`,
> `json["preguntas"]`, `json["reactivos"]`, `json["titulo"]`, `json["nivel"]`,
> `json["kpis"]`, `json["metadata"]["titulo"]`) existe. El título vive en
> `instrument.title` y `metadata.dublin_core["dc:title"]`; el texto en
> `instrument.sections[].questions[].text`; los KPI-hint en
> `design_reference.kpi_hints`; la descripción en
> `metadata.dublin_core["dc:description"]`. El contrato de extracción se reescribe
> contra este esquema real.

Por tanto, el tipo `Instrumento` del frontend se construye combinando **dos
fuentes**:

1. **Columnas reales de la DB** (siempre disponibles): `id_crudo`,
   `tipo_instrumento` (crudo → mapeado, §2.4), `nombre_archivo`, `id_owner`,
   `fecha_carga`, `estado` (de `instrumento_procesado`).
2. **El JSON del instrumento** (cuando existe): aporta los campos de dominio. Su
   ubicación/resolución se define en §2.8 (ruta real de la demo:
   `storage/raw/inst_XX.v1.json`; a futuro `instrumento_procesado.ruta_json`).

**Esquema JSON real → `Instrumento` (contrato fijado contra el repo).** El JSON se
lee como `dict`; el mapeo a `Instrumento`, con **defaults de degradación** cuando
una clave falta o no hay JSON, es:

| Campo `Instrumento` | Origen (clave JSON real, con fallbacks en orden) | Default si falta |
|---|---|---|
| `id` | `str(id_crudo)` (DB) | — (siempre existe) |
| `titulo` | `instrument["title"]` → `metadata["dublin_core"]["dc:title"]` → `raw_data.nombre_archivo` | `nombre_archivo` |
| `tipo` | `raw_data.tipo_instrumento` mapeado (§2.4); fallback por `metadata["dublin_core"]["dc:type"]` solo informativo | `"Encuesta"` (§2.4) |
| `nivel` | derivado de `metadata["dublin_core"]["dc:coverage"]` / `survey_specific` (texto → `NivelEducativo` por heurística, §2.3a) | `"Licenciatura"` |
| `autorId` | `str(raw_data.id_owner)` | `""` |
| `anio` | año de `metadata["dublin_core"]["dc:date"]` → año de `fecha_carga` | año de `fecha_carga` |
| `fecha` | `fecha_carga` ISO (AAAA-MM-DD) | fecha de hoy |
| `kpis` | `design_reference["kpi_hints"]` (lista de str) | `[]` |
| `reactivos` | Σ `len(sección["questions"])` sobre `instrument["sections"]` | `0` |
| `estado` | `instrumento_procesado.estado` mapeado (§2.5) | `"Borrador"` |
| `descripcion` | `metadata["dublin_core"]["dc:description"]` → `instrument["objective"]` | `""` |
| `etiquetas` | `metadata["survey_specific"]["palabras_clave"]` → `metadata["dublin_core"]["dc:subject"]` (split por `,`) | `[]` |

> **Lectura defensiva:** el helper navega el `dict` con `.get(...)` anidado;
> cualquier clave ausente o tipo inesperado cae al default sin abortar, de modo
> que `GET /instrumentos` SIEMPRE devuelve un `Instrumento` válido (nunca rompe el
> contrato de tipos del frontend). Un único helper
> `app/services/map_instrumento.py` lo implementa y lo reutilizan list/get (§6) y
> el RAG (`sources.py`, §4.2). **Test obligatorio:** `inst_01.v1.json` real como
> fixture debe producir `titulo` no vacío, `reactivos == 10`, `kpis` con 5
> elementos y `etiquetas` con las 7 palabras clave — garantiza que la extracción
> no quede en defaults vacíos.

#### 2.3a Heurística de `nivel`

`NivelEducativo` es una unión **cerrada de solo dos valores**, verificada contra
`pixel-perfect-pixel/src/types/index.ts`:

```ts
export const NIVELES_EDUCATIVOS = ["Licenciatura", "Posgrado"] as const;
export type NivelEducativo = (typeof NIVELES_EDUCATIVOS)[number];
```

El esquema real no trae un `nivel` canónico; `dc:coverage` y
`survey_specific.poblacion_objetivo` describen "Estudiantes universitarios / de
licenciatura". **Decisión (resuelve hallazgo MED-2):** heurística por substring
sobre esos textos (minúsculas) que **solo** puede emitir valores del conjunto real
`{"Licenciatura", "Posgrado"}`:

```
contiene "posgrado"/"maestr"/"doctor"/"especialidad"  → "Posgrado"
en cualquier otro caso                                 → "Licenciatura"  (default)
```

Se elimina toda referencia a `"Bachillerato"` y a "variantes de posgrado
múltiples": no son asignables a `NivelEducativo` y romperían el contrato de tipos.
`nivel` se documenta en `InstrumentoDTO` como
`Literal["Licenciatura","Posgrado"]`, igual que `tipo` (§2.4) y `estado` (§2.5),
garantizando asignabilidad. Se registra `logger.debug` del texto usado. El default
`"Licenciatura"` cubre el caso dominante de la demo (todos universitarios).

#### 2.3b Dublin Core desde metadata-service (resuelve hallazgo 2)

`metadata-service` **está implementado** (§5.2) y expone `GET /api/metadata/{id}`
devolviendo los 13 campos Dublin Core desde la tabla `metadatos_dc`
(`dc_title`, `dc_description`, `dc_subject`, `dc_coverage`, …). Esto es una
**tercera fuente potencial** de los mismos campos (`titulo`, `descripcion`,
`etiquetas`, `nivel`) ya cubiertos arriba desde el JSON.

**Decisión (basada en el estado real, no en inexistencia): se difiere la
integración de metadata-service en esta tanda, por alcance.** Razón concreta y
verificable: `metadatos_dc` solo tiene filas tras ejecutar el paso 2 del pipeline
(registro DC, `POST /api/metadata/{id}`), que **no** forma parte del flujo
demostrable de esta tanda (carga → juntar → chatear); los artefactos de la demo
son los JSON `inst_XX` ya presentes, que **ya contienen** el bloque
`metadata.dublin_core` embebido. Por tanto el mapeo §2.3 lee el DC directamente
del JSON (donde sí hay datos para los 21 instrumentos) en vez de consultar
`metadata-service` (DB vacía de DC en la demo). Queda anotado como deuda: cuando
el pipeline registre DC, `map_instrumento` puede añadir `GET /api/metadata/{id}`
como fuente preferente antes del JSON embebido, sin cambiar el contrato de
`Instrumento`. `carga.ts`/`kpis.ts` permanecen en mock por este mismo alcance
(§8.4/§8.5), **no** por inexistencia de backend (afirmación corregida).

### 2.4 Mapeo canónico de `tipo` backend→frontend (resuelve hallazgo 7)

`raw_data.tipo_instrumento` es minúsculas con guión bajo
(`encuesta | entrevista | prueba_estandarizada`). `TipoInstrumento` del frontend
es una **unión cerrada capitalizada** (`"Encuesta" | "Entrevista" | "Prueba
estandarizada"`). Mapeo canónico, aplicado **tanto en `GET /instrumentos` como en
`FuenteChatOut.tipo`** (helper único compartido):

```
encuesta              → "Encuesta"
entrevista            → "Entrevista"
prueba_estandarizada  → "Prueba estandarizada"
```

**Fallback para tipo desconocido:** si llega un valor fuera de ese conjunto, se
mapea a `"Encuesta"` (el default más común) y se registra `logger.warning` con el
valor crudo. Nunca se emite un literal fuera de `TipoInstrumento`, garantizando
asignabilidad. En consecuencia **`FuenteChatOut.tipo` se tipa como el mismo
`Literal["Encuesta","Entrevista","Prueba estandarizada"]`**, no `str`.

### 2.5 Mapeo de `estado`

`instrumento_procesado.estado` ∈ {`recibido`, `limpieza_en_proceso`, `limpio`,
`metadatos_registrados`, `estandarizado`, `vectorizado`, `error`}. El frontend usa
`EstadoInstrumento` ∈ {`Borrador`, `En revisión`, `Estandarizado`}. Mapeo:

```
recibido | limpieza_en_proceso | limpio          → "Borrador"
metadatos_registrados                             → "En revisión"
estandarizado | vectorizado                       → "Estandarizado"
error                                             → "Borrador"
```

### 2.6 Artefactos que `storage-service` custodia (requisito del usuario)

- **JSON de metadata-service (PRIMERO, SIN kpis):** `tipo="metadata"`.
- **JSON de analysis-service (SEGUNDO, CON kpis):** `tipo="analysis"`.
- Archivos crudos (respondido/original) y `.sav`: `tipo="raw"` / `tipo="sav"`.
- Scratch temporal: `tipo="temp"`.

Ambos JSON se guardan **versionados y distinguibles** por `(instrumentoId, tipo)`
(§3.2). Aquí `instrumentoId` = `str(id_crudo)` (§2.1).

### 2.7 `settings` y rutas de almacenamiento

`shared/db/core/config.py` **no** define `STORAGE_PATH` como campo; docker-compose
lo inyecta pero pydantic lo ignora (`extra="ignore"`). Los servicios usan los
campos reales: `RAW_PATH`, `JSON_PATH`, `SAV_PATH`, `TEMP_PATH` y sus propiedades
absolutas (`raw_path_abs`, `json_path_abs`, `sav_path_abs`, `temp_path_abs`), más
`CHROMA_HOST`, `CHROMA_PORT`, `EMBEDDING_MODEL`, `OLLAMA_HOST`, `OLLAMA_MODEL`.
**La raíz de storage se deriva como `settings.raw_path_abs.parent`** (igual que
`local_backend.py` del instrument-service). No se modifica `shared/` en esta
tanda.

> **Corrección verificada:** `INSTRUMENT_SERVICE_URL` **SÍ** es campo de
> `AppSettings` (default `http://localhost:8001`), igual que `ANALYSIS_SERVICE_URL`.
> `STORAGE_SERVICE_URL` **NO** es campo (no existe en `config.py`). Por tanto:
> `INSTRUMENT_SERVICE_URL` puede leerse de `settings`; `STORAGE_SERVICE_URL` se lee
> con `os.getenv` (§4.2). (La 2.ª iteración agrupaba ambas como "no son campos",
> lo cual era inexacto para `INSTRUMENT_SERVICE_URL`.)

### 2.8 Correspondencia real `instrumentoId ↔ artefacto` y seed de la demo (resuelve hallazgo 3)

**Hecho verificado:** los únicos JSON de instrumento del repo viven en
`storage/raw/inst_01.v1.json` … `inst_21.v1.json`; `storage/json/` solo contiene
`.gitkeep`. La clave de negocio del archivo es `inst_XX` (y el campo interno
`instrument_id: "inst_XX"`), **no** `str(id_crudo)`, y **no** está bajo
`JSON_PATH/<id>/`. El id canónico del frontend es `str(id_crudo)` (§2.1). Hay por
tanto una brecha entre el id canónico (`id_crudo`, entero de `raw_data`) y la
clave del artefacto físico (`inst_XX`).

**Decisión (combina las dos opciones de la revisión; verificable, sin rutas
hipotéticas):**

- **(a) Seed idempotente de la demo** — un script `scripts/seed_demo.py` (ejecutado
  una vez al preparar la demo, documentado en el README de la tanda) que: por cada
  `storage/raw/inst_XX.v1.json`, (1) inserta/asegura una fila en `raw_data`
  (`id_owner = settings.DEV_USER_ID = 1`, `tipo_instrumento = "encuesta"`,
  `nombre_archivo = inst_XX.v1.json`, rutas apuntando al archivo) y su
  `instrumento_procesado` (`estado = "estandarizado"`,
  `ruta_json = storage/raw/inst_XX.v1.json`), obteniendo el `id_crudo` real; (2)
  **mantiene y persiste el mapeo `inst_XX → id_crudo`** en un pequeño manifiesto
  `storage/raw/_seed_map.json` (`{"inst_01": 1, "inst_02": 2, ...}`). El seed es
  idempotente: si el `inst_XX` ya está mapeado, no duplica. El script es parte de
  la **ejecución** de la demo, no del runtime de los servicios.
- **(b) Fallback de resolución en `sources.py`** — para que el RAG funcione aun sin
  consultar la DB, `core/sources.py` resuelve el artefacto de un `instrumentoId`
  (`= str(id_crudo)`) en este orden: (1) storage-service `GET
  /almacenamiento/artefacto/analysis|metadata/<id>`; (2)
  `instrumento_procesado.ruta_json` (si hay DB); (3) **fallback explícito a
  `storage/raw/`**: lee `_seed_map.json` para traducir `id_crudo → inst_XX`, y si
  no existe el manifiesto, aplica el mapeo directo `id_crudo N → inst_{N:02d}` y
  abre `storage/raw/inst_<NN>.v*.json` (glob por la última versión `v*`). Así, con
  el seed por defecto (`inst_01 → id_crudo 1`), un `instrumentoId = "1"` resuelve a
  `storage/raw/inst_01.v1.json`.

Esto fija una **fuente de contenido verificable** para la demo (los 21 JSON que ya
están en el repo) en vez de una ruta hipotética bajo `JSON_PATH`. El mapeo y el
glob se encapsulan en `sources.resolver_artefacto(instrumentoId)` y se cubren con
un test que, dado `"1"`, encuentra `inst_01.v1.json`.

---

## 3. storage-service (:8004) — autoridad de archivos/artefactos

Reemplaza el stub health-only de `services/storage-service/main.py`. Mantiene el
estilo FastAPI del repo: shim de `import shared` (copiado de
`instrument-service/main.py`), `lifespan` que crea los directorios al arrancar,
CORS `allow_origins=["*"]`, logging `logging.basicConfig` + logger
`storage-service`, arranque `uvicorn` en 8004.

### 3.1 Estructura de archivos (nueva)

```
services/storage-service/
  main.py                      # reemplaza el stub; shim + lifespan + routers
  app/
    __init__.py
    routers/
      __init__.py
      health.py                # GET /health (igual que instrument-service)
      almacenamiento.py        # POST .../json, .../archivo, GET fetch/list
    schemas/
      __init__.py
      almacenamiento.py        # DTOs Pydantic
    core/
      __init__.py
      store.py                 # decisión de ruta + lectura/escritura atómica
      index.py                 # índice ligero (manifest JSON) + saneo de nombre
```

### 3.2 Clave estable de artefacto

```
<tipo>/<instrumentoId>/<version>__<slug-nombre>.<ext>
#   metadata/42/1__instrumento.json      (primer JSON, sin kpis)
#   analysis/42/1__instrumento.json      (segundo JSON, con kpis)
#   raw/42/1__respuestas.xlsx
```

- `tipo ∈ {raw, sav, metadata, analysis, temp}` (resuelve hallazgo 11: `json`
  genérico **se elimina** del conjunto; `metadata` y `analysis` son los únicos
  tipos de JSON y ambos se guardan bajo `JSON_PATH`).
- `metadata`/`analysis` → `JSON_PATH`; `raw` → `RAW_PATH`; `sav` → `SAV_PATH`;
  `temp` → `TEMP_PATH`.
- `version` autoincremental por `(tipo, instrumentoId)` (empieza en 1); conserva
  históricos y distingue "primer" vs "segundo" JSON además de por tipo. El fetch
  sin versión devuelve la **última**.
- `slug-nombre`: saneo idéntico a `_sanitize_filename` de instrument-service
  (NFKD → ASCII → `[^A-Za-z0-9._-]→_`, trunca a 120, fallback `"archivo"`),
  reimplementado como helper local en `core/index.py`.

### 3.3 Endpoints

Prefijo del router: `/almacenamiento`.

| Método | Ruta | Entrada | Salida | Propósito |
|---|---|---|---|---|
| POST | `/almacenamiento/archivo` | multipart: `archivo` (UploadFile), `tipo` (Form), `instrumentoId` (Form, opcional) | `ArtefactoRef` | Guardar binario raw/sav/temp. |
| POST | `/almacenamiento/json` | JSON body `GuardarJsonRequest` | `ArtefactoRef` | Guardar JSON (metadata o analysis). |
| GET | `/almacenamiento/artefacto/{tipo}/{instrumentoId}` | query `version?` | `ArtefactoDetalle` (incluye `contenido` si es JSON) | Recuperar por clave. |
| GET | `/almacenamiento/artefactos` | query `instrumentoId?`, `tipo?` | `list[ArtefactoRef]` | Listar/filtrar. |
| GET | `/health` | — | `{status, service}` | Salud. |

**Schemas (Pydantic v2):**

```python
class GuardarJsonRequest(BaseModel):
    instrumentoId: str
    tipo: Literal["metadata", "analysis"]
    contenido: dict[str, Any]            # el JSON a persistir
    nombre: str | None = None            # para el slug; default "instrumento"

class ArtefactoRef(BaseModel):
    key: str                              # clave relativa estable (§3.2)
    tipo: str
    instrumentoId: str | None
    version: int
    ruta_absoluta: str                    # path dentro del contenedor
    ruta_relativa: str                    # relativa a la raíz de storage
    size_bytes: int
    nombre_original: str
    creado: datetime

class ArtefactoDetalle(ArtefactoRef):
    contenido: dict[str, Any] | None = None   # solo para JSON (metadata/analysis)
```

### 3.4 Decisión de ruta (regla de negocio)

`store.resolver_directorio(tipo)` → `raw→raw_path_abs`, `sav→sav_path_abs`,
`metadata|analysis→json_path_abs`, `temp→temp_path_abs`. Crea el subdirectorio
`<instrumentoId>/`. La respuesta incluye **ambas** rutas (absoluta de contenedor +
relativa) y la clave estable, cumpliendo "decide dónde guardarlos y regresa dónde
están".

### 3.5 Validación de entrada

- `tipo` fuera del conjunto `{raw, sav, metadata, analysis, temp}` → **422** con
  detalle español (`"Tipo de artefacto no soportado: <x>"`). No recuperable.
- `instrumentoId`: en `/json` requerido y no vacío → 422 si falta. En `/archivo`
  opcional (scratch sin instrumento usa `instrumentoId="_"`).
- `archivo` (multipart): límite blando 50 MB → **413** `"El archivo excede el
  tamaño permitido (50 MB)."`.
- `contenido` (JSON): objeto no vacío → 422 si viene `{}` o no-objeto.
- Saneo de `nombre`/filename contra path traversal; el `key` resuelto se verifica
  **dentro** de la raíz de storage (defensa en profundidad, igual que
  `local_backend.eliminar`). Si queda fuera → **400**.

### 3.6 Manejo de errores (por operación)

| Operación | Falla | ¿Recuperable? | Respuesta | Log |
|---|---|---|---|---|
| Escritura a disco | `OSError` en `.part`/`replace` | No (fatal esa petición) | 500 `"No se pudo almacenar el artefacto."` | `error` + traza |
| Fetch por clave | no existe | Sí (otra versión) | 404 `"Artefacto no encontrado."` | `info` |
| Fetch JSON corrupto | `JSONDecodeError` al releer | No | 500 `"El artefacto almacenado no es un JSON válido."` | `error` |
| Lectura del índice | manifiesto ausente | Sí | lista vacía / primera versión = 1 | `debug` |
| Índice corrupto | `JSONDecodeError` del manifiesto | No | 500 `"Índice de artefactos corrupto."` | `error` |

**Índice:** manifiesto JSON por tipo en `JSON_PATH/_index/artefactos.json`,
escritura atómica (`.part`+`replace`) serializada con un `threading.Lock` de
módulo (como `_lock` de `chroma_client.py`). (Alternativa Postgres vía `shared`
descartada: añade esquema/migraciones fuera de alcance.)

### 3.7 Testabilidad

- **Unit:** `resolver_directorio`, saneo de nombre, cálculo de `version`, defensa
  de path traversal — puros / con `tmp_path`.
- **Integración:** POST `/json` → GET `/artefacto/...` round-trip sobre un
  storage temporal; listar con filtros; subir multipart.

---

## 4. visualization-service (:8005) — EL servicio RAG (centro)

Reemplaza el stub health-only de `services/visualization-service/main.py`. Mismo
estilo FastAPI (shim, lifespan, CORS, logging `visualization-service`, uvicorn
:8005). Reutiliza embeddings/Chroma (§1, §4.3).

### 4.1 Estructura de archivos (nueva)

```
services/visualization-service/
  main.py                      # reemplaza el stub
  app/
    __init__.py
    routers/
      __init__.py
      health.py
      rag.py                   # POST /rag/index, POST /rag/chat
    schemas/
      __init__.py
      rag.py                   # DTOs de index y chat
    core/
      __init__.py
      embeddings.py            # COPIA 1:1 de analysis-service (lazy ST, normalize)
      chroma_client.py         # COPIA de analysis-service + query(where=None) aditivo
      chunking.py              # troceo de texto
      sources.py               # obtención de contenido de instrumentos
      ollama_client.py         # cliente httpx a Ollama (stream + no-stream)
      prompt.py                # prompt de fundamentación en español
```

### 4.2 Cómo obtiene el contenido de los instrumentos (resuelve hallazgo 9)

El RAG necesita texto + metadata por instrumento (clave = `str(id_crudo)`, §2.1).
`core/sources.resolver_artefacto(instrumentoId)` localiza el JSON en el orden
definido en §2.8:

1. **storage-service** (preferido): `GET /almacenamiento/artefacto/analysis/<id>`
   (JSON con kpis) y, si falta, `/metadata/<id>` (JSON sin kpis). Se llama por
   `httpx` async. **La URL base se lee con
   `os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004")`** — NO vía
   `settings` (verificado: `AppSettings` no define `STORAGE_SERVICE_URL`; con
   `extra="ignore"` pydantic lo descartaría y `settings.STORAGE_SERVICE_URL` daría
   `AttributeError`). Mismo patrón que `api-gateway/proxy/proxy.py`.
2. **`instrumento_procesado.ruta_json`** (si hay DB disponible vía `shared`).
3. **Fallback a `storage/raw/inst_<NN>.v*.json`** (§2.8): traduce
   `id_crudo → inst_XX` por `_seed_map.json` o por el mapeo directo
   `N → inst_{N:02d}`, y abre la última versión (`glob inst_<NN>.v*.json`). Esta es
   la ruta que resuelve con los artefactos **que de hecho existen** en el repo.

Del JSON (esquema real §2.3) se extrae:
- **texto a indexar** (`sources.extraer_texto(json)`): se concatenan, en este
  orden si existen:
  1. `instrument["title"]`;
  2. `instrument["objective"]`;
  3. `instrument["dimensions_explored"]` (join `\n`);
  4. por cada `instrument["sections"][*]["questions"][*]`:
     `question["text"]` + sus `question["options"]` (join `\n`).
  Fallback si `instrument` falta: `metadata["dublin_core"]["dc:description"]`. Con
  `inst_01.v1.json` esto produce título + objetivo + 5 dimensiones + 10 preguntas
  con sus opciones ⇒ **texto rico y `chunks > 0`** (test obligatorio, §4.13).
- **metadata del instrumento:** `titulo`, `tipo` (mapeado §2.4),
  `investigador` (= `autorId`, hoy `str(id_owner)` o `""`), `kpis` (=
  `design_reference["kpi_hints"]`) — con los mismos defaults de §2.3, vía el helper
  compartido `map_instrumento`.

**Decisión:** se implementan las tres fuentes de §2.8. Si **ninguna** resuelve un
artefacto para un id, ese instrumento se **omite** y se reporta en
`IndexResponse.instrumentos[*].estado = "omitido"` con `motivo` (p. ej. `"sin
artefacto JSON para instrumentoId=<id>"`), sin abortar el resto. No se consulta
instrument-service para texto (solo expone upload/delete + los nuevos list/get de
§6). Con el seed por defecto, `instrumentoIds = ["1","2",...]` resuelven a
`inst_01/02/...` y se indexan con `chunks > 0`.

### 4.3 Reutilización de Chroma y el filtro `where` (resuelve hallazgo 6)

La copia local de `chroma_client.py` es idéntica a la del analysis-service
**salvo una extensión aditiva**: la función `query` recibe un parámetro opcional
`where`:

```python
def query(collection, query_embedding, top_k, where: dict | None = None):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,                       # None ⇒ Chroma lo ignora (= firma original)
        include=["metadatas", "documents", "distances"],
    )
```

Se documenta en el archivo: *"Copia de analysis-service; única desviación: `query`
añade `where` opcional (default None ⇒ comportamiento idéntico al original)"*.
Así el chat puede filtrar por `where={"instrumentoId": {"$in": [...]}}` sin
afirmar una copia "1:1" que sería falsa. `get_or_create_collection`
(`{"hnsw:space": "cosine"}`), `upsert`, `get_point` y el `_lock` se copian sin
cambios.

### 4.4 Naming de colección

`investigacion_<slug>` donde `<slug>` = `investigacionId` saneado a `[a-z0-9_-]`
(Chroma restringe nombres). Función `nombre_coleccion(inv_id)` en el
`chroma_client` local. Una colección por investigación, aislando sus chunks.

### 4.5 Estrategia de chunking

`core/chunking.py`: ventanas de ~800 caracteres con solape de 150, cortando
preferentemente en límites de párrafo/oración (split por `\n\n`, luego `. `),
descartando chunks de <40 caracteres. Chunking por caracteres (no tokens) para no
añadir dependencia de tokenizador; 800/150 entra holgado en la ventana del modelo
de embeddings y da fragmentos citables. Cada chunk hereda la metadata de su
instrumento.

### 4.6 Endpoint de indexado

`POST /rag/index`

```python
class IndexRequest(BaseModel):
    investigacionId: str
    instrumentoIds: list[str]            # ids del frontend (= str(id_crudo))
    reindexar: bool = False              # si true, borra la colección antes

class IndexInstrumentoResultado(BaseModel):
    instrumentoId: str
    chunks: int
    estado: Literal["indexado", "omitido"]
    motivo: str | None = None            # p.ej. "sin artefacto JSON"

class IndexResponse(BaseModel):
    coleccion: str
    total_chunks: int
    instrumentos: list[IndexInstrumentoResultado]
    mensaje: str
```

Flujo: resuelve colección → (si `reindexar`, `delete_collection` + recrea) → por
cada `instrumentoId`: obtiene contenido (§4.2), trocea, `embed_texts(chunks)`,
`upsert` con ids `"<investigacionId>:<instrumentoId>:<n>"`, documents = texto del
chunk, metadatas = `{instrumentoId, titulo, tipo, investigador, kpis(JSON string),
investigacionId, chunk_index}`.

> **Metadata Chroma:** solo acepta escalares (str/int/float/bool). `kpis` (lista)
> se serializa a string JSON al hacer upsert y se deserializa al leer para
> `FuenteChatOut.kpis`. Documentado en `sources.py`.

### 4.7 Endpoint de chat (centro de la demo)

`POST /rag/chat`

```python
class ChatRequest(BaseModel):
    investigacionId: str
    pregunta: str
    instrumentoIds: list[str] | None = None   # filtrar dentro de la colección
    modelo: str | None = None                 # id Ollama; default settings.OLLAMA_MODEL
    stream: bool = True
    top_k: int = 5

    @field_validator("top_k")                 # resuelve hallazgo 12
    @classmethod
    def _clamp_top_k(cls, v: int) -> int:
        return max(1, min(20, v))             # normaliza (NO rechaza) al rango [1,20]

class FuenteChatOut(BaseModel):               # == shape FuenteChat del frontend
    instrumentoId: str
    titulo: str
    tipo: Literal["Encuesta", "Entrevista", "Prueba estandarizada"]  # §2.4
    investigador: str
    kpis: list[str]
    fragmento: str

class ChatResponse(BaseModel):                # usado cuando stream=false
    respuesta: str
    fuentes: list[FuenteChatOut]
    modelo: str
    degradado: bool = False                   # true si Ollama no estuvo disponible
```

Flujo:
1. `embed_text(pregunta)` → vector normalizado.
2. `query(collection, vector, top_k, where=...)`; si `instrumentoIds` viene, se
   pasa `where={"instrumentoId": {"$in": [...]}}` (§4.3).
3. Construir `fuentes` desde los resultados: una `FuenteChatOut` por chunk
   (deduplicando por `instrumentoId`; `fragmento` = chunk más cercano de ese
   instrumento). `kpis` deserializado del string JSON; `tipo` ya viene mapeado
   (§2.4) desde el index.
4. `prompt.construir(pregunta, chunks)` → prompt español fundamentado (§4.8).
5. Llamar a Ollama por `httpx` a `settings.OLLAMA_HOST` + `/api/generate` con
   `{"model": modelo or settings.OLLAMA_MODEL, "prompt": ..., "stream": bool}`.

### 4.8 Prompt de fundamentación (español)

```
Eres un asistente de investigación educativa. Responde en español, de forma
clara y concisa, USANDO ÚNICAMENTE la información del CONTEXTO. Si el contexto
no contiene la respuesta, dilo explícitamente y no inventes datos.

CONTEXTO:
[Fuente 1 — <titulo> (<tipo>, <investigador>)]
<fragmento>
...

PREGUNTA: <pregunta>

RESPUESTA:
```

### 4.9 Streaming y mapeo al callback del frontend

El frontend `enviarMensaje(..., onToken, onDone)` espera tokens por `onToken` y al
final las fuentes por `onDone`. Canal: **`text/event-stream` (SSE) por líneas**:

- `stream=true`: el servicio consume el NDJSON de Ollama (`/api/generate` emite un
  JSON por línea con `response` y `done`) y reemite SSE:
  - `event: token` + `data: {"t": "<trozo>"}` por cada fragmento.
  - `event: fuentes` + `data: {"fuentes": [...FuenteChatOut...]}` **una vez** al
    final (las fuentes se calculan en el paso 3, antes de Ollama).
  - `event: fin` + `data: {}` para cerrar.
- `stream=false`: `ChatResponse` JSON de una sola vez (curl / clientes no-stream).

Mapeo en el cliente (`chat.ts`, §8.3): `fetch` con lectura incremental del
`ReadableStream` (no `EventSource`: no permite POST ni headers de auth). Se parsea
por líneas: `token`→`onToken(t)`; `fuentes`→se guardan; `fin`→`onDone(fuentes)`.
Devuelve un cancelador con `AbortController`.

### 4.10 Degradación grácil si Ollama no está disponible

`ollama_client` captura `httpx.ConnectError`/timeout:
- `stream=false`: 200 con `ChatResponse(respuesta=<mensaje>, degradado=true,
  fuentes=<recuperadas>)`. Mensaje: *"No se pudo contactar al modelo local
  (Ollama). Se muestran las fuentes recuperadas de tus instrumentos; reintenta
  cuando el modelo esté disponible."*
- `stream=true`: un único `event: token` con ese mensaje, luego `fuentes` y `fin`.
  La UI nunca se cuelga. El **happy path** (Ollama arriba) produce respuesta real.

Timeout Ollama: `httpx.Timeout(connect=5, read=120)`.

### 4.11 Validación de entrada (chat/index)

- `investigacionId`: requerido, no vacío, saneable → 422 si vacío.
- `instrumentoIds`: en index, lista no vacía → 422 si vacía. En chat, opcional.
- `pregunta`: requerida, 1..4000 chars → 422 fuera de rango.
- `top_k`: normalizado a [1,20] por `field_validator` (clamp, no rechaza; §4.7).
- `modelo`: si viene y no está instalado en Ollama, Ollama devuelve error → se
  trata como degradación (§4.10). No se valida contra catálogo local.

### 4.12 Manejo de errores (por operación)

| Operación | Falla | ¿Recuperable? | Respuesta | Log |
|---|---|---|---|---|
| Embedding | modelo ST no carga | No | 500 `"No se pudo cargar el modelo de embeddings."` | `error` |
| Chroma query/upsert | Chroma caído | No esa petición | 502 `"Vector store no disponible."` | `error` |
| Colección inexistente en chat | aún no indexada | Sí | 409 `"La investigación no está indexada todavía."` | `info` |
| Obtener contenido instrumento | storage + volumen fallan | parcial | se omite ese instrumento (`omitidos`), 200 | `warning` |
| Ollama no disponible | connect/timeout | Sí | degradación §4.10 (200) | `warning` |
| Ollama responde error (modelo inexistente) | 4xx/5xx de Ollama | Sí | degradación citando el modelo | `warning` |

### 4.13 Testabilidad

- **Unit:** `chunking` (límites, solape, descarte), `nombre_coleccion` (saneo),
  `prompt.construir` (contiene contexto y pregunta), parsers del stream, mapeo de
  `tipo` (§2.4), clamp de `top_k`.
- **Integración (Chroma + Ollama vía compose):** index de 1-2 instrumentos → chat
  `stream=false` devuelve respuesta no vacía + fuentes; chat `stream=true` emite
  tokens. `ollama_client` mockeable para tests sin GPU/modelo.

---

## 5. api-gateway (:8000) — cableado del proxy

### 5.1 Corrección del helper `proxy_request`

En `services/api-gateway/proxy/proxy.py`, `proxy_request` debe devolver la
respuesta del upstream **transparente**: mismo status, mismo cuerpo. Se reescribe
para devolver un `fastapi.responses.Response`/`JSONResponse` con
`status_code=response.status_code` y el cuerpo tal cual
(`content=response.content`, `media_type=response.headers.get("content-type")`).
Así `pedir()` recibe el JSON de dominio directo y el status real (incluye
401/404/409/422 para que mapee mensajes). Se elimina el envoltorio
`{status_code, body}`, el `except Exception → 502` genérico (que ocultaba
errores) y la función muerta `proxy_to_service` (URL con `PORT` literal).

**Streaming a través del gateway:** la ruta de chat es SSE. El gateway no debe
bufferizarla: usa `httpx.AsyncClient.stream(...)` y devuelve `StreamingResponse`
reemitiendo chunks, preservando `content-type: text/event-stream`. Las demás
rutas usan el proxy transparente normal.

**Passthrough de Authorization:** se reenvían los headers del request
(`headers = dict(request.headers)`), eliminando `host` y `content-length` para que
`httpx` los recompute. Se conserva `Authorization`.

### 5.2 Rutas del gateway (nuevas) y registro

En `main.py` se añade `app.include_router(proxy_router)` (hoy no incluido). El
router reemplaza sus endpoints de ejemplo por rutas limpias, con **passthrough por
prefijo** (`{path:path}`) que reenvía método + body + headers, más la ruta
especial de `/rag/chat` que streamea. Las claves de `SERVICES` ya existen en
`proxy.py` (instruments/analysis/metadata/storage/visualization) y se reutilizan.

> **El proxy reenvía el path TAL CUAL, sin traducir (resuelve hallazgo 7).** El
> `proxy.py` actual trae endpoints de ejemplo en inglés (`/instruments/upload`)
> que **se eliminan**. Los servicios reales montan rutas en español (verificado:
> `instrument-service` → `prefix="/instrumentos"`, `POST /instrumentos/upload`,
> `DELETE /instrumentos/{id_crudo}`). El router de proxy reenvía el path exacto
> recibido (`/instrumentos/...`, `/almacenamiento/...`, `/rag/...`) al upstream
> correspondiente **sin reescribirlo** (nada de traducir inglés↔español ni remapear
> segmentos).

Instrumentos (→ instrument-service :8001):
- `GET /instrumentos` y `GET /instrumentos/{id}` (list/get, §6)
- `GET /instrumentos/{id}/descarga` (si §6 lo implementa)
- `GET /instrumentos/kpis/catalogo` (catálogo de KPIs desde instrument-service)
- `POST /instrumentos/upload` (multipart passthrough)
- `DELETE /instrumentos/{id}` → `DELETE /instrumentos/{id_crudo}` real (§2.1)

Storage (→ storage-service :8004):
- `POST /almacenamiento/json`, `POST /almacenamiento/archivo`
- `GET /almacenamiento/artefacto/{tipo}/{instrumentoId}`
- `GET /almacenamiento/artefactos`

Visualización / RAG (→ visualization-service :8005):
- `POST /rag/index`
- `POST /rag/chat` (StreamingResponse)

Salud/auth se conservan: `GET /health`, `/auth/*`.

**metadata-service — IMPLEMENTADO, pero NO proxeado en esta tanda por alcance
(resuelve hallazgo 2).** Corrección de la afirmación falsa de la 2.ª iteración:
`metadata-service` **sí tiene código** (verificado): `main.py` monta
`app.include_router(..., prefix="/api")`, con `routers/metadata.py`
(`GET/POST/DELETE /api/metadata/{id}`, `GET /api/metadata/{id}/init`,
`GET /api/metadata`) y `routers/enrichment.py`
(`POST /api/enrichment/{id}/create`, `GET /api/enrichment/{id}`,
`POST /api/enrichment/{id}/approve`, `GET /api/enrichment/{id}/summary`), más
`dc_manager.py` y `enrichment_engine.py`. Las rutas reales cuelgan de `/api/*`
(prefijo `/api`), no de `/metadata/*`.

**Decisión (por alcance, no por inexistencia): el gateway NO publica `/metadata/*`
en esta tanda.** Razón: el flujo demostrable (carga → juntar instrumentos →
chatear con RAG) no ejecuta el paso de registro Dublin Core, por lo que
`metadatos_dc` está vacío en la demo y proxear `/metadata/*` no aportaría datos al
entregable central; además mezclaría el prefijo `/api` del servicio con el estilo
sin prefijo del resto del gateway. La clave `metadata` permanece en `SERVICES`
para una tanda futura; **si** se proxea entonces, debe respetarse el prefijo real
`/api` (p. ej. `GET /metadata/{id}` del gateway → `GET /api/metadata/{id}` del
upstream, traducción explícita documentada en esa tanda). En consecuencia,
`carga.ts` y `kpis.ts` permanecen en mock (§8.4/§8.5) **por alcance de esta
tanda**, no por falta de backend; además los metadatos de dominio para la demo se
leen del bloque `metadata.dublin_core` ya embebido en los JSON `inst_XX` (§2.3b).

### 5.3 Correlación con `src/api/client.ts`

`pedir()` hace `fetch` y espera JSON + status directo. Con el proxy corregido,
cualquier `pedir(`${API_URL}/...`)` funciona sin tocar `pedir`. El multipart de
upload NO usa `pedir` (fuerza `Content-Type: application/json`); se usa `fetch`
directo con `FormData` (sin fijar Content-Type) y el token de `leerToken()`.

---

## 6. Listado / get / descarga de instrumentos (resuelve hallazgos 1 y 2)

Hoy instrument-service expone **solo** `POST /instrumentos/upload`, `DELETE
/instrumentos/{id_crudo}` y `/health`. El frontend necesita además
`getInstrumentos()`, `getInstrumento(id)`, `getCatalogoKpis()` y
`descargarInstrumento(id, formato)`.

**Decisión: añadir list/get a instrument-service** (tiene DB vía `shared`), con
los datos construidos según §2.3 (DB + JSON de `ruta_json` con defaults de
degradación) y los mapeos de `tipo`/`estado` de §2.4/§2.5. Archivos nuevos:
`app/routers/list.py` y el helper `app/services/map_instrumento.py`.

**Autenticación de los endpoints nuevos (resuelve hallazgo 4).** `upload` y
`delete` existentes exigen `Depends(require_rol(ROL_INVESTIGADOR,
ROL_ADMINISTRADOR))` (verificado en `upload.py`/`delete.py`); `dependencies.py`
declara explícitamente que **no hay bypass de desarrollo** en el instrument-service
(todo endpoint protegido valida un Bearer JWT real). Por coherencia y para no
exponer datos sin sesión, los **nuevos** `GET /instrumentos`,
`GET /instrumentos/{id}` y `GET /instrumentos/kpis/catalogo` usan la **misma**
dependencia `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)`. Esto obliga a que
el frontend los llame con `{auth:true}` (§8.1).

> **Nota `AUTH_DEV_MODE`:** el campo `settings.AUTH_DEV_MODE` existe y por defecto
> es `True`, pero el `require_rol`/`get_current_user` del instrument-service **no
> lo consulta** (valida JWT siempre). Por tanto la lista exige token también en
> Docker; el frontend ya posee sesión tras el login (`leerToken()`), así que
> `getInstrumentos()` dentro del `useEffect` de `ChatPage` debe ejecutarse con
> sesión activa. No se depende de `AUTH_DEV_MODE` como contrato.

Endpoints nuevos (todos devuelven `id = str(id_crudo)`; todos
`Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))`):

- `GET /instrumentos` → `list[InstrumentoDTO]`. Lee `raw_data` join
  `instrumento_procesado`; por cada fila construye el DTO con `map_instrumento`
  (resuelve el JSON por §2.8 si existe). Mapeable a `Instrumento` del frontend.
- `GET /instrumentos/{id}` → `InstrumentoDTO | 404`. `{id}` = `id_crudo`.
- `GET /instrumentos/kpis/catalogo` → `list[str]`: unión de los `kpis`
  (`design_reference["kpi_hints"]`) presentes en los JSON de todos los
  instrumentos (o `[]` si aún no hay JSON). Sirve al `getCatalogoKpis()` de
  `instrumentos.ts` (lista de strings).
- `DELETE /instrumentos/{id}` → **ya existe** (`{id_crudo}`, mismo `require_rol`);
  el gateway lo reexpone (§5.2). No se añade nada.

`InstrumentoDTO` (Pydantic v2) espeja `Instrumento` del frontend:
`{id: str, titulo, tipo (Literal §2.4), nivel, autorId, anio, fecha, kpis:
list[str], reactivos, estado (Literal §2.5), descripcion, etiquetas}` + campo
informativo `idProcesado: str | None` (= `str(id_instrumento)`), que el frontend
ignora al mapear a `Instrumento`.

**Descarga** (`descargarInstrumento`): `GET /instrumentos/{id}/descarga?formato=
crudo|json|sav`:
- `json` → lee el artefacto `analysis` (o `metadata`) desde storage/volumen.
- `crudo`/`sav` → sirve el binario original desde `RAW_PATH`/`SAV_PATH`.

**Alcance práctico (demo RAG):**
- `getInstrumentos`, `getInstrumento`, `eliminarInstrumento`, `getCatalogoKpis`
  (de `instrumentos.ts`) → **reales** vía gateway.
- `descargarInstrumento` → real si el endpoint de descarga entra; si por tiempo se
  difiere, **queda en su comportamiento actual (blob local) con TODO**, sin romper
  firma.
- `buscarRelacionados`, `getInvestigadores` → **mock/local con TODO** (no bloquean
  el RAG; no inventar endpoints). Respeta "no inventar endpoints que ningún
  servicio expone".

---

## 7. Cambios en docker-compose

- `visualization-service` (resuelve hallazgo 5): hoy su bloque **no** define
  `OLLAMA_*`, `CHROMA_*`, `EMBEDDING_MODEL`, URLs de servicio, ni `depends_on` de
  `ollama`/`chromadb`, ni `hf_cache` (verificado). Para que el modelo/dimensión de
  embeddings y la conexión a Chroma/Ollama queden **idénticos** a los de
  `analysis-service` (y la similitud coseno sea coherente), se **copian
  textualmente** sus valores. El bloque queda EXACTO así (se añade lo marcado;
  se conservan los envs de Postgres y los `*_PATH` ya presentes):

  ```yaml
  visualization-service:
    build:
      context: .
      dockerfile: ./infrastructure/docker/Dockerfile.visualization-service
    container_name: indagata_visualization_service
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_started      # AÑADIR (igual que analysis-service)
      chromadb:
        condition: service_started      # AÑADIR
    environment:
      SERVICE_NAME: visualization-service
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-indagata_db}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-securepassword}
      STORAGE_PATH: /app/storage          # ya presente
      JSON_PATH: /app/storage/json        # ya presente
      SAV_PATH: /app/storage/sav          # ya presente
      RAW_PATH: /app/storage/raw          # AÑADIR (fallback §2.8 lee storage/raw)
      TEMP_PATH: /app/storage/temp        # AÑADIR
      # ── AÑADIR, copiados textualmente de analysis-service ──
      OLLAMA_HOST: http://ollama:11434
      OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.2:3b}
      CHROMA_HOST: chromadb
      CHROMA_PORT: 8000
      EMBEDDING_MODEL: ${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-mpnet-base-v2}
      # ── URLs de servicio (leídas con os.getenv, §4.2) ──
      STORAGE_SERVICE_URL: http://storage-service:8004
      INSTRUMENT_SERVICE_URL: http://instrument-service:8001
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ports:
      - "8005:8005"
    volumes:
      - ./services/visualization-service:/app
      - ./shared:/app/shared
      - ./storage:/app/storage
      - hf_cache:/root/.cache/huggingface   # AÑADIR (reusa el volumen ya declarado)
    networks:
      - indagata_network
    restart: unless-stopped
  ```

  > El volumen `hf_cache` ya está declarado al final del compose (lo usa
  > analysis-service); solo se monta aquí, no se declara de nuevo.
  > `EMBEDDING_MODEL` = `...mpnet...` produce **768** dimensiones, idéntico a
  > analysis-service ⇒ los vectores de ambas apps son compatibles.
  > `STORAGE_SERVICE_URL`/`INSTRUMENT_SERVICE_URL` se **leen con `os.getenv`**
  > (§4.2): `STORAGE_SERVICE_URL` no es campo de `AppSettings`;
  > `INSTRUMENT_SERVICE_URL` sí lo es, pero por simetría se lee igual con
  > `os.getenv` (el env del contenedor lo provee). `OLLAMA_*`, `CHROMA_*`,
  > `EMBEDDING_MODEL` SÍ son campos de `settings` y llegan por env.
- `storage-service`: ya tiene paths y volúmenes `./storage`/`./chromadb`; no
  requiere cambios de env.
- `api-gateway`: sin cambios de env (ya trae las `*_SERVICE_URL`, incluida
  `METADATA_SERVICE_URL`, aunque no se use esta tanda).

**Puertos Chroma:** dentro de la red Docker, Chroma escucha en `chromadb:8000`;
por eso `CHROMA_PORT=8000` para los servicios (8008 es el mapeo al host). El
default de `config.py` (8008) es para desarrollo fuera de Docker.

**Nota frontend (resuelve hallazgo 10):** el servicio `frontend` de
`docker-compose.yml` monta `./frontend` y expone 3000, pero la app real está en
`pixel-perfect-pixel/`. **El contenedor `frontend` de compose NO sirve esta app
tal cual.** Para la demo el frontend se ejecuta **fuera de Docker** (`npm run dev`
en `pixel-perfect-pixel/` con `VITE_API_URL=http://localhost:8000` y
`VITE_ANALYSIS_URL=http://localhost:8002`). Corregir el contexto/volumen del
servicio `frontend` queda **fuera de alcance** de esta tanda (otra tanda).

---

## 8. Frontend — de-mock sin tocar la UI

Regla: cuerpos reales, mocks fuera para lo que pasa a real; sin imports de
`src/mocks` en esas funciones. Todas las llamadas por `API_URL` (gateway) salvo
analysis (directo). **Excepción acotada:** se permiten dos cambios mínimos de
firma/valor en la capa `src/api` y un cambio de un literal en `ChatPage.tsx`,
justificados en §8.3 (el enunciado prohíbe cambios de UI/estilo, no de firmas de
`src/api` cuando son imprescindibles para el contrato).

### 8.1 `src/api/instrumentos.ts`
- `getInstrumentos()` → `pedir<InstrumentoDTO[]>(`${API_URL}/instrumentos`,
  {auth:true})`, mapeando DTO→`Instrumento`.
  **Map campo a campo, descartando `idProcesado` (resuelve hallazgo 6).**
  `Instrumento` (en `src/types/index.ts`) es una interfaz cerrada **sin**
  `idProcesado`; para no colar la propiedad extra del DTO, el map NO hace spread,
  sino asignación explícita de los 12 campos:
  ```ts
  const mapear = (d: InstrumentoDTO): Instrumento => ({
    id: d.id,
    titulo: d.titulo,
    tipo: d.tipo,            // ya Literal §2.4 desde el backend
    nivel: d.nivel,
    autorId: d.autorId,
    anio: d.anio,
    fecha: d.fecha,
    kpis: d.kpis,
    reactivos: d.reactivos,
    estado: d.estado,        // ya Literal §2.5
    descripcion: d.descripcion,
    etiquetas: d.etiquetas,
  });                        // d.idProcesado se ignora deliberadamente
  ```
- `getInstrumento(id)` → `GET ${API_URL}/instrumentos/${id}` con `{auth:true}`;
  aplica el mismo `mapear`. **Manejo de 404 → null (resuelve hallazgo MED-3):** la
  firma exportada actual es `Promise<Instrumento | null>`, y `pedir()` **lanza**
  `ErrorHttp` con `status` en cualquier respuesta no-2xx (verificado en
  `client.ts`), de modo que un 404 NO se traduce solo a `null`. Para preservar la
  firma sin cambios, se captura el 404 y se devuelve `null`:
  ```ts
  export async function getInstrumento(id: string): Promise<Instrumento | null> {
    try {
      const dto = await pedir<InstrumentoDTO>(`${API_URL}/instrumentos/${id}`, { auth: true });
      return mapear(dto);
    } catch (e) {
      if ((e as ErrorHttp).status === 404) return null;
      throw e;
    }
  }
  ```
  Cualquier otro status se re-lanza. La firma `Promise<Instrumento | null>` queda
  intacta.
- `eliminarInstrumento(id)` → `DELETE ${API_URL}/instrumentos/${id}` con
  `{auth:true}`; `id` es `str(id_crudo)` (§2.1), que es lo que el endpoint real
  espera.
- `getCatalogoKpis()` → `GET ${API_URL}/instrumentos/kpis/catalogo` con
  `{auth:true}` (list[str]).
- `getInvestigadores()` → **mock con TODO** (sin endpoint; no crítico).
- `descargarInstrumento()` → real si §6 lo implementa; si no, blob local + TODO.
- `buscarRelacionados()` → **local + TODO**.

### 8.2 `src/api/investigaciones.ts`
- `getInvestigaciones()` / `crearInvestigacion()`: **no hay servicio de
  investigaciones** en el backend. Decisión: **persistencia en cliente
  (localStorage)**, no mock estático, para que el flujo "crear investigación →
  juntar instrumentos → chatear" sea real de punta a punta sin backend nuevo.
  - Clave `indagata.investigaciones` → `Investigacion[]`.
  - `crearInvestigacion(nombre, propietarioId)` genera `id = res-<timestamp>`,
    lo guarda en esa lista y lo devuelve (firma intacta). Ese `id` es el
    `investigacionId` de index/chat (§2.2).
  - `getInvestigaciones()` lee de localStorage (vacío ⇒ `[]`).
  Se documenta como el único dominio sin backend; crear
  `investigaciones-service` queda fuera de alcance (no inventar).

### 8.3 `src/api/chat.ts` — cableado del RAG (resuelve hallazgos 3, 4, 5)

**Selección de instrumentos por investigación — dónde vive (resuelve hallazgo 4).**
No existe estado de "instrumentos juntados por investigación". Se persiste en
**cliente**, junto a `indagata.investigacionActiva`:

- Clave `indagata.instrumentosPorInvestigacion` → `Record<investigacionId,
  string[]>` (ids = `str(id_crudo)`).
- Dos helpers nuevos **exportados** en `chat.ts` (son API de datos, no UI):
  `setInstrumentosDeInvestigacion(investigacionId, instrumentoIds)` y
  `getInstrumentosDeInvestigacion(investigacionId): string[]`.
- **Quién arma la lista (resuelve hallazgo HIGH-1 — Opción A elegida):** el flujo
  de contexto del chat. Hoy `ChatPage.handleComenzar` ya calcula
  `instrumentosFuentes` y llama `guardarContexto(activa.id, ctx)`. Se amplía esa
  llamada para pasar también `instrumentosFuentes.map(i => i.id)` (ver cambio de
  firma abajo); así "juntar los instrumentos" queda materializado y persistido.
  **El `useEffect` que hoy puebla `instrumentosFuentes` NO se toca.** Verificado
  contra `pixel-perfect-pixel/src/features/chat/ChatPage.tsx`, su lógica actual es
  determinista (filtra 3 propios + 2 ajenos vía `getInstrumentos()`), **no**
  aleatoria, y alimenta directamente `<ChipsFuentes>`; cambiar su fuente de datos
  alteraría qué chips se renderizan, lo cual es un cambio de UI prohibido. Por eso
  el `useEffect` conserva su poblado actual intacto y NO lee la clave de
  localStorage. El único cambio en `ChatPage.tsx` es **ampliar los argumentos** de
  las dos llamadas existentes (`guardarContexto` y `enviarMensaje`): `guardarContexto`
  recibe la lista de ids ya mostrados y la persiste + indexa. Así los chips se ven
  exactamente igual que hoy y el RAG recibe los ids que ya están a la vista; se
  elimina toda dependencia circular (la clave solo se escribe, nunca se lee para
  poblar la vista inicial).

**Cambios de firma acotados y justificados (resuelve hallazgo 3).**
`ContextoInvestigacion` no porta `investigacionId` ni instrumentos, y `chat.ts`
(módulo plano) no puede leer `ResearchContext` (hook). En vez de un setter
implícito frágil, se **amplían las firmas** de las dos funciones de `chat.ts` para
recibir explícitamente lo que necesitan. Es un cambio de la capa `src/api` (no de
UI/estilo), y obliga a ajustar las dos llamadas en `ChatPage.tsx` (que ya tiene
`activa.id` y la lista de fuentes a mano):

- `enviarMensaje(pregunta, contexto, modelo, onToken, onDone, investigacionId,
  instrumentoIds?)`:
  - `fetch` POST a `${API_URL}/rag/chat` con `{investigacionId, pregunta,
    instrumentoIds: instrumentoIds ?? getInstrumentosDeInvestigacion(
    investigacionId), modelo, stream:true, top_k:5}`.
  - Lee el `ReadableStream`, mapea eventos SSE a `onToken`/`onDone(fuentes)`
    (§4.9). Devuelve cancelador con `AbortController`.
  - Llamada en `ChatPage.handleEnviar`: pasa `activa.id` (ya disponible vía
    `useResearch()`) y, opcionalmente, los ids ya cargados.
  - **Dependencias del `useCallback` (resuelve hallazgo MED-4):** `handleEnviar`
    es hoy `useCallback(..., [contexto, modelo])`. Al referenciar `activa.id` en el
    cuerpo, su array de dependencias pasa a `[contexto, modelo, activa]` para
    evitar un closure obsoleto de `activa` si el usuario cambia de investigación
    activa sin que cambien `contexto`/`modelo` (enviaría la pregunta a la colección
    equivocada). Es un cambio de lógica acotado, no de JSX ni estilo; se declara
    igual que los demás cambios acotados de `ChatPage.tsx`.
- `guardarContexto(investigacionId, contexto, instrumentoIds)`:
  - `setInstrumentosDeInvestigacion(investigacionId, instrumentoIds)` (persiste la
    selección) y luego `POST ${API_URL}/rag/index` con `{investigacionId,
    instrumentoIds}`. Mantiene `Promise<void>`.
  - Llamada en `ChatPage.handleComenzar`: pasa `activa.id`, `ctx` y los ids de
    `instrumentosFuentes.map(i => i.id)`.

> Estos son los únicos cambios de componente permitidos: ajustar los **argumentos**
> de dos llamadas existentes en `ChatPage.tsx` (no se toca JSX, estilos ni layout).

**Modelos LLM (resuelve hallazgo 5).**
- `MODELOS_DISPONIBLES` → `[{ id: "llama3.2:3b", etiqueta: "Llama 3.2 (3B) —
  local" }]` (opcionalmente más modelos Ollama con etiquetas en español).
- **`ModeloLLM` (en `src/types/index.ts`) se re-tipa** a los id(s) Ollama (el
  "minimal src/types adjustment" que el enunciado autoriza):
  `export type ModeloLLM = "llama3.2:3b";` (o unión de los instalados).
- **Reconocido explícitamente:** re-tipar `ModeloLLM` **rompe `ChatPage.tsx:48`**
  (`useState<ModeloLLM>("gpt-4o")`). Por tanto se edita ESA línea cambiando el
  literal inicial a `"llama3.2:3b"` — **cambio acotado de un valor literal**, no
  de estructura ni estilo. Verificado que no hay otros literales de `ModeloLLM`
  en componentes (`BarraEntrada.tsx` usa el tipo pero no literales;
  `MODELOS_DISPONIBLES` es el otro punto y ya se actualiza). Si se quisiera cero
  cambios de componente, la alternativa sería dejar `ModeloLLM` como unión
  **abierta** añadiendo los ids Ollama sin quitar `"gpt-4o"`; se descarta porque
  deja literales cloud muertos y confunde el catálogo. **Elegido: re-tipar +
  editar la línea 48.**

### 8.4 `src/api/carga.ts`
- `limpiarArchivo`, `getKpisSugeridos`, `guardarInstrumento` → dependen del paso
  de limpieza/metadatos/enriquecimiento del pipeline. metadata-service **sí está
  implementado** (`/api/metadata/*`, `/api/enrichment/*`, §5.2), pero su
  integración **se difiere por alcance** de esta tanda (el flujo demostrable es
  carga→juntar→chatear, no el registro DC) y además el gateway no proxea
  `/metadata/*` todavía. Por tanto estas funciones **permanecen en `simularRed`
  con TODO** que apunta a los endpoints reales (`POST /api/metadata/{id}`,
  `POST /api/enrichment/{id}/create`) para la tanda que los cablee. Subidas de
  archivo (si entran) usan `fetch` + `FormData`.

### 8.5 `src/api/kpis.ts`
- `getCatalogoKpis()` (`KpiCatalogo[]`), `getKpis`, `getNoticias`,
  `getDatosGrafica` → dashboard/visualización de datos sin backend en esta tanda →
  **mock + TODO**. No bloquean el RAG. (El `getCatalogoKpis` que SÍ se cablea es
  el de `instrumentos.ts`, que devuelve `string[]`, no el `KpiCatalogo[]` de aquí.)

### 8.6 `src/api/client.ts`
Sin cambios de firma. El streaming de chat usa `fetch` directo en `chat.ts` (no se
toca `pedir`, usado por auth y que debe seguir forzando JSON).

---

## 9. Resumen de contratos (tabla única)

| Contrato | Método/Ruta (gateway salvo nota) | Request | Response |
|---|---|---|---|
| Guardar JSON | `POST /almacenamiento/json` | `{instrumentoId, tipo: metadata\|analysis, contenido, nombre?}` | `ArtefactoRef` |
| Guardar binario | `POST /almacenamiento/archivo` (multipart) | `archivo, tipo, instrumentoId?` | `ArtefactoRef` |
| Recuperar artefacto | `GET /almacenamiento/artefacto/{tipo}/{instrumentoId}?version=` | — | `ArtefactoDetalle` |
| Listar artefactos | `GET /almacenamiento/artefactos?instrumentoId=&tipo=` | — | `ArtefactoRef[]` |
| Indexar investigación | `POST /rag/index` | `{investigacionId, instrumentoIds, reindexar?}` | `IndexResponse` |
| Chat RAG (JSON) | `POST /rag/chat` (stream=false) | `{investigacionId, pregunta, instrumentoIds?, modelo?, stream:false, top_k?}` | `ChatResponse` |
| Chat RAG (stream) | `POST /rag/chat` (stream=true) | idem | SSE: `token*`, `fuentes`, `fin` |
| Instrumentos list (auth) | `GET /instrumentos` | — | `InstrumentoDTO[]` (id=str(id_crudo)) |
| Instrumento get (auth) | `GET /instrumentos/{id}` | — | `InstrumentoDTO` |
| Catálogo KPIs (instrumentos, auth) | `GET /instrumentos/kpis/catalogo` | — | `string[]` |
| Descarga instrumento | `GET /instrumentos/{id}/descarga?formato=crudo\|json\|sav` | — | binario / JSON |
| Eliminar instrumento | `DELETE /instrumentos/{id}` (id=id_crudo) | — | `{mensaje}` |
| Upload instrumento | `POST /instrumentos/upload` (multipart) | `archivo, tipo_instrumento, archivo_original?` | `UploadResponse` |

---

## 10. Supuestos (consolidados)

1. El texto semántico y los metadatos de cada instrumento viven en los JSON
   `storage/raw/inst_XX.v1.json` (**verificado en el repo**, 21 artefactos), con
   el esquema real `instrument.* / metadata.dublin_core / metadata.survey_specific
   / design_reference.kpi_hints` (§2.3). El contrato de extracción de §2.3/§4.2
   apunta a esas claves reales; los defaults de degradación cubren un instrumento
   sin JSON sin romper el tipo del frontend. No se usa ningún endpoint de contenido
   de instrument-service (no existe).
2. **`Instrumento.id` del frontend = `str(id_crudo)`** (PK de `raw_data`), elegido
   para que el `DELETE /instrumentos/{id_crudo}` existente funcione sin endpoints
   nuevos. `id_instrumento` viaja como `idProcesado` informativo.
3. `investigacionId` es clave opaca generada por el frontend (`res-...`); el
   backend solo la sanea para el nombre de colección Chroma.
4. No hay servicio de investigaciones; `investigaciones.ts` persiste en
   **localStorage** (cliente). Crear un servicio queda fuera de alcance.
5. `STORAGE_PATH` no es campo de `settings`; la raíz de storage se deriva de
   `settings.raw_path_abs.parent`.
6. `STORAGE_SERVICE_URL` NO es campo de `AppSettings` ⇒ se lee con `os.getenv`.
   `INSTRUMENT_SERVICE_URL` **SÍ** es campo de `AppSettings` (verificado), pero por
   simetría también se lee con `os.getenv` en el visualization-service. (Corrige la
   agrupación inexacta de la 2.ª iteración.)
7. `CHROMA_PORT=8000` dentro de Docker (no 8008, mapeo al host).
8. `embeddings.py` se copia 1:1; `chroma_client.py` se copia con una única
   extensión aditiva (`query(where=None)`). No se promueven a `shared/` esta tanda.
9. `ModeloLLM` se re-tipa a los id(s) Ollama; esto exige editar el literal inicial
   de `ChatPage.tsx:48` (cambio acotado de valor, declarado permitido).
10. `enviarMensaje`/`guardarContexto` amplían su firma para recibir
    `investigacionId`/`instrumentoIds`; se ajustan las dos llamadas en
    `ChatPage.tsx` (solo argumentos, sin tocar JSX/estilo).
11. metadata-service **está implementado** (routers reales en `/api/metadata/*` y
    `/api/enrichment/*`, **verificado**). NO se proxea `/metadata/*` en el gateway
    **por alcance** de esta tanda (no por inexistencia); `carga.ts`/`kpis.ts`
    quedan en mock con TODO que apunta a esos endpoints reales. Los metadatos DC de
    la demo se leen del bloque `metadata.dublin_core` embebido en los JSON `inst_XX`
    (§2.3b).
12. El frontend corre fuera de Docker para la demo (`npm run dev` + `VITE_*`); el
    servicio `frontend` de compose no sirve esta app (fuera de alcance).
13. Formato NDJSON de `/api/generate` de Ollama (`response`/`done`): contrato
    externo de un tercero, razonable y no verificable en el repo.
14. Las funciones de frontend sin backend (relacionados, investigadores, kpis de
    dashboard, noticias, gráficas, limpieza/kpis sugeridos) permanecen en
    `simularRed` con TODO, sin romper firmas.
15. Las operaciones de rama (`git`: crear `pruebas`, subir) son parte de la
    ejecución, no de este diseño.
16. La fuente de contenido de la demo son los 21 JSON `storage/raw/inst_XX.v1.json`
    (**verificado**). La correspondencia `inst_XX ↔ id_crudo` se fija por un seed
    idempotente (`scripts/seed_demo.py` + `storage/raw/_seed_map.json`) y, en su
    defecto, por el mapeo directo `id_crudo N → inst_{N:02d}` con glob de la última
    versión (§2.8). El RAG no depende de rutas hipotéticas bajo `JSON_PATH`.
17. `GET /instrumentos`, `GET /instrumentos/{id}` y `GET /instrumentos/kpis/catalogo`
    exigen `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` (como upload/delete) y
    el frontend los llama con `{auth:true}`. El instrument-service valida JWT
    siempre (no consulta `AUTH_DEV_MODE`).
18. El `visualization-service` copia **textualmente** `EMBEDDING_MODEL`,
    `CHROMA_HOST/PORT`, `OLLAMA_HOST/MODEL`, `depends_on` y `hf_cache` de
    `analysis-service` (YAML exacto en §7) ⇒ embeddings de 768 dim coherentes entre
    ambas apps.
19. El nivel educativo (`NivelEducativo`) no existe como campo canónico en el JSON;
    se deriva por heurística de `dc:coverage`/`poblacion_objetivo` con default
    `"Licenciatura"` (§2.3a). Es una aproximación declarada, no un dato afirmado.

---

## 11. Respuestas a los hallazgos de la revisión (1.ª revisión, iteración 1→2)

> _Histórico. Las respuestas a la revisión más reciente (iteración 2→3) están en
> §12._


- **[HIGH 1] Metadatos de dominio no están en `instrumento_procesado`.**
  **Resuelto.** §2.3 corrige la premisa: se enumeran las columnas reales de ambos
  modelos y se define que `Instrumento` se arma combinando DB + el JSON de
  `ruta_json`, con esquema JSON→campo y defaults de degradación explícitos (opción
  (a)+(b) de la revisión combinadas). §6 implementa el `GET /instrumentos` sobre
  esa fuente mediante `map_instrumento`. Se eliminó toda afirmación de que esos
  campos vivan en la DB.

- **[HIGH 2] Conflicto de id en el borrado.** **Resuelto.** §2.1 fija
  `Instrumento.id = str(id_crudo)` (no `id_instrumento`), precisamente para que
  `DELETE /instrumentos/{id_crudo}` existente funcione sin endpoints nuevos. Todo
  el diseño (index/chat/fuentes/list) usa ese id canónico. `id_instrumento` queda
  como `idProcesado` informativo.

- **[HIGH 3] `enviarMensaje` sin `investigacionId`/`instrumentoIds`.**
  **Resuelto.** §8.3 amplía explícitamente la firma de `enviarMensaje` (y
  `guardarContexto`) para recibirlos, y ajusta las dos llamadas en `ChatPage.tsx`
  (solo argumentos). Se abandona el "se verifica al implementar".

- **[HIGH 4] `guardarContexto` sin fuente de `instrumentoIds`.** **Resuelto.**
  §8.3 define la clave de localStorage
  `indagata.instrumentosPorInvestigacion`, los helpers
  `set/getInstrumentosDeInvestigacion`, y que `handleComenzar` arma la lista desde
  `instrumentosFuentes` y la pasa a `guardarContexto`, que persiste e indexa.

- **[HIGH 5] Re-tipar `ModeloLLM` rompe `ChatPage.tsx:48`.** **Resuelto.** §8.3
  reconoce el cambio y lo declara permitido como edición acotada de un literal
  (`"gpt-4o"`→`"llama3.2:3b"`), tras verificar que no hay otros literales en
  componentes. Se documenta la alternativa (unión abierta) y por qué se descarta.

- **[MED 6] `where` no cabe en el `query` "1:1".** **Resuelto.** §1 y §4.3 dejan de
  afirmar copia "1:1" para `chroma_client.py`: la copia añade un parámetro
  opcional aditivo `where=None`, documentado en el archivo. `embeddings.py` sí es
  1:1.

- **[MED 7] `FuenteChatOut.tipo: str` vs unión cerrada.** **Resuelto.** §2.4 define
  el mapeo canónico `encuesta→"Encuesta"` etc. (con fallback) aplicado a
  `GET /instrumentos` y a las fuentes; §4.7 tipa `FuenteChatOut.tipo` como
  `Literal["Encuesta","Entrevista","Prueba estandarizada"]`.

- **[MED 8] metadata-service inexistente proxeado a la nada.** **Resuelto.** §5.2
  declara metadata-service como stub y **no publica `/metadata/*`**; `carga.ts`/
  `kpis.ts` dependientes quedan en mock (§8.4/§8.5).

- **[MED 9] `STORAGE_SERVICE_URL` no es campo de `settings`.** **Resuelto.** §4.2 y
  §7 especifican `os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004")`
  (como el gateway), no `settings.*`. Supuesto 6 lo consolida.

- **[NIT 10] Servicio `frontend` de compose no sirve esta app.** **Resuelto.** §7
  añade la nota: el frontend corre fuera de Docker (`npm run dev` + `VITE_*`);
  arreglar compose queda fuera de alcance.

- **[NIT 11] `json` genérico en el conjunto de tipos.** **Resuelto.** §3.2 elimina
  `json` del conjunto permitido; solo `metadata`/`analysis` (ambos bajo
  `JSON_PATH`).

- **[NIT 12] `top_k` clamp no reflejado en el schema.** **Resuelto.** §4.7 añade un
  `field_validator` que normaliza `top_k` a `[1,20]` (clamp, no rechaza); §4.11 y
  §4.13 lo reflejan.

---

## 12. Respuestas a los hallazgos de la revisión (2.ª revisión, iteración 2→3)

Esta revisión (`design-review.json`, veredicto `CHANGES_REQUESTED`: 2 HIGH + 3
MEDIUM + 2 NIT) señaló que dos afirmaciones "verificadas" eran falsas contra el
repo. Antes de revisar, se **leyeron directamente** los archivos citados para
confirmar cada hallazgo; todos resultaron correctos. Respuestas:

- **[HIGH 1] El esquema real del JSON de instrumento existe y no coincide con el
  contrato de extracción.** **Resuelto (addressed).** Verificado leyendo
  `storage/raw/inst_01.v1.json`: el esquema real es `instrument.title/objective/
  dimensions_explored`, `instrument.sections[].questions[].text/options`,
  `metadata.dublin_core[dc:*]`, `metadata.survey_specific.palabras_clave`,
  `design_reference.kpi_hints`. §2.3 reescribe la tabla de mapeo contra esas claves
  reales (ya no `json["texto"]`/`["preguntas"]`/etc.); §4.2 reescribe
  `sources.extraer_texto` para concatenar título + objetivo + dimensiones +
  `questions[].text/options`. Se añade un **test obligatorio** con
  `inst_01.v1.json` que exige `chunks > 0`, `reactivos == 10`, `kpis` con 5
  elementos y `etiquetas` con 7 (§2.3, §4.13). La premisa "el esquema no está
  fijado en el repo" se eliminó.

- **[HIGH 2] `metadata-service` NO es un stub sin código.** **Resuelto
  (addressed).** Verificado: `main.py` monta routers con `prefix="/api"`;
  `routers/metadata.py` expone `/api/metadata/*` y `routers/enrichment.py`
  `/api/enrichment/*`, con `dc_manager.py`/`enrichment_engine.py`. §5.2 corrige la
  afirmación falsa y declara que **no se proxea `/metadata/*` por alcance** (no por
  inexistencia), con el prefijo real `/api` documentado para la tanda futura. §2.3b
  explica que los metadatos DC de la demo se leen del bloque `metadata.dublin_core`
  embebido en los JSON (donde sí hay datos), difiriendo `GET /api/metadata/{id}`
  como fuente preferente futura. Supuesto 11 corregido.

- **[MED 3] La clave de artefacto no coincide con la ubicación real de los JSON.**
  **Resuelto (addressed).** Verificado: los JSON viven en
  `storage/raw/inst_XX.v1.json`, no bajo `JSON_PATH/<id>/`. §2.8 fija la
  correspondencia real combinando (a) un **seed idempotente** que inserta
  `raw_data`/`instrumento_procesado` y persiste `inst_XX → id_crudo` en
  `storage/raw/_seed_map.json`, y (b) un **fallback en `sources.py`** que resuelve
  `id_crudo → inst_XX` (por el manifiesto o por `N → inst_{N:02d}`) y abre
  `storage/raw/inst_<NN>.v*.json`. Fuente de contenido verificable, no hipotética.

- **[MED 4] Autenticación de los nuevos GET no especificada.** **Resuelto
  (addressed).** §6 declara que `GET /instrumentos`, `GET /instrumentos/{id}` y
  `GET /instrumentos/kpis/catalogo` usan `require_rol(ROL_INVESTIGADOR,
  ROL_ADMINISTRADOR)` (coherente con upload/delete, verificados) y que el frontend
  los llama con `{auth:true}` (§8.1 lo aplica a los tres). Se documenta que el
  instrument-service valida JWT siempre y **no** consulta `AUTH_DEV_MODE`.

- **[MED 5] Envs de embeddings/Chroma/Ollama del visualization-service.**
  **Resuelto (addressed).** §7 fija el **YAML exacto** del bloque copiando
  textualmente de analysis-service: `EMBEDDING_MODEL` mpnet (768),
  `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`, `OLLAMA_HOST=http://ollama:11434`,
  `OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2:3b}`, `depends_on [ollama, chromadb]
  (service_started)` y `hf_cache:/root/.cache/huggingface`. Sin margen de
  desalineación de dimensión.

- **[NIT 6] `InstrumentoDTO.idProcesado` debe descartarse en el map.** **Resuelto
  (addressed).** §8.1 especifica el map campo a campo de los 12 campos de
  `Instrumento` (`{id, titulo, tipo, nivel, autorId, anio, fecha, kpis, reactivos,
  estado, descripcion, etiquetas}`), sin spread, ignorando `idProcesado`.

- **[NIT 7] Fijar que el proxy reenvía el path tal cual.** **Resuelto
  (addressed).** §5.2 añade que el router reenvía el path exacto (`/instrumentos/*`,
  `/almacenamiento/*`, `/rag/*`) sin traducir y que se eliminan los endpoints de
  ejemplo en inglés (`/instruments/*`) del `proxy.py`.

**Nota sobre las "assumptions no verificadas" de la revisión:** se corrigió la
agrupación de `INSTRUMENT_SERVICE_URL` (SÍ es campo de `settings`) vs.
`STORAGE_SERVICE_URL` (no lo es) en §2.7/§4.2/§7 y supuesto 6. El resto de
assumptions que la revisión marcó como correctas se mantienen.
