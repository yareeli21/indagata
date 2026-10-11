# Hallazgos — Asistente de carga de instrumentos (Indagata)

Investigación de solo lectura. Rama `elotro-back`. Raíz: `C:\Users\yarel\Documents\indagata\indagata`.
No se modificó código. Todas las citas son `archivo:símbolo` o `archivo:línea` reales leídos durante la investigación.

---

## Resumen ejecutivo (respuesta primero)

El asistente de carga está **parcialmente cableado al backend real**. Los pasos 1 (subir),
3 (Dublin Core) y 7 (cálculo de KPIs) sí llaman a servicios reales; los pasos 2 (limpieza),
4 (metadatos del tipo) y 6 (KPIs sugeridos) quedan **locales o inertes** porque el flujo de
upload "puro" nunca produce los artefactos (JSON enriquecido + `.md` original) que el resto
del pipeline espera.

Las 5 fallas tienen **una sola causa raíz compartida**: el pipeline fue diseñado alrededor de
instrumentos **sembrados** (`storage/raw/inst_XX.v1.json` + `inst_XX.md`), con un JSON de dominio
estructurado (`metadata.dublin_core`, `metadata.survey_specific`, `instrument.sections[].questions[]`,
`design_reference.kpi_hints`). El flujo de upload real **no genera ese JSON**: solo guarda el archivo
crudo, lo parsea a una tabla (`RawTable`: headers + filas) y crea `instrumento_procesado` en estado
`recibido` **sin `ruta_json`**. A partir de ahí:

- **Bug 1 (Dublin Core):** el formulario y el payload del wizard no cubren los 7 campos de usuario del
  contrato real; faltan `dc_source` y `dc_relation`, y envía `dc_subject` desde un campo "Tema" singular.
- **Bug 2 (metadatos del tipo):** los campos del paso 4 **no existen** en ningún contrato backend y
  **no se persisten**; el único endpoint de enriquecimiento es para propuestas LLM, no para esos campos.
- **Bug 3 (tipos de pregunta):** el pipeline de upload **no clasifica tipos de pregunta** en absoluto;
  la tipificación solo vive en el JSON sembrado. No hay "supuesto de una sola escala"; hay **ausencia de
  tipificación**.
- **Bug 4 (sin KPIs):** `index_summary()` (indexar en `summary_instrument`) **solo** se invoca dentro de
  `ProposalService.propose`, alcanzable únicamente por `POST /vectorizacion/propuestas`, que **exige**
  `archivo_json` (JSON enriquecido) + `instrumento_original` (`.md`). El upload puro no produce ninguno,
  así que el `useEffect` del wizard corta con `setSugeridos([])` → 0 propuestas → 0 cálculo.
- **Bug 5 (instrumento equivocado en la lista):** como el upload no escribe `ruta_json`,
  `resolver_json_por_id_crudo(1)` cae al fallback `inst_{N:02d}` → carga `storage/raw/inst_01.v1.json`
  (sembrado) → título "Calidad académica y condiciones de aprendizaje" y KPIs en inglés
  ("Accreditation Status and Rankings", …). El listado SÍ usa el backend real; el dato equivocado
  viene del fallback a la semilla, no de un mock del frontend.

---

## Evidencia por bug

### Bug 1 — Dublin Core (paso 3): el formulario no coincide con el contrato real

**Contrato real (13 campos).** `services/metadata-service/routers/metadata.py` (docstring de
`register_metadata`) y `services/metadata-service/services/dc_manager.py:DCManager.register_dc`
definen 6 campos autollenados + 7 de usuario:

- Autollenados (backend): `dc_creator`, `dc_publisher`, `dc_type`, `dc_format`, `dc_date`, `dc_language`.
  En `dc_manager.register_dc` se fijan a: `app_name` (publisher), `tipo_instrumento` de `raw_data` (type),
  extensión de la ruta (format), fecha UTC de hoy (date), `"es"` (language). `dc_creator` se toma del
  request o cae a `"Sistema"`.
- De usuario (los que el backend LEE del request):
  `dc_title`, `dc_subject` (lista), `dc_description`, `dc_coverage`, `dc_rights`, `dc_source`, `dc_relation`
  (ver `MetadatosDC(...)` en `dc_manager.py`).

**Columnas en BD.** `infrastructure/postgres/init/01_schema.sql` tabla `metadatos_dc` (líneas ~90-106):
`id_crudo` (PK/FK), `dc_title` (NOT NULL), `dc_creator`, `dc_description`, `dc_type`, `dc_date`,
`dc_language`, `dc_coverage`, `dc_subject`, `dc_publisher`, `dc_rights`, `dc_format`, `dc_source`,
`dc_relation`. → 13 campos, coherentes con `dc_manager`.

**Lo que el frontend recoge.** `pixel-perfect-pixel/src/features/upload/StepDublinCore.tsx` captura:
`titulo`, `creador`, `tema`, `descripcion`, `fecha`, `idioma`, `derechos`, `cobertura` (select de
`NIVELES_EDUCATIVOS`). El tipo `DublinCore` (`src/types/index.ts`) tiene exactamente esos 8 campos; **no
tiene** `fuente`/`source` ni `relacion`/`relation`.

**Lo que el frontend ENVÍA.** `UploadWizard.tsx` paso 2→3 (función `avanzar`, bloque `if (paso === 2 ...)`)
arma `RegistroMetadatos`:
```
dc_title       ← dc.titulo
dc_creator     ← dc.creador
dc_subject     ← dc.tema.split(",")   // de UN campo "Tema"
dc_description ← dc.descripcion
dc_coverage    ← dc.cobertura (opcional)   // = nivel educativo
dc_rights      ← dc.derechos (opcional)
```
`src/api/carga.ts:registrarMetadatos` hace `POST /api/metadata/metadata/{id}`. La ruta y el doble
`metadata` son correctos (coinciden con el proxy del gateway, ver abajo).

**Diferencias exactas:**
- **Campos de usuario que el backend acepta y el wizard SÍ envía (6/7):** `dc_title`, `dc_subject`,
  `dc_description`, `dc_coverage`, `dc_rights`. (`dc_creator` también, aunque el backend lo trata como
  autollenado y lo persiste tal cual.)
- **Campos de usuario que el backend acepta pero el wizard NO envía:** `dc_source` (fuente),
  `dc_relation` (relación). `RegistroMetadatos` en `carga.ts` **sí los declara opcionales**, pero el
  formulario `StepDublinCore` no tiene inputs para ellos y `UploadWizard` nunca los setea → nunca viajan.
- **Campos que el wizard captura pero el backend IGNORA en el registro:** `fecha` (`dc.fecha`) e `idioma`
  (`dc.idioma`). El backend **ignora** cualquier `dc_date`/`dc_language` del request: `register_dc` los
  sobreescribe con hoy-UTC y `"es"`. (El init sí sugiere `dc_date`/`dc_language`, pero el POST no los lee.)
- **`cobertura` como nivel educativo:** el wizard mapea `dc_coverage` ← nivel educativo
  (`"Licenciatura"`/`"Posgrado"`), no una cobertura geográfica/temporal. Es una decisión de producto, no
  un bug de contrato, pero conviene documentarla.

**¿El wizard llama realmente al metadata-service?** Sí. `UploadWizard.avanzar()` en `paso === 2` invoca
`registrarMetadatos` (real), maneja 409 (inmutable) avanzando igual, y un `useEffect` previo llama
`getMetadatosInit` para pre-poblar. Es decir, **el paso 3 SÍ está cableado** al backend real.

**Comportamiento correcto:** agregar inputs para `dc_source` y `dc_relation` (opcionales), renombrar/duplicar
"Tema" → `dc_subject` con semántica de lista de palabras clave, y **ocultar o marcar como informativos**
`fecha`/`idioma` en el paso de registro (porque el backend los fija). Opcionalmente, mostrar los 6
autollenados como solo-lectura usando `getMetadatosInit`.

**Cambio mínimo (archivos):**
- `pixel-perfect-pixel/src/types/index.ts` — añadir `fuente?: string; relacion?: string;` a `DublinCore`.
- `pixel-perfect-pixel/src/features/upload/StepDublinCore.tsx` — inputs para fuente y relación; aclarar
  que fecha/idioma son informativos.
- `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx` — incluir `dc_source`/`dc_relation` en
  `RegistroMetadatos` cuando no estén vacíos.

---

### Bug 2 — Metadatos del tipo (paso 4): no existen en el backend y no se persisten

**Lo que recoge el frontend.** `pixel-perfect-pixel/src/features/upload/StepMetadatosTipo.tsx`
(`CAMPOS_POR_TIPO`): Encuesta → `numero_reactivos`, `escala`, `modalidad`, `tamano_muestra`;
Entrevista → `tipo_entrevista`, `numero_preguntas`, `duracion_minutos`, `perfil_informante`;
Prueba → `numero_reactivos`, `puntaje_maximo`, `confiabilidad`, `tiempo_limite`.
El estado es `MetadatosTipo = Record<string, string>` (`src/types/index.ts`), **texto libre sin esquema**.

**Lo que el backend tiene para "metadatos enriquecidos".** Tablas en `01_schema.sql`:
- `metadatos_enriquecidos_encuestas` (líneas ~109-122): `n_respondentes`, `n_poblacion`, `objetivo`,
  `carrera`, `poblacion_objetivo`, `constructo_principal`, `palabras_clave` (JSONB), `dimensiones` (JSONB),
  `notas_contextuales`, `notas_interpretacion`.
- `metadatos_enriquecidos_entrevistas` (~123-131): `identificador_propio`, `objetivo`, `metodologia`,
  `institucion`, `derechos`.
- `metadatos_enriquecidos_pruebas` (~132-152): `unidad_de_aprendizaje`, `mapeo_de_reactivos_por_seccion`
  (JSONB), `institucion`, `campus`, `grado`, `grupo`, `ciclo_escolar`, `tipo_de_prueba`, `version`,
  `taxonomia_bloom`, `nivel_educativo`, `objetivo_de_evaluacion`, `subareas`, `competencias`.

**Mismatch de campos.** NINGÚN campo del paso 4 coincide con esas columnas: el wizard pide
`numero_reactivos`/`escala`/`modalidad`/`tamano_muestra`, pero la tabla de encuestas pide
`n_respondentes`/`objetivo`/`constructo_principal`/`dimensiones`/… El vocabulario es completamente distinto.

**¿Hay endpoint que persista esos campos?** No para estos campos. El único enriquecimiento es
`services/metadata-service/routers/enrichment.py`, proxied por el gateway como `/api/enrichment/*`
(ver `services/api-gateway/proxy/proxy.py`, docstring líneas ~12-14). Pero su contrato es de **propuestas
LLM**, no del formulario del wizard:
- `POST /enrichment/{id}/create` recibe `List[dict]` con forma
  `{"tipo": "domain_inferred", "valor": ..., "confianza": 0.95, "descripcion": ...}` y está pensado para
  que **analysis-service** lo llame tras el análisis LLM (docstring del módulo: "analysis-service calls
  POST /enrichment/{id} with proposals").
- `GET /enrichment/{id}`, `POST /enrichment/{id}/approve` son revisión/aprobación de esas propuestas.

El frontend `src/api/carga.ts` **no tiene ninguna función** que llame a `/api/enrichment/*` ni a las tablas
`metadatos_enriquecidos_*`. En `UploadWizard.tsx`, `meta` (del paso 4) **solo** entra al objeto `documento`
(memo) que alimenta la `JsonPreview` del paso 5 y el resumen del paso 8; `guardarInstrumento(documento)`
(`carga.ts`) es un **no-op** que solo devuelve `{ id }` sin persistir nada
(ver docstring: "El 'guardado' de dominio del paso 4 es el `json_enriquecido`…").

**Conclusión:** los metadatos del tipo son **puramente locales/mock**. No se guardan en ninguna parte.

**Comportamiento correcto:** dos opciones de diseño (elegir una en la fase de implementación):
1. Reemplazar `CAMPOS_POR_TIPO` por los campos reales de cada tabla `metadatos_enriquecidos_*` y crear un
   endpoint en metadata-service (p. ej. `POST /api/enrichment/{id}/manual` o un router dedicado de
   metadatos específicos) que escriba a esas tablas por `id_crudo`. Requiere nuevo contrato + modelo
   SQLAlchemy (hoy no existe un modelo para esas tablas accesible desde el wizard).
2. Marcar el paso 4 explícitamente como "informativo/no persistente" hasta que exista el contrato, para no
   dar la falsa impresión de que se guarda.

**Cambio mínimo (archivos):**
- Backend: `services/metadata-service/routers/` (nuevo endpoint) + `shared/models/` (modelos de
  `metadatos_enriquecidos_*`) + `services/metadata-service/services/` (lógica de persistencia).
- Frontend: `src/features/upload/StepMetadatosTipo.tsx` (campos alineados a la tabla),
  `src/api/carga.ts` (nueva función que llame al endpoint), `src/features/upload/UploadWizard.tsx`
  (invocarla al avanzar del paso 3→4 o en guardar).

---

### Bug 3 — Tipos de pregunta mixtos (Likert + opción múltiple + sí/no + numérica)

**El upload NO tipifica preguntas.** `services/instrument-service/app/parsing/tabular_parser.py`
(`read_csv`/`read_xlsx`) produce un `RawTable` con `headers` + `rows` normalizados y notas de parseo.
No hay clasificación de escala ni de tipo de pregunta en todo `app/parsing/*`
(`tabular_parser.py`, `document_parser.py`, `header_utils.py`, `raw_table.py`). El `UploadResponse`
(`schemas/upload.py`) solo expone `ParseoArchivo` (columnas, filas, preview, encoding, notas).

**La tipificación solo existe en el JSON sembrado.** La semántica de preguntas vive en los artefactos
`storage/raw/inst_XX.v1.json`, bajo `instrument.sections[].questions[]`. El backend la consume en dos
lugares, **ambos sobre ese JSON**, no sobre la tabla cruda:
- `services/instrument-service/app/services/map_instrumento.py:_extraer_reactivos` cuenta
  `len(section["questions"])` para el DTO del listado.
- `services/analysis-service/app/vectorization/core/metadata_extractor.py:extract_key_metadata` lee
  `metadata.dublin_core` + `metadata.survey_specific` + `respondents[]` para armar el summary.

**El cálculo de KPIs no mira tipos de pregunta.** `services/analysis-service/app/vectorization/routers/
kpi_calculo.py` deriva variables de la **fórmula del KPI** (vía Ollama en `/preparar`) y de valores que
captura el usuario; el tipo/escala de las preguntas **no interviene**.

**Respuesta a las preguntas del bug:**
- ¿El pipeline asume una sola escala? **No**: no asume ninguna escala porque **no clasifica** preguntas en
  el flujo de upload. El "tipo de escala" solo aparece como texto libre en el paso 4 del wizard
  (`StepMetadatosTipo`, campo `escala`), que no se persiste (ver Bug 2).
- ¿Qué pasa hoy con instrumentos de tipos mixtos? El respondido se guarda como tabla; cada columna es un
  encabezado normalizado sin tipo. Un instrumento con Likert + opción múltiple + sí/no + numérica se trata
  igual: columnas de texto. No se rompe, pero tampoco se interpreta.
- ¿Dónde vive el supuesto? No hay un supuesto de "una sola escala" en código. El supuesto implícito es más
  fuerte: **el pipeline espera un JSON ya estructurado y tipificado** (sembrado), y el upload no lo produce.

**Comportamiento correcto / cambio mínimo:** si se requiere soportar tipos mixtos de forma real, hace falta
una etapa de **estandarización** que convierta el `RawTable` en el JSON de dominio
(`instrument.sections[].questions[]` con `type`/`scale` por pregunta). Esa etapa **no existe** hoy. Es una
pieza nueva (no inventar un servicio: encajaría como fase en instrument-service entre `recibido` y
`metadatos_registrados`, escribiendo `instrumento_procesado.ruta_json`). Mínimo viable para no bloquear:
detectar tipo por heurística de columna (valores en {sí,no}; conjunto pequeño de opciones; numérico; escala
1..N) al parsear, y persistirlo. Archivos candidatos: `app/parsing/` + nuevo servicio de estandarización +
`shared/models/instrumento_procesado` (`ruta_json`).

---

### Bug 4 — No se recomiendan KPIs → no hay cálculo

**Cadena completa de `/vectorizacion/propuestas`:**
1. `services/analysis-service/app/vectorization/routers/vectorizacion.py:proponer_kpis` recibe (multipart)
   `archivo_json`, `instrumento_original` (`.md`/`.txt`), `tipo_instrumento`, `id_instrumento`. Lee ambos
   archivos y llama a `ProposalService.propose`.
2. `services/analysis-service/app/vectorization/services/proposal_service.py:ProposalService.propose`:
   parsea tipo + JSON, `extract_key_metadata` (lee `metadata.dublin_core`/`survey_specific`/`respondents`),
   `build_summary` (metadatos + texto del `.md`), luego:
   `embeddings.embed_text` → **`kpi_search.index_summary(...)`** → `kpi_search.search_kpis(...)`.
3. `services/analysis-service/app/vectorization/core/kpi_search.py:index_summary` hace el `upsert` del
   vector del summary en la colección Chroma `summary_instrument` (id = `id_instrumento`).
   `search_kpis` consulta la colección `kpis` y devuelve los más cercanos por score.
4. `summary_builder.build_summary` requiere metadatos y/o texto del `.md`; si ambos faltan, `propose` lanza
   422 ("No se pudo construir el summary").

**Por qué el summary NUNCA se indexa en el flujo real:**
- `index_summary` se invoca **exclusivamente** dentro de `ProposalService.propose` (confirmado: no hay otra
  llamada en `app/vectorization/*`). No hay path de "seed" que lo llame por separado; es la ruta de
  `/propuestas` o nada. (La inspección `GET /vectorizacion/summary/{id}` solo lee lo que ya exista.)
- `/propuestas` **exige** `archivo_json` + `instrumento_original`. El upload puro NO los produce:
  `UploadService.upload` (`instrument-service`) solo guarda crudos y crea `instrumento_procesado` en
  `recibido` **sin `ruta_json`** y sin generar un `.md` original ni un JSON enriquecido.
- En el frontend, `UploadWizard.tsx` (useEffect del `paso === 5`) tiene la guarda:
  `if (!jsonInstrumento || !archivoOriginal) { setSugeridos([]); return; }`. Como en el upload puro
  `jsonInstrumento` y `archivoOriginal` son `null` (comentario en el propio archivo: "en el flujo de upload
  puro quedan nulos"), **nunca** llama a `proponerKpis`. Resultado: `sugeridos = []`.
- `src/api/carga.ts:proponerKpis` confirma la exigencia de `archivoJson` + `instrumentoOriginal` (manda
  `archivo_json` como Blob JSON e `instrumento_original` como Blob markdown).

**Encadenamiento con el cálculo:** sin propuestas aceptadas, `kpisParaCalcular` queda vacío en
`UploadWizard`, el paso 7 no tiene KPIs, y `guardar()` no registra ningún `kpi_calculo`. De ahí "tampoco se
pudo hacer el cálculo" (mensaje 4 del usuario).

**Confirmación del dato del orquestador:** `tt_rag.documento_vectorizado` con 0 filas es consistente: el
upload nunca indexó el summary (no se llamó `index_summary`), y la tabla relacional de vectorización
(`documento_vectorizado`, `01_schema.sql` ~250) no se puebla en el flujo de upload.

**La brecha "subir instrumento" ↔ "tener summary vectorizado":** falta una etapa que, tras el upload,
produzca (a) el JSON de dominio y (b) el texto del instrumento original, y que invoque la vectorización. Hoy
esa etapa solo existe de facto para instrumentos sembrados (que ya traen `inst_XX.v1.json` + `inst_XX.md`).
El TODO explícito en `UploadWizard.tsx` lo reconoce: "no hay endpoint que devuelva el JSON enriquecido tras
el upload para alimentar las propuestas end-to-end".

**Comportamiento correcto / cambio mínimo (usando lo que EXISTE):**
- Opción A (más fiel): añadir una etapa de estandarización (ver Bug 3) que escriba `ruta_json` y derive el
  texto original, y luego llamar a `/vectorizacion/propuestas` con esos artefactos. Archivos:
  instrument-service (estandarización) + `UploadWizard.tsx`/`carga.ts` (alimentar `proponerKpis`).
- Opción B (mínima para desbloquear): construir en el cliente un JSON mínimo
  (`metadata.dublin_core` con los DC capturados + `metadata.survey_specific` con lo del paso 4) y usar el
  `.md`/texto del instrumento original (el usuario YA sube el original — ver `StepArchivo`/`archivoOriginal`
  en `UploadWizard`) para poblar `jsonInstrumento` + `archivoOriginal` antes del paso 5. Esto hace que
  `proponerKpis` tenga insumos y que `index_summary` corra. Archivos: `UploadWizard.tsx` (construir
  `jsonInstrumento` desde `dc`+`meta`; usar `archivoOriginal` ya cargado), posiblemente `carga.ts`.
- Prerrequisito operativo: la colección `kpis` debe estar indexada
  (`POST /vectorizacion/kpis/reindex`, `routers/vectorizacion.py:reindexar_kpis`) o `search_kpis` no
  devolverá candidatos aunque el summary sí se indexe.

---

### Bug 5 — El listado muestra un instrumento distinto (semilla) en vez del enc_01 cargado

**El listado usa el backend REAL.** `pixel-perfect-pixel/src/api/instrumentos.ts:getInstrumentos` hace
`pedir(GET /instrumentos)` (no mock). El gateway proxea `/instrumentos` → instrument-service :8001
(`services/api-gateway/proxy/proxy.py:instrumentos_get`). Así que el título/KPIs equivocados vienen del
backend, no de `src/mocks/data`.

**Cadena de resolución del título/KPIs:**
1. `services/instrument-service/app/routers/list.py:listar_instrumentos` hace
   `RawData LEFT JOIN InstrumentoProcesado` y, por fila, llama
   `resolver_json_por_id_crudo(raw.id_crudo, procesado)` y luego `mapear_instrumento(raw, procesado, json)`.
2. `services/instrument-service/app/services/instrumento_query.py:resolver_json_por_id_crudo`:
   - (1) `_resolver_por_ruta_json(procesado)`: usa `procesado.ruta_json` **si existe en disco**.
   - (2) si no, `_resolver_fallback_raw(id_crudo)`: `_slug_por_id_crudo` traduce `id_crudo → inst_XX`
     usando `_seed_map.json` o, en su ausencia, el mapeo directo `N → inst_{N:02d}`; luego carga la última
     versión `storage/raw/inst_<NN>.v*.json`.
3. `services/instrument-service/app/services/map_instrumento.py`:
   - `_extraer_titulo` = `instrument.title` → `dc:title` → `nombre_archivo`.
   - `extraer_kpis` = `design_reference.kpi_hints` (lista de strings).

**Causa raíz, confirmada con los artefactos:**
- El upload (`UploadService.upload`) crea `InstrumentoProcesado(id_crudo=raw.id_crudo, estado="recibido")`
  **sin asignar `ruta_json`** (grep del campo: no se setea en el upload). Por tanto, para el enc_01
  (`id_crudo=1`), `_resolver_por_ruta_json` devuelve `None`.
- No existe `storage/raw/_seed_map.json` (verificado: `Test-Path … _seed_map.json` → `False`). Entonces
  `_slug_por_id_crudo(1)` cae al mapeo directo `inst_{1:02d}` = `inst_01`.
- `storage/raw/inst_01.v1.json` existe y contiene (verificado leyendo el archivo):
  `instrument.title = "Calidad académica y condiciones de aprendizaje"`,
  `dc:title` idéntico, y `design_reference.kpi_hints = ["Accreditation Status and Rankings",
  "Admissions Selectivity", "Average Class Size", "Benchmark Test Scores",
  "Student-to-Teacher Ratio"]`.

Eso explica **exactamente** el título mostrado y los KPIs en inglés del reporte del orquestador (bug #5):
el fallback a la semilla `inst_01.v1.json` secuestra la fila real `id_crudo=1`.

**Comportamiento correcto:** el listado debe reflejar el instrumento realmente cargado (nombre de archivo /
DC registrados), no una semilla con el mismo índice. El fallback `N → inst_{N:02d}` es peligroso porque
colisiona cualquier `id_crudo` bajo con un `inst_XX` sembrado del mismo número.

**Cambio mínimo (archivos):**
- `services/instrument-service/app/services/instrumento_query.py` — eliminar (o restringir) el fallback
  implícito `N → inst_{N:02d}`: usar fallback a `storage/raw` **solo** si `_seed_map.json` mapea
  explícitamente ese `id_crudo`. Para instrumentos reales sin `ruta_json`, devolver `None` y dejar que
  `map_instrumento` degrade a datos de BD (`nombre_archivo`, `tipo_instrumento`, metadatos DC si se
  consultaran).
- Idealmente, hacer que la etapa de estandarización (Bug 3/4) escriba `instrumento_procesado.ruta_json` del
  instrumento real, de modo que `_resolver_por_ruta_json` tome el JSON correcto antes de cualquier fallback.
- Opcional: en `map_instrumento`, cuando no haya JSON, resolver `titulo` desde `metadatos_dc.dc_title`
  (registrado en el paso 3) en vez de solo `nombre_archivo`.

---

## Panorama general: qué está cableado vs. mock/local

| Paso del wizard | Estado | Evidencia |
|---|---|---|
| 1. Archivo (subir) | **Real** | `carga.ts:subirInstrumento` → `POST /instrumentos/upload` (gateway → instrument-service `UploadService.upload`). Devuelve `id_crudo`+`id_instrumento`. |
| 2. Limpieza | **Derivado/local** | No hay endpoint de limpieza. `carga.ts:mapearParseoALimpieza` deriva un reporte del parseo; `duplicados/nulos = 0` (honesto). |
| 3. Dublin Core | **Real (parcial)** | `registrarMetadatos` → `POST /api/metadata/metadata/{id}`; `getMetadatosInit` para pre-poblar. Faltan `source`/`relation`; ignora `date`/`language` (Bug 1). |
| 4. Metadatos del tipo | **Mock/local** | `StepMetadatosTipo` solo alimenta `JsonPreview`/resumen; `guardarInstrumento` es no-op. Sin endpoint ni tabla destino (Bug 2). |
| 5. Vista previa JSON | **Local** | `documento` memo en `UploadWizard`; no se persiste tal cual. |
| 6. KPIs sugeridos | **Real pero inerte** | `proponerKpis` → `POST /vectorizacion/propuestas` (analysis-service directo), pero el useEffect corta por falta de `jsonInstrumento`+`archivoOriginal` → `[]` (Bug 4). |
| 7. Calcular KPIs | **Real** | `prepararCalculo`/`registrarCalculo` → `/kpis/calculo/*` (analysis-service directo). Solo corre si hay KPIs aceptados. |
| 8. Guardar | **Mixto** | `confirmarKpis` (real, si hay `jsonInstrumento`), `registrarCalculo` (real), `guardarInstrumento` (no-op). |

Notas de enrutamiento (de `services/api-gateway/proxy/proxy.py`):
- `/instrumentos/*` → instrument-service :8001 (passthrough).
- `/api/metadata/*` y `/api/enrichment/*` → metadata-service :8003 (passthrough; doble `metadata`
  preservado).
- `/rag/*` → visualization-service :8005.
- **analysis-service NO se proxea**: el frontend lo consume directo vía `ANALYSIS_URL` (`/vectorizacion/*`,
  `/kpis/calculo/*`, espacio vectorial). Coherente con `src/api/carga.ts` (usa `ANALYSIS_URL` para esas
  llamadas).

## Pipeline correcto end-to-end (con el código que EXISTE)

El flujo que el código sembrado presupone, y que el upload real debería completar, es:

1. **Upload** (`UploadService.upload`): guarda crudo + original, crea `instrumento_procesado` (`recibido`).
   *Ya existe.*
2. **Estandarización (FALTA):** convertir `RawTable` → JSON de dominio
   (`instrument.sections[].questions[]` tipificadas, `metadata.*`), escribir
   `instrumento_procesado.ruta_json`, pasar a estado `estandarizado`. Resuelve Bug 3 y la fuente del Bug 5.
3. **Metadatos DC** (`metadata-service` `register_dc`): paso 3 del wizard. *Ya existe* (ajustar campos,
   Bug 1).
4. **Metadatos del tipo (FALTA contrato):** persistir el paso 4 en `metadatos_enriquecidos_*`
   (Bug 2) — hoy no hay endpoint para los campos del formulario.
5. **Vectorización + propuestas** (`ProposalService.propose` → `index_summary` + `search_kpis`): alimentada
   con el JSON (de la etapa 2) + texto original. Puebla `summary_instrument`. Resuelve Bug 4. Requiere la
   colección `kpis` indexada (`/vectorizacion/kpis/reindex`).
6. **Confirmar KPIs** (`EnrichmentService.confirm` vía `/vectorizacion/confirmar`): persiste `kpi_inferido`.
   *Ya existe.*
7. **Cálculo de KPIs** (`/kpis/calculo/*`): valores + semáforo. *Ya existe.*

El eslabón ausente es la **etapa 2 (estandarización que escribe `ruta_json` y produce el JSON de dominio)**;
su ausencia es la causa compartida de los bugs 3, 4 y 5, y el motivo por el que los pasos 4 y 6 quedan
inertes.

---

## Recomendaciones priorizadas (no implementadas aquí)

1. **Bug 5 (rápido, alto impacto):** en `instrumento_query.py`, condicionar el fallback a `storage/raw` a un
   `_seed_map.json` explícito; no mapear `N → inst_{N:02d}` para instrumentos reales. Esto corta de
   inmediato la suplantación por semilla. (Cambio localizado, bajo riesgo.)
2. **Bug 4 (desbloquear KPIs):** Opción B del Bug 4 — construir `jsonInstrumento` desde los DC + metadatos
   del tipo y reutilizar el `archivoOriginal` que el usuario ya sube, para que `proponerKpis` corra.
   Verificar primero que la colección `kpis` esté reindexada.
3. **Bug 1 (contrato DC):** añadir `source`/`relation`, aclarar `fecha`/`idioma` informativos.
4. **Bugs 2 y 3 (estructurales):** requieren la etapa de estandarización y/o un contrato de metadatos
   específicos; planificar como trabajo de backend (nuevos modelos/endpoints), no solo frontend.

### Verificación sugerida para la fase de implementación

- Backend Python: ejecutar la suite del repo (ver `pixel-perfect-pixel/TESTING.md` y los
  `requirements.txt` de cada servicio; p. ej. `pytest` en `services/<svc>` donde existan tests) tras cada
  cambio.
- Frontend: `bun run build` en `pixel-perfect-pixel/` y, si hay suite, `bun test`.
- End-to-end del bug 5: subir un instrumento nuevo y confirmar que `GET /instrumentos` devuelve su
  `nombre_archivo`/DC real y no el título de `inst_01.v1.json`.
- End-to-end del bug 4: tras el fix, confirmar filas nuevas en `tt_rag.documento_vectorizado` /
  colección `summary_instrument` y propuestas no vacías en `/vectorizacion/propuestas`.
