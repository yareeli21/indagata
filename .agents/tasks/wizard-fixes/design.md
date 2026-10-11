# Diseño — Etapa de estandarización + 5 fixes del wizard (Indagata)

Rama: `elotro-back`. Raíz: `C:\Users\yarel\Documents\indagata\indagata`.
Alcance: **diseño**, no implementación. Todos los contratos se fijan contra código real leído
(archivo:símbolo). UI y dominio en español. Cambios de esquema aditivos (`IF NOT EXISTS`). Nunca `push`.
Se conservan intactos: el paso de **cálculo de KPIs** (`/kpis/calculo/*`), la feature **grafo/espacio
vectorial**, y el campo opcional **archivo original** (`archivoOriginal` en `StepArchivo`/`UploadWizard`).

> **Revisión 3.** Este documento incorpora las correcciones a los 5 hallazgos de la **segunda**
> revisión de diseño (`design-review.json`/`design-review.md`, veredicto `CHANGES_REQUESTED` sobre la
> revisión 2). Las respuestas puntuales a cada hallazgo están en §11. Cambios respecto a la revisión 2:
> (a) el enriquecimiento DC/`survey_specific` ya **no muta** el estado de React: se construye una copia
> inmutable `jsonEnriquecido`, se hace `setJsonInstrumento(jsonEnriquecido)` y ese **mismo** objeto es el
> que consume `confirmarKpis` en el paso 8 (Hallazgo 1); (b) el `catch` del `useEffect` de KPIs ahora
> **diferencia** lista vacía (éxito) de error de servicio (503/4xx/5xx) y lo surfacea con `toast.error`;
> el 503 (Chroma/Ollama caídos) se agrega a las tablas de errores y al runbook (Hallazgo 2); (c) se fija
> que `domain_builder` usa el **texto completo** de `ExtractedDocument.text` para documentos (no el
> `text_preview` truncado), que `textoDerivadoDePreguntas` es respaldo **solo tabular**, y que
> `archivoOriginal` se **restringe a texto plano/markdown** antes de enviarlo como `text/markdown`
> (Hallazgo 3); (d) se corrige §5 para reflejar que el input de Derechos ya tiene `maxLength={120}` y no
> requiere cambio (Hallazgo 4); (e) se fija el **orden de `include_router`** del router `specific` en
> `main.py` y que el test de integración afirma que ambas rutas resuelven a su handler (Hallazgo 5).
>
> **Revisión 2 (histórico).** Incorporó las correcciones a los 9 hallazgos de la primera revisión:
> (a) el bloque Dublin Core se escribe en el JSON de dominio con claves `dc:`; (b) la guarda del
> `useEffect` de KPIs dejó de exigir `archivoOriginal`; (c) la ruta del endpoint de metadatos
> específicos se corrigió a `POST /api/metadata/{id}/especificos` porque el gateway **solo** proxea
> `/api/metadata/*` y `/api/enrichment/*` — verificado en `proxy.py`.

---

## 0. Panorama y decisión arquitectónica central

El pipeline sembrado presupone un **JSON de dominio** (`storage/raw/inst_XX.v1.json`) que el flujo de
upload real nunca produce. El `UploadService.upload` (`services/instrument-service/app/services/upload_service.py`)
guarda el archivo respondido + original, lo parsea a `ParsedContent`/`RawTable` y crea
`InstrumentoProcesado(estado="recibido")` **sin `ruta_json`**. De ahí nacen los bugs 3, 4 y 5.

**Decisión:** se añade la **etapa de estandarización DENTRO de `services/instrument-service`** (no es un
microservicio nuevo). Reutiliza el parser existente (`app/parsing/*`), produce el JSON de dominio con el
**esquema exacto del seed**, lo escribe en disco vía el puerto de storage, setea
`instrumento_procesado.ruta_json` y avanza el estado a `estandarizado` (valor ya válido en el
`CheckConstraint` de `InstrumentoProcesado` y mapeado a `"Estandarizado"` en `map_instrumento.py:_ESTADO_MAP`).

La estandarización es un **flujo de dos llamadas** (camino A confirmado por el usuario): el sistema
PROPONE los tipos de pregunta y el investigador los CONFIRMA/CORRIGE antes de persistir el JSON final.

Stack bloqueado (ya en uso en el repo, no se introduce nada nuevo):
- Backend: **Python 3 + FastAPI + SQLAlchemy (ORM `Mapped`)**, Pydantic v2 para schemas, PostgreSQL
  (schema `tt_rag`), Chroma para vectores. `openpyxl`/`pypdf`/`python-docx` ya son dependencias del parser.
- Frontend: **React + TypeScript + TanStack Router + Tailwind (tokens semánticos)**, `bun` como runner.
  HTTP vía `src/api/client.ts` (`API_URL` → gateway :8000, `ANALYSIS_URL` → analysis-service :8002).
- Ruteo: el gateway proxea `/instrumentos/*` passthrough a instrument-service
  (`services/api-gateway/proxy/proxy.py:instrumentos_get/post`), así cualquier endpoint nuevo bajo
  `/instrumentos/...` queda expuesto sin tocar el gateway. `analysis-service` NO se proxea: el frontend lo
  llama directo con `ANALYSIS_URL`. `metadata-service` monta sus routers con `prefix="/api"`
  (`services/metadata-service/main.py`), por eso las rutas tienen doble segmento (`/api/metadata/metadata/...`).

Orden del pipeline corregido:
`upload (recibido)` → **estandarizar/preview** (propone tipos) → **estandarizar** (persiste JSON + tipos
confirmados → `estandarizado`, escribe `ruta_json`) → `metadatos DC` (`metadatos_registrados`) →
`metadatos específicos del tipo` (nuevo contrato) → `propuestas KPI` (vectoriza summary) → `confirmar KPI`
→ `cálculo KPI`.

> Nota de orden de estados: hoy `register_dc` fuerza `estado="metadatos_registrados"`. Como la
> estandarización ocurre ANTES del paso DC en el wizard, el instrumento pasa `recibido → estandarizado →
> metadatos_registrados`. El avance a `metadatos_registrados` NO retrocede nada: `ruta_json` ya quedó
> escrito y `_resolver_por_ruta_json` lo seguirá tomando con prioridad independientemente del `estado`.

---

## 1. Etapa de estandarización (pieza nueva central)

### 1.1 Ubicación y archivos

Todo vive en `services/instrument-service`:

- **Nuevo** `app/standardization/type_detector.py` — heurística de clasificación de tipo de pregunta.
- **Nuevo** `app/standardization/domain_builder.py` — construye el dict del JSON de dominio (esquema seed).
- **Nuevo** `app/services/standardization_service.py` — orquesta: lee el archivo guardado, parsea, detecta
  tipos (preview) o persiste (estandarizar), escribe `ruta_json`, actualiza estado.
- **Nuevo** `app/routers/standardize.py` — endpoints `preview` y `estandarizar`.
- **Nuevo** `app/schemas/estandarizacion.py` — DTOs Pydantic de request/response.
- **Modificar** `app/storage/port.py` + `app/storage/local_backend.py` — añadir `leer(ruta) -> bytes` al
  puerto (hoy solo hay `guardar`/`eliminar`; la estandarización necesita releer el archivo respondido).
- **Modificar** `services/instrument-service/main.py` — `app.include_router(standardize.router)`.

### 1.2 Lectura del archivo respondido (nuevo método del puerto de storage)

`StoragePort` (`app/storage/port.py`) hoy expone solo `guardar`/`eliminar`. La estandarización ocurre en
una llamada posterior al upload, así que necesita releer el archivo persistido desde `raw_data.raw_archivo`.

Contrato nuevo en el puerto:

```python
# app/storage/port.py — añadir a StoragePort
@abstractmethod
def leer(self, ruta: str) -> bytes:
    """Lee el contenido almacenado por su `ruta` (la que se guardó en raw_data).
    Raises: StorageError si no existe o falla la lectura."""
```

Implementación en `LocalStorageBackend` (`app/storage/local_backend.py`): resuelve
`settings.raw_path_abs.parent / ruta` (igual que `eliminar`, que usa `storage_root = raw_path_abs.parent`
y compone `storage_root / ruta`, porque `ruta` tiene forma `raw/<uuid>__name.ext`), valida que quede dentro
de `storage/` (misma defensa en profundidad que `eliminar`) y hace `Path(target).read_bytes()`. Error de
E/S → `StorageError`.

### 1.3 Detección de tipo de pregunta — `type_detector.py` (Bug 3)

Para **instrumentos tabulares** (encuesta), cada columna de datos (no demográfica) se analiza sobre los
valores no vacíos de `RawTable.rows`. Para **documentos** (entrevista/prueba), no hay columnas: cada
"pregunta" se trata como `abierta` (ver §1.4). Heurística (orden de evaluación; primera que acierta gana):

| Tipo detectado (`type` en el JSON) | Regla sobre valores no vacíos de la columna |
|---|---|
| `binaria` | el conjunto de valores distintos (normalizados a minúsculas, sin acentos) ⊆ `{si, sí, no, 0, 1, true, false, verdadero, falso}` y su cardinalidad ≤ 2 |
| `likert` | **todos** los valores son enteros en un rango contiguo `1..N` con **preferencia** `N ≤ 7` (se captura `scale_min=1`, `scale_max=N`). El `N ≤ 7` es una **preferencia del detector** (señal típica de Likert), **no** una cota de validación: el investigador puede confirmar escalas mayores en el paso de corrección (ver §1.7, Hallazgo 6) |
| `numerica_continua` | **todos** los valores parsean a número (int/float) y NO cae en `likert` (rango fuera de 1..7, o floats, o enteros con muchos distintos) |
| `opcion_multiple` | conjunto cerrado de etiquetas de texto repetidas: nº de valores distintos ≤ `min(12, 0.5 * nº_respuestas)` y ≥ 2 (se capturan las `options` = etiquetas distintas ordenadas por frecuencia) |
| `abierta` | ninguna de las anteriores (texto libre, alta cardinalidad, o columna de documento) |

Reglas de desempate y bordes:
- Columna sin valores no vacíos → `abierta` con `confianza` baja (ver DTO) y nota.
- `likert` tiene prioridad sobre `numerica_continua` (un 1..5 es Likert, no continuo).
- `binaria` tiene prioridad sobre `opcion_multiple` y `likert` cuando el conjunto es exactamente binario.
- Normalización de celdas: ya la hace el parser (`header_utils.normalize_cell`); el detector solo recorta y
  compara en minúsculas sin acentos para la familia binaria.
- La detección **no** reordena ni elimina columnas; produce **una propuesta por columna/pregunta**,
  preservando el orden del `RawTable.headers`.

Salida del detector: lista de `TipoPreguntaDetectado { question_id, text, type, options?, scale_min?,
scale_max?, confianza, es_demografica }`.

- `question_id`: `q1, q2, …` por orden de columna (estable).
- `text`: el `header` normalizado de la columna (para documentos, un título derivado del párrafo/pregunta).
- `es_demografica`: `true` si el header coincide (normalizado) con un diccionario corto de demográficos
  conocidos (`edad, genero, género, carrera, semestre, promedio, empleo, horas_estudio,
  situacion_economica, apoyo_familiar`). Las columnas demográficas **no** se vuelven preguntas del
  instrumento: alimentan `respondents[].demographics` (ver §1.4). El investigador puede, en el paso de
  confirmación, reclasificar una columna demográfica como pregunta y viceversa (campo editable).
- `confianza`: `"alta" | "media" | "baja"` (heurística: binaria/likert con rango perfecto = alta;
  opcion_multiple = media; abierta por descarte o columna vacía = baja). Es informativa para la UI.

### 1.4 Construcción del JSON de dominio — `domain_builder.py`

Produce un dict con el **esquema exacto** de `storage/raw/inst_01.v1.json` (verificado leyendo el seed).
Claves y su origen:

```jsonc
{
  "instrument_id": "upload_<id_crudo>",        // prefijo inequívoco; NO colisiona con slugs sembrados (ver §5 y Hallazgo 7)
  "schema_version": "1.0",
  "instrument": {
    "title": "<dc_title | nombre_archivo>",    // DC aún no registrado en este punto → nombre_archivo
    "objective": "",                           // se completa en pasos de metadatos; opcional
    "dimensions_explored": [],
    "sections": [
      {
        "section_id": "s1",
        "name": "Reactivos del módulo",        // mismo literal que el seed; irrelevante para consumidores (ver nota de política)
        "questions": [
          { "question_id": "q1", "text": "...", "type": "likert",
            "options": ["..."], "scale_min": 1, "scale_max": 5 }
          // 'options' solo en opcion_multiple/binaria/likert; 'scale_*' solo en likert
        ]
      }
    ]
  },
  "metadata": {
    "dublin_core": {},        // vacío al estandarizar; se escribe con claves dc: al registrar DC (ver §1.4bis y Hallazgo 1)
    "survey_specific": {}     // se puebla en el paso de metadatos específicos
  },
  "design_reference": { "kpi_hints": [], "note": "..." },
  "respondents": [            // SOLO tabular: una fila -> un respondente
    { "respondent_id": "r_0001", "demographics": { "...": "..." },
      "answers": { "q1": 4, "q3": "15-29", ... } }
  ]
}
```

Decisiones de construcción:
- **Tipo de pregunta por `type`** usa el vocabulario estandarizado del detector (`binaria`,
  `opcion_multiple`, `likert`, `numerica_continua`, `abierta`). Esto es intencional y NO rompe el consumo
  existente: `map_instrumento._extraer_reactivos` solo cuenta `len(questions)`, y `metadata_extractor` NO
  lee `questions[].type` (lee `dublin_core` + `survey_specific`). El seed usa literales más específicos
  (`likert_1_5`, `multiple_choice`); el nuevo vocabulario es el acordado en el camino A y convive sin
  afectar a ningún consumidor actual.
- `respondents` se arma **solo para tabular**: cada fila de `RawTable.rows` → un `respondent` con
  `respondent_id = f"r_{i:04d}"`, `demographics` = columnas marcadas `es_demografica`, y `answers` =
  `{question_id: valor}` para las columnas-pregunta. Valores Likert/numéricos se convierten a `int`/`float`
  cuando el `type` lo permite; el resto queda como `str`; celda vacía → `null`.
- Para **documentos** (entrevista/prueba): `respondents = []`, y `questions` se deriva del texto parseado.
  Mínimo viable: una sola `question` `abierta` cuyo `text` es el **texto completo** extraído, sin segmentar
  (el `document_parser` no segmenta). **Fuente fijada (Hallazgo 3 — rev. 3):** el `domain_builder` usa
  `ExtractedDocument.text` **íntegro** (verificado en `app/parsing/document_parser.py`: `read_document`
  devuelve el campo `text` con el documento completo), **NO** el `text_preview` truncado del
  `UploadResponse`. Razón: la etapa de estandarización vuelve a parsear el archivo respondido desde
  `raw_data.raw_archivo` (§1.2) e invoca `read_document` directamente, por lo que tiene acceso al texto
  completo; truncar al preview degradaría el summary para documentos. Si en una iteración futura se
  segmenta el documento en preguntas individuales, cada párrafo/pregunta sería una `question` `abierta`
  propia; hoy es una sola. `metadata.survey_specific` queda para el paso de metadatos. Esto es suficiente
  para que el summary se construya (usa metadatos + instrumento original en §4).
- `instrument_id`: se usa `f"upload_{id_crudo}"` (prefijo inequívoco). El campo es **puramente
  informativo**; el id canónico de resolución es `id_crudo` y la de-colisión real contra los slugs
  sembrados la garantiza `_seed_map.json` explícito (fix del Bug 5, §3), no el formato del `instrument_id`.
  Se usa `upload_` en vez de `inst_` para evitar cualquier ambigüedad con los slugs `inst_XX` del seed
  (p. ej. `id_crudo = 11` daría `inst_11`, idéntico al slug sembrado; `upload_11` no colisiona). Ver
  Hallazgo 7.

**Claves del seed deliberadamente OMITIDAS** (el objetivo es un **superconjunto compatible de lectura**,
no una copia byte a byte del seed): se **omiten** `synthetic_profiles` y `respondents[].profile_id`.
Razón: son artefactos de **datos sintéticos sembrados** (perfiles generados para la demo) que no aplican a
un upload real; ningún consumidor leído los requiere (`map_instrumento` y `metadata_extractor` no los
tocan — verificado). No se emiten (ni como `[]` ni como clave vacía). El resto de claves del esquema del
seed (`instrument_id`, `schema_version`, `instrument.{title,objective,dimensions_explored,sections}`,
`metadata.{dublin_core,survey_specific}`, `design_reference`, `respondents`) **sí** se emiten.
`section.name` se fija al literal `"Reactivos del módulo"` (el mismo del seed); su valor es irrelevante
para los consumidores (nadie lo lee), se fija solo por consistencia visual con el seed.

### 1.4bis Escritura del bloque Dublin Core en el JSON de dominio (Hallazgo 1)

Los dos consumidores reales leen Dublin Core **desde el JSON de dominio**, con claves **prefijadas `dc:`**
(verificado):
- `analysis-service/app/vectorization/config/constants.py:DUBLIN_CORE_KEYS = ("dc:title", "dc:subject",
  "dc:description", "dc:coverage")`, recorridas por `metadata_extractor.extract_key_metadata` sobre
  `data["metadata"]["dublin_core"]`.
- `instrument-service/app/services/map_instrumento.py` lee `dc:title`, `dc:coverage`, `dc:date`,
  `dc:subject` del JSON.

Al estandarizar, `metadata.dublin_core` queda **vacío** (el paso DC aún no ocurrió). **Decisión fijada
(vía única):** el **cliente** (`UploadWizard.tsx`) enriquece `metadata.dublin_core` con claves `dc:` a
partir del estado `dc` del wizard, **antes** de llamar `proponerKpis` (paso 6). Se elige la vía cliente (no
reescribir el JSON en disco desde el backend) porque: (a) el `jsonInstrumento` que viaja a
`/vectorizacion/propuestas` ya se arma en el cliente, así que el summary recibe el DC completo sin otra
llamada de red; (b) el DC se registra en el paso 3 (posterior a estandarizar), de modo que escribirlo en el
JSON en `/estandarizar` sería prematuro; (c) `/vectorizacion/propuestas` lee el `archivo_json` del
multipart, no el de disco, por lo que basta enriquecer el objeto en memoria.

**Regla de inmutabilidad (Hallazgo 1 — rev. 3).** `jsonInstrumento` es estado de React
(`const [jsonInstrumento, setJsonInstrumento] = useState<Record<string, unknown> | null>(null)`,
verificado en `UploadWizard.tsx`). **NO** se muta en sitio (`jsonInstrumento.metadata = ...` es un
antipatrón: no dispara re-render ni actualiza la referencia que leen `confirmarKpis`/el `useEffect`,
dejando el DC fuera del JSON que se persiste en el dominio de KPIs). En su lugar se construye una **copia
nueva** `jsonEnriquecido`, se persiste con `setJsonInstrumento(jsonEnriquecido)`, se deriva el `Blob`
`archivoJson` **de esa misma copia**, y se especifica que `confirmarKpis` (paso 8) consume el **mismo**
`jsonEnriquecido` (que ya vive en estado tras el `setJsonInstrumento`):

```ts
// UploadWizard.tsx — helper puro que enriquece sin mutar (reutilizable por el useEffect y guardar):
function enriquecerJson(
  base: Record<string, unknown>,
  dc: DublinCore,
  surveyEspecifico: Record<string, unknown>,
): Record<string, unknown> {
  const dcJson: Record<string, string> = {};
  if (dc.titulo)      dcJson["dc:title"]       = dc.titulo;
  if (dc.tema)        dcJson["dc:subject"]     = dc.tema;        // metadata_extractor coacciona a texto
  if (dc.descripcion) dcJson["dc:description"] = dc.descripcion;
  if (dc.cobertura)   dcJson["dc:coverage"]    = dc.cobertura;
  const metaPrev = (base.metadata as Record<string, unknown>) ?? {};
  const surveyPrev = (metaPrev.survey_specific as Record<string, unknown>) ?? {};
  return {
    ...base,
    metadata: {
      ...metaPrev,
      dublin_core: dcJson,                               // claves dc:
      survey_specific: { ...surveyPrev, ...surveyEspecifico },
    },
  };
}

// En el useEffect de KPIs (paso 6), antes de proponerKpis:
const jsonEnriquecido = enriquecerJson(jsonInstrumento, dc, surveyEspecifico);
setJsonInstrumento(jsonEnriquecido);                     // ← persiste en estado para confirmarKpis (paso 8)
const archivoJson = new Blob([JSON.stringify(jsonEnriquecido)], { type: "application/json" });
proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal: original, tipo });
```

Como `setJsonInstrumento(jsonEnriquecido)` actualiza el estado, el `guardar()` del paso 8
(`confirmarKpis({ ..., jsonInstrumento })`, verificado en `UploadWizard.tsx`/`carga.ts`) lee **la copia
enriquecida con DC**, no una versión sin DC. Así el JSON persistido en el dominio de KPIs lleva Dublin Core,
cerrando el Hallazgo 1 por completo (ya no "parcialmente sin resolver").

> Nota de orden de render: al hacer `setJsonInstrumento` dentro del `useEffect` y usar `jsonEnriquecido`
> (variable local) para el `Blob` del mismo tick, el `proponerKpis` de esa ejecución ya trabaja con el
> objeto correcto sin esperar al re-render. El `setState` solo garantiza que el **siguiente** lector
> (`guardar`) vea la copia enriquecida. `jsonInstrumento` sigue en el array de deps del `useEffect`; para
> evitar un re-disparo redundante tras el `setState`, la guarda `if (paso !== 6 || sugeridos || ...)` ya
> corta cuando `sugeridos` dejó de ser `null` (una sola propuesta por entrada al paso).

**El conjunto de claves de `survey_specific` VARÍA POR TIPO (resuelve revisión 3, MEDIUM #1).**
`metadata_extractor.extract_key_metadata` lee `CAMPOS_ESPECIFICOS_POR_TIPO[tipo]`
(en `analysis-service/app/vectorization/config/constants.py`), que es DISTINTO por tipo:
- **Encuesta**: `constructo_principal`, `dimensiones`, `palabras_clave`, `carrera`, `notas_contextuales`, `notas_interpretacion`.
- **Entrevista**: `objetivo`, `metodologia`.
- **Prueba estandarizada**: `unidad_de_aprendizaje`, `taxonomia_bloom`, `objetivo_de_evaluacion`, `competencias`.

Por eso `enriquecerJson` debe recibir un `surveyEspecifico` armado según el tipo del instrumento, con un
mapeo `CLAVES_SURVEY_POR_TIPO` que sea **espejo** de `CAMPOS_ESPECIFICOS_POR_TIPO`. Si solo se poblaran los
campos de encuesta, para entrevista y prueba el summary se armaría únicamente con Dublin Core y las
propuestas de KPI se degradarían (reabriendo el Hallazgo 1 de la revisión 2 para esos tipos). El paso 4
(`StepMetadatosTipo`) ya recoge los campos por tipo (§6, §7); de ahí sale el `surveyEspecifico` del tipo
correspondiente.

> **Omisión deliberada de `dc:rights`/`dc:source`/`dc:relation` del bloque DC del summary (NIT #4):**
> `enriquecerJson` solo escribe `dc:title`/`dc:subject`/`dc:description`/`dc:coverage` porque
> `DUBLIN_CORE_KEYS` (lo que `metadata_extractor` lee) contiene exactamente esas cuatro. Rights/source/
> relation SÍ se persisten, pero vía el registro DC del paso 3 (`metadatos_dc`), no en el summary vectorial.

`surveyEspecifico` son los campos del paso 4 que `metadata_extractor` lee (`constructo_principal`,
`dimensiones`, `palabras_clave`, `carrera`, `notas_contextuales`, `notas_interpretacion`), ver §6.2. Con
esto el summary recibe **Dublin Core + survey_specific + texto del original**, cerrando la degradación de
la calidad de propuestas que el Hallazgo 1 señaló. `map_instrumento` seguirá tomando el título del JSON de
disco (que al estandarizar aún no tiene DC); eso lo cubre el fallback a `nombre_archivo` y la mejora
opcional de §3 (título desde `dc_title`).

### 1.5 Persistencia del JSON y de `ruta_json`

El JSON se escribe vía el puerto de storage (misma abstracción que los crudos), con nombre
`inst_<id_crudo>.estandarizado.v1.json`. `StoredRef.ruta` resultante (p. ej. `raw/<uuid>__inst_5...json`)
se guarda en `instrumento_procesado.ruta_json`.

> `_resolver_por_ruta_json` (`instrumento_query.py`) resuelve rutas relativas contra `settings.PROJECT_ROOT`.
> `raw_path_abs` apunta a `storage/raw`, y el prefijo de la ruta del backend local es `raw/...` relativo a
> `storage/`. **Invariante a respetar:** la ruta persistida en `ruta_json` debe ser resoluble por
> `_resolver_por_ruta_json`. Como esa función hace `settings.PROJECT_ROOT / ruta_json`, se persiste la ruta
> **relativa a `storage/`** con el prefijo `storage/` incluido (es decir `storage/raw/<uuid>__...json`), de
> modo que `PROJECT_ROOT / "storage/raw/..."` apunte al archivo real. El `standardization_service` compone
> esta ruta a partir de `StoredRef.ruta` anteponiendo el nombre del directorio `storage`
> (`settings.raw_path_abs.parent.name`). Esta normalización se hace en un único punto
> (`standardization_service._ruta_relativa_proyecto`) y se cubre con un test unitario (§8).

Transición de estado: tras escribir `ruta_json`, `estado = "estandarizado"`,
`fecha_procesamiento = now()`. Idempotencia: ver §1.7 (reestandarizar).

### 1.6 Contrato EXACTO de endpoints

Ambos bajo el router `prefix="/instrumentos"` (se exponen por el passthrough del gateway). `{id}` = `id_crudo`
(id canónico del frontend, coherente con `list.py`). Auth: `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)`
(igual que upload/list).

**(A) Previsualizar tipos detectados — no persiste nada**

```
POST /instrumentos/{id}/estandarizar/preview
→ 200 OK
```
Request: sin body (lee el archivo respondido desde `raw_data.raw_archivo`). `tipo_instrumento` del
preview/estandarizar es **siempre** `raw_data.tipo_instrumento` tal cual, uno de
`encuesta | entrevista | prueba_estandarizada` (coherente con el enum `TipoInstrumento` del
analysis-service; para la familia documento viene `entrevista`/`prueba_estandarizada`, ver Hallazgo 9).
Response (`PreviewResponse`):
```jsonc
{
  "id_crudo": 5,
  "tipo_instrumento": "encuesta",   // = raw_data.tipo_instrumento (encuesta|entrevista|prueba_estandarizada)
  "preguntas": [
    { "question_id": "q1", "text": "¿Qué tan claro...?", "type": "likert",
      "options": ["1","2","3","4","5"], "scale_min": 1, "scale_max": 5,
      "confianza": "alta", "es_demografica": false }
    // ...
  ],
  "n_respondentes_detectados": 250,     // filas de datos (tabular); 0 para documento
  "notas": ["Columna 'q9' sin valores: clasificada como abierta (confianza baja)."]
}
```

**(B) Estandarizar con tipos confirmados — persiste el JSON y avanza estado**

```
POST /instrumentos/{id}/estandarizar
→ 200 OK
```
Request (`EstandarizarRequest`): el investigador envía los tipos CONFIRMADOS/CORREGIDOS (lista completa; el
backend NO reusa la detección: usa lo que llega, re-derivando `respondents.answers` según esos tipos):
```jsonc
{
  "preguntas": [
    { "question_id": "q1", "text": "¿Qué tan claro...?", "type": "likert",
      "scale_min": 1, "scale_max": 5, "es_demografica": false }
    // opciones/escala son opcionales; si faltan en un tipo que las requiere, el backend las recalcula
    // desde los datos (p. ej. options de opcion_multiple) de forma best-effort.
  ]
}
```
Response (`EstandarizarResponse`):
```jsonc
{
  "id_crudo": 5,
  "id_instrumento": 7,
  "estado": "estandarizado",
  "ruta_json": "storage/raw/<uuid>__inst_5.estandarizado.v1.json",
  "json_instrumento": { /* el dict de dominio completo (§1.4) */ },
  "mensaje": "Instrumento estandarizado."
}
```

`json_instrumento` se devuelve en el cuerpo para que el wizard lo tenga disponible y lo reenvíe a
`proponerKpis` sin otra llamada (resuelve Bug 4; ver §4).

### 1.7 Manejo de errores (concreto, por operación)

| Operación | Condición de fallo | ¿Recuperable? | Respuesta al caller | Log |
|---|---|---|---|---|
| Resolver instrumento | `raw_data` con `{id}` no existe | fatal (de esa petición) | `404` "Instrumento no encontrado." | no |
| Leer archivo respondido | `StorageError` (archivo ausente/ilegible) | fatal | `422` "No se pudo leer el archivo del instrumento." | `logger.exception` (WARNING) |
| Parsear | `ParseError` del parser | fatal | `422` "No se pudo parsear el instrumento: {detalle}." | WARNING |
| Detección de tipos | columna vacía / tipo ambiguo | **recuperable** | se degrada a `abierta` + nota en `notas` (no es error HTTP) | DEBUG |
| `/estandarizar` sin preguntas | `preguntas` vacío o inconsistente con headers | fatal | `422` con detalle del desajuste (nº columnas vs nº preguntas) | WARNING |
| Escribir JSON | `StorageError` al `guardar` | fatal | `500` "No se pudo guardar el JSON estandarizado." + NO cambia estado ni `ruta_json` | `logger.exception` (ERROR) |
| Persistir en BD | `SQLAlchemyError` | fatal | rollback; se **elimina** el JSON ya escrito (sin huérfanos, patrón de `upload_service`); `500` | ERROR |
| Reestandarizar | ya existe `ruta_json` | recuperable | `200`: se **sobrescribe** el JSON y se re-persiste `ruta_json` (la estandarización NO es inmutable, a diferencia del registro DC). Si el estado ya avanzó a `vectorizado`, se responde `409` "El instrumento ya fue vectorizado; no puede reestandarizarse." | INFO |

Validación de entrada (`/estandarizar`): `preguntas` es requerido, lista no vacía; cada ítem:
`question_id` str requerido; `text` str requerido; `type` ∈ `{binaria, opcion_multiple, likert,
numerica_continua, abierta}` (422 si otro valor); `options` lista de str opcional; `es_demografica` bool
opcional (default `false`).

**Validación de escala (Hallazgo 6).** `scale_min`/`scale_max` enteros, solo relevantes si
`type == likert`. La **validación de entrada** acepta cualquier escala que el investigador confirme:
`1 ≤ scale_min < scale_max ≤ 100` (tope amplio defensivo contra entradas absurdas, no una regla de
negocio). El `N ≤ 7` del detector (§1.3) es solo una **preferencia de detección**, no se aplica aquí: el
investigador puede declarar 1..10 o 0..10 y se acepta. Si `scale_min`/`scale_max` faltan en un `likert`, el
backend los recalcula desde los datos (best-effort); si vienen pero violan `1 ≤ min < max ≤ 100`, 422.

**Validación de correspondencia pregunta↔header (Hallazgo 4).** Se valida por **correspondencia de
nombres**, no por conteo:
- Cada `pregunta` enviada (identificada por su `text`/`question_id` que mapea al header normalizado del
  `RawTable`) debe corresponder a un header existente del `RawTable` tras normalización. Si una pregunta
  referencia un header que **no existe** en el `RawTable` → **422** con el nombre ofensor.
- Los headers del `RawTable` **no referenciados** por ninguna pregunta ni marcados `es_demografica` se
  **ignoran** y se registran en `notas` (no es 422). Esto cubre columnas como `respondent_id`/`profile_id`
  del seed, que no son ni pregunta ni demográfica conocida.
- Las columnas marcadas `es_demografica` alimentan `respondents[].demographics` y no cuentan como preguntas
  faltantes.
- El investigador puede reclasificar una columna demográfica↔pregunta (§1.3); la validación opera sobre lo
  que llega en el request, así que la reclasificación es consistente por construcción.
- **Headers duplicados tras normalizar**: si dos headers normalizan al mismo nombre, se desambiguan por
  posición (sufijo `__2`, `__3`, …) al construir el mapa header→columna, y se añade una nota; una pregunta
  solo puede mapear a uno de ellos. No es 422 salvo que el nombre resultante no exista.

### 1.8 Invariantes y quién los dueña

- **El esquema del JSON de dominio** lo dueña `domain_builder.py`: es el único punto que serializa a la
  forma del seed. Razón: centralizar evita divergencias con los consumidores (`map_instrumento`,
  `metadata_extractor`).
- **La resolución del JSON correcto por instrumento** la dueña `instrumento_query.resolver_json_por_id_crudo`
  (prioridad a `ruta_json`). La estandarización garantiza el precondición (escribe `ruta_json`), pero no
  cambia la prioridad de resolución.
- **El vocabulario de tipos** lo dueña el `type_detector` + validación del endpoint `/estandarizar`
  (lista cerrada). Es la frontera donde el input del investigador se valida.

---

## 2. Regla de embedding / recuperación (confirmada con el usuario)

El summary que se vectoriza usa **solo el TEXTO de las preguntas + metadatos**, NUNCA el tipo de respuesta.
Esto ya es cierto en el código y se **preserva** explícitamente:

- `summary_builder.build_summary` arma el texto con `metadatos` (de `metadata_extractor`) + el instrumento
  original (texto). No recibe ni usa `questions[].type`.
- `metadata_extractor.extract_key_metadata` lee `metadata.dublin_core` + `metadata.survey_specific` +
  `respondents[].demographics.carrera`. **No** lee `questions[].type`.

Decisión de diseño fijada: el `type` detectado es **metadato para análisis cuantitativo posterior**
(`likert` → media; `binaria` → proporción; `opcion_multiple`/categórica → frecuencia; `numerica_continua`
→ agregado) y vive en `instrument.sections[].questions[].type`. **No** debe inyectarse en el summary ni en
el embedding. Cualquier cambio futuro al summary debe respetar esta separación: el embedding depende del
contenido semántico (preguntas + metadatos), no del formato de respuesta. El cálculo real de KPIs
(`/kpis/calculo/*`) deriva variables de la fórmula del KPI, no del `type` de pregunta — se conserva intacto.

---

## 3. Bug 5 — El listado muestra la semilla en vez del upload real

Causa raíz confirmada: `instrumento_query._slug_por_id_crudo` cae a `f"inst_{id_crudo:02d}"` cuando no hay
`_seed_map.json`, y `_resolver_fallback_raw` carga `storage/raw/inst_01.v1.json`, secuestrando la fila real
`id_crudo=1` con la semilla del mismo índice.

**Fix (archivo: `services/instrument-service/app/services/instrumento_query.py`):**

El código real de `_slug_por_id_crudo` **ya consulta `_seed_map.json` primero** y solo cae al patrón
directo si no hay mapeo (verificado — Hallazgo 3):

```python
# ESTADO ACTUAL (real):
def _slug_por_id_crudo(id_crudo: int) -> str | None:
    seed_map = _cargar_seed_map()
    for inst, cid in seed_map.items():
        if cid == id_crudo:
            return inst
    if id_crudo >= 1:                      # ← ÚNICO cambio: eliminar estas dos líneas
        return f"inst_{id_crudo:02d}"
    return None
```

1. **Eliminar únicamente** las dos líneas del `if id_crudo >= 1: return f"inst_{id_crudo:02d}"`,
   **conservando intacta** la consulta a `_seed_map.json` (que ya existe). Resultado:

```python
# DESPUÉS del fix:
def _slug_por_id_crudo(id_crudo: int) -> str | None:
    seed_map = _cargar_seed_map()
    for inst, cid in seed_map.items():
        if cid == id_crudo:
            return inst
    return None   # sin mapeo explícito → sin fallback a semilla
```

2. Con esto, para un upload real sin `ruta_json`, `resolver_json_por_id_crudo` devuelve `None`, y
   `map_instrumento.mapear_instrumento` degrada a datos de BD: `titulo` cae a `nombre_archivo` (ya es el
   comportamiento de `_extraer_titulo` cuando no hay `instrument.title`/`dc:title`), `tipo` desde
   `raw_data.tipo_instrumento`, `estado` desde `instrumento_procesado.estado`, `kpis = []`.

3. **Mejora de degradación (opcional pero recomendada, en `map_instrumento.py`):** cuando no hay JSON,
   resolver `titulo` desde `metadatos_dc.dc_title` si ya se registró el paso DC. Esto requiere que
   `list.py` consulte `MetadatosDC` por `id_crudo` y lo pase a `mapear_instrumento`. Se marca **opcional**
   porque: (a) una vez que la estandarización escribe `ruta_json`, `_resolver_por_ruta_json` toma el JSON
   real y el título sale de `instrument.title`, cubriendo el caso principal; (b) añadir la consulta a
   `MetadatosDC` toca la firma de `mapear_instrumento` y el router. **Backlog** salvo que el QA del Bug 5
   muestre títulos poco informativos (nombre de archivo) antes de estandarizar.

4. Una vez estandarizado, `_resolver_por_ruta_json` toma el JSON real primero (ya es el orden actual), así
   que el fix de fallback y la etapa de estandarización se refuerzan mutuamente.

**Riesgo/compatibilidad:** los instrumentos **sembrados** dependen hoy del fallback directo. Para no
romperlos, la estandarización/seed debe apoyarse en `_seed_map.json`. Decisión: el script de seed
(`services/instrument-service/scripts/seed_demo.py`) debe **escribir/mantener `storage/raw/_seed_map.json`**
con el mapeo `{"inst_01": <id_crudo>, ...}` real tras sembrar (cambio aditivo, no destructivo). Si el seed
ya corrió sin generar el mapa, se documenta regenerarlo. Así los seeds siguen resolviéndose por el mapa
explícito y los uploads reales dejan de ser secuestrados.

---

## 4. Bug 4 — Sin KPIs recomendados → sin cálculo

Causa raíz confirmada: el `useEffect` del paso de KPIs en `UploadWizard.tsx` corta con
`if (!jsonInstrumento || !archivoOriginal) { setSugeridos([]); return; }`, y en el upload puro ambos son
`null`. `index_summary` solo corre dentro de `ProposalService.propose` (vía `POST /vectorizacion/propuestas`),
que exige `archivo_json` + `instrumento_original`.

**Fix:** la etapa de estandarización (§1) ahora produce el JSON de dominio y lo devuelve en
`EstandarizarResponse.json_instrumento`. El wizard lo guarda en `jsonInstrumento`. El `archivoOriginal` ya
lo sube el usuario (campo existente en `StepArchivo`). Con ambos presentes, el `useEffect` ejecuta
`proponerKpis` real.

Cambios en `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`:

1. Tras `/estandarizar` (nuevo paso, §6), hacer `setJsonInstrumento(resp.json_instrumento)`.
2. **Reescribir la guarda** del `useEffect` para que exija **solo** `jsonInstrumento` y derive el original
   cuando no hay original de texto plano (Hallazgo 2 de la **primera** revisión — la guarda vieja
   `if (!jsonInstrumento || !archivoOriginal)` era incompatible con el fallback: cuando faltaba el original
   hacía `setSugeridos([]); return;` y el fallback nunca corría). Código real de hoy (verificado,
   `UploadWizard.tsx` ~L131-152): la guarda es `if (!jsonInstrumento || !archivoOriginal) {
   setSugeridos([]); return; }`. Nueva forma:

```ts
if (!jsonInstrumento) { setSugeridos([]); return; }
const original = originalDeTextoPlano
  ?? new Blob([textoDerivadoDePreguntas(jsonInstrumento)], { type: "text/markdown" });
const jsonEnriquecido = enriquecerJson(jsonInstrumento, dc, surveyEspecifico); // §1.4bis, sin mutar
setJsonInstrumento(jsonEnriquecido);                                           // persiste para confirmarKpis
const archivoJson = new Blob([JSON.stringify(jsonEnriquecido)], { type: "application/json" });

proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal: original, tipo })
  .then((lista) => { if (!cancelado) setSugeridos(lista); })
  .catch((e) => {
    if (cancelado) return;
    const status = (e as { status?: number })?.status;      // `pedir`/`client.ts` adjunta `status`
    if (status === 503) {
      toast.error(
        "El servicio de vectorización no está disponible. Verifica que Chroma y Ollama estén " +
        "arriba y que la colección de KPIs esté reindexada (POST /vectorizacion/kpis/reindex).",
      );
    } else {
      toast.error(e instanceof Error ? e.message : "No se pudieron proponer KPIs.");
    }
    setSugeridos([]);   // lista vacía SOLO como estado terminal tras surfacar el error
  });
```

   La diferencia clave respecto a la revisión 2 (Hallazgo 2): el `catch` **ya no silencia** cualquier
   error con `setSugeridos([])`. `ProposalService.propose` (verificado en
   `services/analysis-service/app/vectorization/services/proposal_service.py`) lanza **503**
   (`SERVICE_UNAVAILABLE`, "Servicio de vectorización no disponible") cuando Chroma o los embeddings
   fallan — **no** 422. Dado el historial del usuario (CUDA/arranque del stack, mensajes 3-5), este es el
   escenario más plausible de "0 KPIs". Una lista vacía legítima (summary indexado pero sin KPIs cercanos)
   sigue produciendo `sugeridos = []` **sin** toast; un 503/4xx/5xx produce un toast con instrucciones. Así
   el investigador distingue "no hay KPIs parecidos" de "el servicio está caído".

   Antes de construir `archivoJson` se enriquece el JSON vía `enriquecerJson` (copia inmutable, §1.4bis,
   Hallazgo 1). La dependencia `archivoOriginal` del array de deps del `useEffect` se conserva (para
   recomputar si el usuario lo sube después).
3. `proponerKpis` ya existe en `carga.ts` y manda `archivo_json` (Blob JSON) + `instrumento_original`
   (Blob markdown) + `tipo_instrumento` + `id_instrumento`. **`id_instrumento` debe ser `idInstrumento`**
   (PK de `instrumento_procesado`), que es lo que el endpoint `/vectorizacion/propuestas` espera (`Form
   id_instrumento` → `index_summary(id_instrumento, ...)`). Ya se pasa así en el wizard; se mantiene.

**Fuente del "instrumento original" (texto):** `/propuestas` exige `instrumento_original`, que
`build_summary` trata como `str` (texto). `carga.ts:proponerKpis` fuerza
`new Blob([instrumentoOriginal], { type: "text/markdown" })` (verificado), es decir, **asume texto plano**.
De ahí dos reglas fijadas (Hallazgo 3 — rev. 3):

- **(preferida, solo texto plano/markdown)** usar el `archivoOriginal` que el usuario sube. El usuario
  confirmó (mensaje 8) que lo ocupará; es la fuente primaria. **Restricción:** `archivoOriginal` debe ser
  texto plano/markdown. `StepArchivo` debe **restringir el `accept`** del input de archivo original a
  `.md,.txt` (y validar la extensión al seleccionarlo), porque un `.pdf`/`.docx` **binario** enviado como
  `text/markdown` inyectaría bytes basura en el summary. Si el usuario adjunta un binario, se rechaza en el
  cliente con un mensaje claro y se cae al respaldo. (No se parsea PDF/DOCX en el cliente; eso sería trabajo
  del backend en una iteración futura y está fuera de alcance.) `originalDeTextoPlano` en el snippet es el
  `archivoOriginal` **ya validado** como texto; si no pasó la validación, es `null` y se usa el respaldo.
- **(respaldo, SIEMPRE disponible — solo tabular)** si no hay `archivoOriginal` de texto, se construye en
  el cliente un Blob de texto con una línea por `question.text` del `json_instrumento` (función
  `textoDerivadoDePreguntas`:
  `jsonInstrumento.instrument.sections.flatMap(s => s.questions).map(q => q.text).join("\n")`). Este
  respaldo aplica a **tabular** (encuesta), donde las `question.text` son los enunciados. Para
  **documentos** (entrevista/prueba), el `json_instrumento` ya contiene una sola `question` `abierta` cuyo
  `text` es el **texto completo** del documento (§1.4), de modo que `textoDerivadoDePreguntas` devuelve ese
  texto íntegro — coherente y sin doble fuente ambigua. Así `build_summary` siempre tiene texto y
  `index_summary` corre. **No** se inventa endpoint nuevo. Esto respeta la regla de §2 (solo texto de
  preguntas + metadatos, nunca el `type`).

**Prerrequisito operativo (documentado, no código del wizard):** la colección Chroma `kpis` debe estar
reindexada vía `POST /vectorizacion/kpis/reindex` (endpoint real en `routers/vectorizacion.py:reindexar_kpis`),
o `search_kpis` no devuelve candidatos aunque el summary sí se indexe. Se documenta como paso de operación
en el runbook (y en `arrancar.ps1` si aplica); no se dispara desde el wizard.

**Manejo de errores de `proponerKpis` (Hallazgo 2 — rev. 3):**

| Resultado de `/vectorizacion/propuestas` | Significado | UI (cliente) | Log |
|---|---|---|---|
| `200` con `propuestas: []` | summary indexado, pero sin KPIs cercanos | `setSugeridos([])`, **sin** toast; el paso muestra "sin KPIs recomendados" | no |
| `200` con `propuestas: [...]` | éxito normal | `setSugeridos(lista)` | no |
| `422` (summary vacío / JSON inválido / tipo inválido) | insumos mal formados | `toast.error(e.message)` + `setSugeridos([])` | el backend ya loguea |
| **`503`** (Chroma/embeddings/Ollama caídos) | servicio de vectorización no disponible | `toast.error` con instrucciones (levantar Chroma/Ollama + reindexar `kpis`) + `setSugeridos([])` | `ProposalService` ya hace `logger.exception` |
| Error de red / `5xx` genérico | fallo de transporte o servicio | `toast.error(e.message)` + `setSugeridos([])` | — |

**Runbook — causa #1 de "0 KPIs recomendados":** el **servicio de vectorización caído (503)**, no solo la
falta de reindex. Secuencia de diagnóstico: (1) ¿Chroma y Ollama están arriba? (2) ¿se corrió
`POST /vectorizacion/kpis/reindex` tras el último arranque? (3) ¿el summary se indexó
(`GET /vectorizacion/summary/{id}` / colección `summary_instrument`)? El prerrequisito de reindex cubre el
caso "0 resultados"; el 503 cubre el caso "servicio caído". Ambos deben verificarse antes de concluir que
el instrumento no tiene KPIs afines.

**Verificación de datos (criterio de aceptación 11):** tras un `upload + estandarizar + proponer` real,
`tt_rag.documento_vectorizado` y la colección `summary_instrument` deben recibir filas, y
`/vectorizacion/propuestas` devolver propuestas no vacías. Si el cálculo (`/kpis/calculo/*`) recibe KPIs
aceptados, se registra `kpi_calculo`.

---

## 5. Bug 1 — Paso Dublin Core (campos faltantes)

Contrato real (verificado en `dc_manager.register_dc`): 7 campos de usuario leídos del request:
`dc_title`, `dc_subject` (lista), `dc_description`, `dc_coverage`, `dc_rights`, `dc_source`, `dc_relation`.
El backend **ignora** `dc_date`/`dc_language` (los fija a hoy-UTC y `"es"`). El wizard hoy no envía
`dc_source` ni `dc_relation`.

**Fix (frontend, 3 archivos):**

1. `pixel-perfect-pixel/src/types/index.ts` — añadir a `DublinCore`:
   ```ts
   fuente?: string;     // dc_source
   relacion?: string;   // dc_relation
   ```
2. `pixel-perfect-pixel/src/features/upload/StepDublinCore.tsx` — añadir dos `Campo` (inputs) para
   **Fuente** (`fuente`) y **Relación** (`relacion`), ambos opcionales (sin `*`). Marcar **Fecha** e
   **Idioma** como informativos: convertirlos a solo-lectura o añadir nota
   `"El sistema fija la fecha de registro y el idioma (es)."` con el ícono `Info` (ya importado). Mantener
   el `Select` de cobertura = nivel educativo (decisión de producto documentada en findings; no es bug).
3. `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx` — en el bloque `paso === 2`, incluir en
   `RegistroMetadatos` cuando no estén vacíos:
   ```ts
   if (dc.fuente) metadatos.dc_source = dc.fuente;
   if (dc.relacion) metadatos.dc_relation = dc.relacion;
   ```
   `RegistroMetadatos` en `carga.ts` ya declara `dc_source?`/`dc_relation?`; no cambia su tipo.

El POST sigue a `POST /api/metadata/metadata/{id}` (ruta de doble `metadata` correcta; no tocar). La
inmutabilidad (409) y el pre-poblado (`getMetadatosInit`) se conservan.

**Validación de entrada (DC):** `dc_title` requerido (NOT NULL en BD y en el formulario con `*`);
`dc_subject` lista (se arma de `dc.tema.split(",")`); el resto opcional. Si `dc_source`/`dc_relation` van
vacíos, NO se envían (el backend los acepta como `None`).

**Límite de `dc_rights` (Hallazgo 4 — rev. 3):** en el esquema real `metadatos_dc.dc_rights` es
`VARCHAR(255)` (verificado en `01_schema.sql`), no `TEXT`. El input de **Derechos** en `StepDublinCore.tsx`
**ya tiene `maxLength={120}`** (verificado: `StepDublinCore.tsx` línea del `Input id="derechos"`), que
**ya respeta** el tope de BD (120 ≤ 255). **No requiere cambio** y **no** debe aflojarse a 255. El resto de
campos de usuario DC son `TEXT` (`dc_title`, `dc_subject`, `dc_description`, `dc_coverage`, `dc_source`,
`dc_relation`) y no requieren tope duro; los nuevos inputs de **Fuente** y **Relación** deben llevar un
`maxLength` razonable (p. ej. `120`) por consistencia de UI, no por restricción de BD.

---

## 6. Bug 2 — Metadatos específicos por tipo (paso 4)

Causa raíz confirmada: los campos del paso 4 (`numero_reactivos/escala/modalidad/tamano_muestra`, etc.) NO
existen en ningún contrato backend y no se persisten. Las tablas reales (`01_schema.sql`) son
`metadatos_enriquecidos_encuestas`, `_entrevistas`, `_pruebas`, con otras columnas.

### 6.1 Backend — modelos, servicio y endpoint

**Modelos SQLAlchemy nuevos** en `shared/models/` (PK/FK `id_crudo` → `raw_data.id_crudo`, patrón de
`metadatos_dc`), uno por tabla, alineados **exactamente** a las columnas del schema:

- `shared/models/metadatos_enriquecidos_encuestas.py` → `MetadatosEnriquecidosEncuestas`:
  `id_crudo (PK/FK)`, `n_respondentes INT`, `n_poblacion INT`, `objetivo TEXT`, `carrera TEXT`,
  `poblacion_objetivo TEXT`, `constructo_principal TEXT`, `palabras_clave JSONB`, `dimensiones JSONB`,
  `notas_contextuales TEXT`, `notas_interpretacion TEXT`.
- `shared/models/metadatos_enriquecidos_entrevistas.py` → `MetadatosEnriquecidosEntrevistas`:
  `id_crudo`, `identificador_propio TEXT`, `objetivo TEXT`, `metodologia TEXT`, `institucion TEXT`,
  `derechos TEXT`.
- `shared/models/metadatos_enriquecidos_pruebas.py` → `MetadatosEnriquecidosPruebas`:
  `id_crudo`, `unidad_de_aprendizaje TEXT`, `mapeo_de_reactivos_por_seccion JSONB`, `institucion TEXT`,
  `campus TEXT`, `grado TEXT`, `grupo TEXT`, `ciclo_escolar TEXT`, `tipo_de_prueba TEXT`, `version TEXT`,
  `taxonomia_bloom TEXT`, `nivel_educativo TEXT`, `objetivo_de_evaluacion TEXT`, `subareas TEXT`,
  `competencias TEXT`.

Las columnas JSONB se mapean con `from sqlalchemy.dialects.postgresql import JSONB`. Todas las columnas no
PK son `nullable=True` (coherente con el schema: solo `id_crudo` es obligatorio). **No se altera el schema
SQL** (las tablas ya existen con `IF NOT EXISTS`); los modelos solo las reflejan. Si el schema evoluciona,
se hace aditivamente.

**Servicio nuevo** `services/metadata-service/services/specific_manager.py` →
`SpecificMetadataManager.upsert(db, instrumento_id, tipo, campos)`:
- Resuelve `id_crudo` desde `instrumento_id` (= `id_instrumento`) vía `InstrumentoProcesado` (patrón de
  `DCManager`).
- Según `tipo` (`raw_data.tipo_instrumento`), escribe en la tabla correspondiente. **UPSERT** (no inmutable,
  a diferencia de DC): si existe fila por `id_crudo`, actualiza; si no, inserta. Razón: el paso 4 es un
  formulario editable que el investigador puede revisitar antes de guardar.
- Solo persiste los campos presentes/no vacíos; los ausentes quedan `NULL`. `palabras_clave`/`dimensiones`/
  `mapeo_de_reactivos_por_seccion` se guardan como JSON (lista/objeto); si llegan como string vacío, `NULL`.

**Router nuevo** `services/metadata-service/routers/specific.py`:

```
POST /api/metadata/{instrumento_id}/especificos
```

> **Decisión de ruteo (corrige la revisión 1).** El gateway (`services/api-gateway/proxy/proxy.py`) usa
> **ruteo por prefijos EXPLÍCITOS**, no un passthrough genérico de `/api/*`: solo declara handlers para
> `/api/metadata` + `/api/metadata/{path:path}` y `/api/enrichment` + `/api/enrichment/{path:path}`
> (verificado). Un `POST /api/especificos/{id}` **NO** tendría ruta en el gateway → 404. Por eso el router
> nuevo se monta con **`prefix="/metadata"`** (igual que `routers/metadata.py:router =
> APIRouter(prefix="/metadata")`) y se incluye en `main.py` con `app.include_router(specific.router,
> prefix="/api")`. La ruta final `POST /api/metadata/{instrumento_id}/especificos` cae bajo el prefijo
> `/api/metadata/*` ya proxeado, sin tocar el gateway. El sub-path `/especificos` lo distingue de los
> endpoints DC (`/api/metadata/metadata/{id}`), que tienen el doble segmento por el `prefix="/metadata"`
> interno de `metadata.py` + el `/metadata` de su propia ruta. Para evitar colisión con ese doble segmento,
> la ruta del router nuevo es `@router.post("/{instrumento_id}/especificos")` (sin segundo `/metadata`),
> dando `/api` + `/metadata` + `/{id}/especificos`.
>
> **Orden de registro en `main.py` (Hallazgo 5 — rev. 3).** El `main.py` real
> (`services/metadata-service/main.py`, verificado) incluye los routers dentro de un `try/except
> ImportError` en este orden: `health` (sin prefijo), `metadata` (`prefix="/api"`), `enrichment`
> (`prefix="/api"`). El router nuevo se añade a ese mismo bloque **después** de `metadata`:
>
> ```python
> from routers import health, metadata, enrichment, specific   # ← añadir specific
>
> app.include_router(health.router, tags=["health"])
> app.include_router(metadata.router, prefix="/api", tags=["metadata"])
> app.include_router(specific.router, prefix="/api", tags=["metadata-especificos"])  # ← nuevo
> app.include_router(enrichment.router, prefix="/api", tags=["enrichment"])
> ```
>
> El orden entre `metadata` y `specific` es **irrelevante para la corrección** porque sus patrones no
> solapan: `POST /api/metadata/metadata/{id}` (literal `metadata` como primer segmento tras `/api/metadata`)
> vs `POST /api/metadata/{id}/especificos` (sufijo literal `/especificos`). FastAPI distingue ambos sin
> ambigüedad; el orden se fija aquí solo para dejarlo escrito. El `{instrumento_id}` del router nuevo no
> captura la cadena literal `metadata` porque la ruta de registro DC está registrada como un path más
> específico y, aun si no lo estuviera, `/metadata/{id}/especificos` exige el sufijo `/especificos` que
> `/metadata/metadata/{id}` no tiene.
>
> **Verificación requerida en implementación:** el test de integración de §8 **debe afirmar** que, tras
> añadir `specific`, **ambas** rutas resuelven a su handler: `POST /api/metadata/metadata/{id}` →
> `register_metadata` (registro DC, intacto) y `POST /api/metadata/{id}/especificos` → el handler nuevo de
> metadatos específicos. También que `/metadata/{id}/init` (GET existente de `metadata.py`) sigue
> resolviendo a su handler.

Request (`EspecificosRequest`, discriminado por `tipo`): el frontend envía `tipo` + un objeto `campos` con
las claves de la tabla de ese tipo. El backend valida el `tipo` contra `raw_data.tipo_instrumento` (409/422
si no coincide) y persiste. Response: los campos persistidos + `instrumento_id` + `mensaje`.

Auth: el metadata-service hoy no exige rol en estos routers (`get_db` solo). Se mantiene el patrón del
servicio (sin auth en metadata-service) para no divergir; el gateway ya protege el perímetro.

### 6.2 Frontend — formulario, API y wizard

- `pixel-perfect-pixel/src/features/upload/StepMetadatosTipo.tsx` — reemplazar `CAMPOS_POR_TIPO` por los
  campos **reales** de cada tabla, con subconjunto razonable visible y el resto opcional:
  - **Encuesta**: `n_respondentes` (number, **pre-rellenado con `n_respondentes_detectados` del preview, editable** — resuelve revisión 3, NIT #3; es solo el valor por defecto, no se valida igualdad con `respondents[]`), `n_poblacion` (number), `objetivo` (text), `carrera` (text),
    `poblacion_objetivo` (text), `constructo_principal` (text), `palabras_clave` (texto → lista por comas),
    `dimensiones` (texto → lista por comas), `notas_contextuales` (textarea opc.),
    `notas_interpretacion` (textarea opc.). Requeridos razonables: ninguno estrictamente (todos opcionales
    en BD); se recomienda marcar `objetivo` y `constructo_principal` como sugeridos (no bloqueantes).
  - **Entrevista**: `identificador_propio`, `objetivo`, `metodologia`, `institucion`, `derechos` (todos
    text/textarea, opcionales).
  - **Prueba estandarizada**: `unidad_de_aprendizaje`, `institucion`, `campus`, `grado`, `grupo`,
    `ciclo_escolar`, `tipo_de_prueba`, `version`, `taxonomia_bloom`, `nivel_educativo`,
    `objetivo_de_evaluacion`, `subareas` (texto→lista), `competencias` (texto→lista). `mapeo_de_reactivos_por_seccion`
    se **omite del formulario** (estructura compleja JSONB): se backloguea o se deja que lo derive la
    estandarización en una iteración futura. Mostrar un subconjunto principal (`unidad_de_aprendizaje`,
    `tipo_de_prueba`, `nivel_educativo`, `objetivo_de_evaluacion`) y el resto en una sección "Más detalles"
    colapsable, para mantener el formulario manejable.
  - El estado sigue siendo `MetadatosTipo = Record<string, string>`; las claves ahora son las columnas
    reales. Los campos lista (`palabras_clave`, `dimensiones`, `subareas`, `competencias`) se capturan como
    texto separado por comas y se transforman a array en `carga.ts`.
- `pixel-perfect-pixel/src/api/carga.ts` — nueva función
  `registrarMetadatosEspecificos(idInstrumento, tipo, campos)` →
  `POST ${API_URL}/api/metadata/{id}/especificos` (gateway → metadata-service), `auth: true`, body
  `{ tipo, campos }` con los arrays ya parseados y los numéricos convertidos. Maneja 422/409 con mensaje en
  español (patrón de `registrarMetadatos`).
- `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx` — al avanzar del paso de metadatos específicos,
  llamar `registrarMetadatosEspecificos`. También usar esos campos para **enriquecer el `jsonInstrumento`**
  en `metadata.survey_specific` (`constructo_principal`, `dimensiones`, `palabras_clave`, `carrera`,
  `notas_contextuales`, `notas_interpretacion` — los que `metadata_extractor` lee para el summary) junto con
  el bloque `metadata.dublin_core` de claves `dc:` (§1.4bis). Ambos enriquecimientos ocurren antes de
  `proponerKpis` (paso 6). Esto hace que las propuestas de KPI sean más precisas y conecta los pasos 3 y 4
  con el paso de KPIs.

### 6.3 Errores y validación (específicos)

| Operación | Fallo | Respuesta | Log |
|---|---|---|---|
| Resolver instrumento | no existe | `404` | no |
| `tipo` no coincide con `raw_data.tipo_instrumento` | mismatch | `409` "El tipo no coincide con el instrumento." | WARNING |
| Campo numérico no numérico (`n_respondentes`) | parse falla | `422` con el campo | WARNING |
| JSONB mal formado (`palabras_clave`) | no es lista | se coacciona a `[]` o `422` si viene tipo imposible | WARNING |
| Persistir | `SQLAlchemyError` | rollback + `500` | ERROR |

Validación por campo: numéricos (`n_respondentes`, `n_poblacion`) enteros ≥ 0 o `NULL`; listas de str para
los JSONB; strings con límite razonable (sin truncar silenciosamente; el front limita longitud en inputs).

---

## 7. Orden de pasos del wizard (resuelto)

Hoy (`PASOS` en `UploadWizard.tsx`): `0 Archivo, 1 Limpieza, 2 Dublin Core, 3 Metadatos del tipo,
4 Vista previa JSON, 5 KPIs sugeridos, 6 Calcular KPIs, 7 Guardar`.

La confirmación de tipos de pregunta va **después del parseo/limpieza y antes de finalizar el JSON de
dominio** (para que el JSON estandarizado refleje los tipos confirmados y alimente las propuestas de KPI).
Se inserta como paso 2 (tras Limpieza), empujando el resto:

**Nuevo orden (9 pasos):**

| # (idx) | Paso | Acción de red al avanzar |
|---|---|---|
| 0 | Archivo | `POST /instrumentos/upload` (igual que hoy) |
| 1 | Limpieza | ninguna (reporte derivado del parseo) |
| **2** | **Tipos de pregunta** (NUEVO) | al **entrar**: `POST /instrumentos/{id}/estandarizar/preview`; al **avanzar**: `POST /instrumentos/{id}/estandarizar` (persiste JSON, setea `ruta_json`, guarda `jsonInstrumento`) |
| 3 | Dublin Core | `POST /api/metadata/metadata/{id}` (+ `dc_source`/`dc_relation`, §5) |
| 4 | Metadatos del tipo | `POST /api/metadata/{id}/especificos` (§6) + enriquecer `jsonInstrumento` (DC+survey_specific, §1.4bis) |
| 5 | Vista previa JSON | ninguna |
| 6 | KPIs sugeridos | al entrar: `proponerKpis` (ahora con `jsonInstrumento` real, §4) |
| 7 | Calcular KPIs | `/kpis/calculo/*` (INTACTO) |
| 8 | Guardar | `confirmarKpis` + `registrarCalculo` (INTACTO) |

Cambios concretos en `UploadWizard.tsx`:
- `PASOS` pasa a 9 entradas con `"Tipos de pregunta"` en índice 2.
- `TOTAL_PASOS = PASOS.length` (deriva solo). **Renumerar** las constantes: `PASO_CALCULO = 7`,
  `PASO_GUARDAR = 8` (hoy 6 y 7). Los `paso === N` de los pasos existentes se desplazan +1 a partir del
  antiguo paso 2.
- Nuevo estado: `tiposDetectados` (del preview), `tiposConfirmados` (editable por el investigador).
- Nuevo componente `pixel-perfect-pixel/src/features/upload/StepTiposPregunta.tsx`: tabla de preguntas con
  `text` (solo lectura), `type` (select editable con las 5 opciones en español: Binaria, Opción múltiple,
  Likert, Numérica continua, Abierta), `scale_min/max` (visibles solo si Likert), toggle "¿Es demográfica?"
  y badge de `confianza`. El investigador confirma o corrige; al avanzar se envían los tipos confirmados.
- Guardas `puedeContinuar`: el paso 2 requiere que exista `jsonInstrumento` tras `/estandarizar` (o al
  menos que el preview haya cargado y el usuario confirme). Se añade la entrada correspondiente al array
  `puedeContinuar` respetando el nuevo índice.
- Textos y labels en español (regla del proyecto). El `Stepper` recibe los 9 pasos.
- **Instrumentos tipo documento (entrevista/prueba) — resuelve revisión 3, NIT #2:** cuando el preview
  produce una sola `question` `abierta` con el texto completo del documento (`preguntas.length === 1 && type === 'abierta'`),
  `StepTiposPregunta` NO muestra el select de tipo sobre esa pregunta gigante (no aporta valor y rompería la
  UI). En su lugar muestra un estado **informativo** ("Este instrumento es un documento de texto; no se
  tipifican preguntas individuales") y deja avanzar sin edición. El texto mostrado en la UI se **trunca**
  para legibilidad, pero el **texto completo** se conserva intacto en el estado que se envía a
  `/estandarizar`.

**Mapeo de etiquetas tipo UI → vocabulario backend** (frontera en `StepTiposPregunta`/`carga.ts`):
`Binaria→binaria`, `Opción múltiple→opcion_multiple`, `Likert→likert`, `Numérica continua→numerica_continua`,
`Abierta→abierta`.

---

## 8. Testabilidad

**Unitario (sin BD ni red):**
- `type_detector`: tablas de casos por tipo (binaria `{sí,no}`, likert `1..5`, opcion_multiple con etiquetas
  repetidas, numerica_continua con floats, abierta por alta cardinalidad, columna vacía). Determinista.
- `domain_builder`: dado un `RawTable` + tipos confirmados, el dict resultante **coincide con el esquema del
  seed** (claves `instrument.sections[].questions[]`, `metadata.dublin_core`, `metadata.survey_specific`,
  `design_reference`, `respondents`). Snapshot contra una versión reducida de `inst_01.v1.json`.
- `standardization_service._ruta_relativa_proyecto`: la ruta persistida es resoluble por
  `instrumento_query._resolver_por_ruta_json` (invariante §1.5). Test cruzado.
- `instrumento_query._slug_por_id_crudo` tras el fix (Bug 5): sin `_seed_map.json` → `None`; con mapa
  explícito → el slug mapeado.
- Modelos de metadatos específicos: round-trip de campos y JSONB.

**Integración (con BD de prueba / cliente FastAPI):**
- `POST /instrumentos/{id}/estandarizar/preview` y `/estandarizar`: estados, `ruta_json`, 404/422/409.
- `POST /api/metadata/{id}/especificos`: upsert por tipo, mismatch de tipo (409), persistencia. **Afirmación
  explícita de ruteo (Hallazgo 5):** tras registrar el router `specific` en `main.py`, el test verifica que
  `POST /api/metadata/metadata/{id}` sigue resolviendo a `register_metadata` (registro DC), que
  `POST /api/metadata/{id}/especificos` resuelve al handler nuevo, y que `GET /api/metadata/metadata/{id}/init`
  sigue resolviendo a su handler. Ninguna de las tres se intercepta por otra.
- `GET /instrumentos` end-to-end del Bug 5: subir un instrumento nuevo → el DTO devuelve `nombre_archivo`/
  DC real, **no** el título de `inst_01.v1.json`.

**Difícil de testear por sí solo (requiere Chroma/Ollama) → integración manual o con doble:**
- `index_summary`/`search_kpis` (Chroma) y `/vectorizacion/propuestas`. Verificación de aceptación: filas en
  `tt_rag.documento_vectorizado` + colección `summary_instrument` tras `upload+estandarizar+proponer`, con
  `kpis` reindexada. La búsqueda de KPIs se cubre con un doble de `kpi_search` en unit tests del
  `ProposalService` si se requiere aislar.

**Comandos (de `pixel-perfect-pixel/TESTING.md` y requirements por servicio):**
- Backend: `pytest` en `services/instrument-service` y `services/metadata-service`.
- Frontend: `bun run build` en `pixel-perfect-pixel/`; `bun test` si hay suite.

---

## 9. Requisitos verificados y fuera de alcance

**Verificado contra código real:**
- `instrumento_procesado.ruta_json` y `estado='estandarizado'` ya existen (modelo + CheckConstraint).
- `estandarizado` ya mapea a `"Estandarizado"` en `map_instrumento._ESTADO_MAP`.
- `_resolver_por_ruta_json` prioriza `ruta_json`; el fallback a semilla es el único causante del Bug 5.
- `dc_source`/`dc_relation` ya los lee `register_dc` y ya existen en `metadatos_dc`.
- Las 3 tablas `metadatos_enriquecidos_*` existen; **faltan los modelos ORM y el endpoint**.
- `summary_builder`/`metadata_extractor` NO usan `questions[].type` → regla de embedding §2 se cumple y se
  preserva.
- El gateway proxea `/instrumentos/*` passthrough (endpoints nuevos de estandarización quedan expuestos sin
  tocar el gateway); `analysis-service` se llama directo con `ANALYSIS_URL`.
- El gateway usa **ruteo por prefijos explícitos**: solo `/api/metadata/*` y `/api/enrichment/*` llegan a
  metadata-service (verificado en `proxy.py`). Por eso el endpoint de metadatos específicos cuelga de
  `/api/metadata/{id}/especificos` (no `/api/especificos`, que daría 404). Ver §6.1 y §11.
- `metadata_extractor` lee `metadata.dublin_core` con claves `dc:` (`DUBLIN_CORE_KEYS` en
  `constants.py`); por eso el cliente escribe esas claves en el JSON antes de proponer KPIs (§1.4bis).
- `_slug_por_id_crudo` ya consulta `_seed_map.json` antes del fallback directo; el fix solo elimina el
  fallback directo (§3).
- `metadatos_dc.dc_rights` es `VARCHAR(255)` (§5).

**Fuera de alcance (no implementar aquí):**
- Microservicios nuevos (la estandarización vive en instrument-service).
- Segmentación semántica de documentos en preguntas individuales (el `document_parser` no segmenta; el MVP
  trata el documento como una `question` abierta).
- `mapeo_de_reactivos_por_seccion` como formulario (JSONB complejo; backlog).
- Cambios al paso de cálculo de KPIs, al grafo/espacio vectorial o al campo de archivo original (se conservan).
- Automatizar `kpis/reindex` desde el wizard (es tarea de operación/runbook).

**Supuestos (señalados para revisión de diseño):**
- El vocabulario estandarizado de `type` (`binaria/opcion_multiple/likert/numerica_continua/abierta`) difiere
  de los literales del seed (`likert_1_5`, `multiple_choice`). Es intencional (camino A) y seguro porque
  ningún consumidor actual lee `questions[].type`. Si en el futuro algo depende de los literales del seed,
  habría que mapear.
- El seed debe regenerar `_seed_map.json` para que los instrumentos sembrados sigan resolviéndose tras el
  fix del Bug 5.
- El metadata-service no aplica auth de rol en sus routers; el endpoint nuevo sigue ese patrón (perímetro en
  el gateway).

---

## 10. Resumen de archivos tocados

**Backend — instrument-service:**
- NUEVO `app/standardization/type_detector.py`, `app/standardization/domain_builder.py`
- NUEVO `app/services/standardization_service.py`, `app/routers/standardize.py`, `app/schemas/estandarizacion.py`
- MOD `app/storage/port.py`, `app/storage/local_backend.py` (método `leer`)
- MOD `main.py` (registrar router), `app/services/instrumento_query.py` (fix Bug 5)
- MOD (opcional) `app/services/map_instrumento.py` + `app/routers/list.py` (título desde `dc_title`)
- MOD `scripts/seed_demo.py` (escribir `_seed_map.json`)

**Backend — metadata-service / shared:**
- NUEVO `shared/models/metadatos_enriquecidos_encuestas.py`, `_entrevistas.py`, `_pruebas.py`
- NUEVO `services/metadata-service/services/specific_manager.py`, `routers/specific.py`
- MOD `services/metadata-service/main.py` (importar `specific` y `app.include_router(specific.router,
  prefix="/api", tags=["metadata-especificos"])` tras `metadata`, §6.1)

**Frontend — pixel-perfect-pixel:**
- MOD `src/types/index.ts` (`DublinCore.fuente/relacion`; tipos de estandarización)
- MOD `src/features/upload/StepDublinCore.tsx` (fuente/relación; fecha/idioma informativos)
- MOD `src/features/upload/StepMetadatosTipo.tsx` (campos reales por tipo)
- MOD `src/features/upload/StepArchivo.tsx` (restringir `accept` del archivo original a `.md,.txt` y validar
  extensión; §4, Hallazgo 3)
- NUEVO `src/features/upload/StepTiposPregunta.tsx`
- MOD `src/features/upload/UploadWizard.tsx` (nuevo paso, renumeración, `jsonInstrumento` del backend,
  helper puro `enriquecerJson` sin mutar estado + `setJsonInstrumento`, `catch` del `useEffect` que
  diferencia 503/error de lista vacía, `dc_source/relation`, metadatos específicos)
- MOD `src/api/carga.ts` (`estandarizarPreview`, `estandarizar`, `registrarMetadatosEspecificos`)

Sin cambios al schema SQL (tablas ya existen con `IF NOT EXISTS`); modelos ORM solo las reflejan. Cualquier
evolución de esquema sería aditiva.

---

## 11. Respuesta a los hallazgos de la revisión de diseño

### 11.1 Segunda revisión (`design-review.json` actual) — veredicto `CHANGES_REQUESTED` sobre la revisión 2

Los 5 hallazgos (3 MEDIUM, 2 NIT) se **atienden** en su totalidad; ninguno se backloguea ni se ignora.
Cada cambio es coherente con los requisitos originales (esquema del seed, camino A, embedding solo por
texto, no microservicios nuevos, español, no destructivo).

| # | Sev | Hallazgo | Resolución (rev. 3) |
|---|---|---|---|
| 1 | MEDIUM | El enriquecimiento DC/`survey_specific` muta `jsonInstrumento` en sitio; el objeto no fluye fiablemente a `confirmarKpis` | **Atendido.** §1.4bis se reescribe: helper puro `enriquecerJson` que devuelve una **copia nueva** (`jsonEnriquecido`), `setJsonInstrumento(jsonEnriquecido)` para persistir en estado, el `Blob archivoJson` se deriva de esa copia, y se especifica que `confirmarKpis` (paso 8) consume el **mismo** `jsonEnriquecido`. Eliminada la mutación `jsonInstrumento.metadata = ...`. §4 usa el mismo helper. |
| 2 | MEDIUM | El `catch` degrada cualquier error a "0 KPIs"; `propose` lanza **503** (Chroma/Ollama caídos), no 422, reproduciendo el síntoma del Bug 4 en silencio | **Atendido.** §4: el `catch` diferencia lista vacía (éxito, sin toast) de error de servicio (503/4xx/5xx, con `toast.error` e instrucciones). Nueva tabla de errores de `proponerKpis` en §4 con el 503 explícito, y nota de runbook ("causa #1 de 0 KPIs = servicio de vectorización caído"). Verificado que `ProposalService.propose` lanza `503 SERVICE_UNAVAILABLE`. |
| 3 | MEDIUM | Fuente del texto del original ambigua (texto completo vs `text_preview`); no se acota `archivoOriginal` binario (PDF/DOCX) enviado como `text/markdown` | **Atendido.** §1.4 fija que `domain_builder` usa `ExtractedDocument.text` **íntegro** (no el preview) para documentos. §4 fija que `textoDerivadoDePreguntas` es respaldo **solo tabular** (para documentos el `question.text` ya es el texto completo), y que `StepArchivo` **restringe `accept` a `.md,.txt`** y valida la extensión, cayendo al respaldo si el usuario adjunta un binario. Verificado `read_document`/`ExtractedDocument` y el `Blob text/markdown` de `carga.ts`. |
| 4 | NIT | Pedir `maxLength={255}` en Derechos aflojaría el límite actual (`120`) | **Atendido.** §5 corregido: el `maxLength={120}` actual ya respeta `VARCHAR(255)`; **no requiere cambio** y no debe aumentarse a 255. Verificado en `StepDublinCore.tsx`. |
| 5 | NIT | No se fija el orden de `include_router` del router `specific` ni que el test afirme que ambas rutas resuelven | **Atendido.** §6.1 fija el bloque `include_router` real de `main.py` (orden health→metadata→specific→enrichment, todos `prefix="/api"` salvo health) y aclara que el orden metadata/specific es irrelevante por no solapar. §8 añade la afirmación de que el test de integración verifica que `/api/metadata/metadata/{id}` (DC), `/api/metadata/{id}/especificos` y `/api/metadata/metadata/{id}/init` resuelven cada uno a su handler. Verificado `main.py`. |

### 11.2 Primera revisión (histórico) — 9 hallazgos resueltos en la revisión 2

Veredicto previo: **CHANGES_REQUESTED**. Todos los hallazgos se **atendieron** (ninguno se backlogueó ni se
ignoró); cada cambio es coherente con los requisitos originales (esquema del seed, camino A, embedding solo
por texto, no microservicios nuevos, español, no destructivo).

| # | Sev | Hallazgo | Resolución |
|---|---|---|---|
| 1 | HIGH | DC nunca se escribe en el JSON pero los consumidores lo leen con claves `dc:` | **Atendido.** Nueva §1.4bis: el cliente enriquece `jsonInstrumento.metadata.dublin_core` con claves `dc:` (`dc:title/dc:subject/dc:description/dc:coverage`) desde el estado `dc`, antes de `proponerKpis`. Se eligió la vía cliente (justificada) sobre reescribir el JSON en disco. §4 y §6.2 ya referencian el enriquecimiento DC + survey_specific. |
| 2 | HIGH | La guarda del `useEffect` exige `archivoOriginal`, incompatible con el fallback | **Atendido.** §4 reescribe la guarda a `if (!jsonInstrumento) return;` y deriva el original de los `text` de las preguntas (`textoDerivadoDePreguntas`) cuando `archivoOriginal` es `null`. Documentada la función. |
| 3 | MED | El fix del Bug 5 describía mal `_slug_por_id_crudo` (ya consulta `_seed_map.json`) | **Atendido.** §3 ahora muestra el **código real actual** (con la consulta a `_seed_map.json` ya presente) y especifica que el único cambio es **eliminar las dos líneas** del `if id_crudo >= 1`. Verificado contra `instrumento_query.py:72-81`. |
| 4 | MED | Regla "preguntas+demográficas cubren los headers" (422) ambigua | **Atendido.** §1.7 reescribe la validación por **correspondencia de nombres**: 422 solo si una pregunta referencia un header inexistente; headers no referenciados (incl. `respondent_id`/`profile_id`) se ignoran con nota; headers duplicados se desambiguan por posición. |
| 5 | MED | El esquema omite claves del seed (`synthetic_profiles`, `profile_id`) y diverge en `section.name` | **Atendido.** §1.4 lista explícitamente las claves omitidas a propósito con su razón, declara el objetivo como "superconjunto compatible de lectura" (no copia byte a byte) y fija `section.name = "Reactivos del módulo"` (literal del seed). |
| 6 | MED | Cota dura `scale_max ≤ 7` contradice el camino A | **Atendido.** §1.3 degrada `N ≤ 7` a **preferencia del detector**; §1.7 relaja la validación de entrada a `1 ≤ scale_min < scale_max ≤ 100`, permitiendo escalas confirmadas por el investigador (1..10, 0..10, etc.). |
| 7 | MED | `instrument_id = inst_{id_crudo}` colisiona con `inst_11` para `id_crudo=11` | **Atendido.** §1.4/§1.5 usan `instrument_id = f"upload_{id_crudo}"` (prefijo inequívoco) y declaran el campo **puramente informativo**; la de-colisión real la garantiza `_seed_map.json` (fix Bug 5). Eliminada la afirmación falsa de "sin colisión por el formato". |
| 8 | NIT | `dc_rights` es `VARCHAR(255)`, no `TEXT` | **Atendido.** §5 documenta el tope de 255 y fija `maxLength={255}` (o menor) en el input de Derechos. Verificado en `01_schema.sql:101`. |
| 9 | NIT | Falta fijar `tipo_instrumento` del preview para documentos | **Atendido.** §1.6(A) declara que `tipo_instrumento` es siempre `raw_data.tipo_instrumento` ∈ `{encuesta, entrevista, prueba_estandarizada}`. |

**Riesgo de ruteo de la revisión 1 (supuesto no verificado #4), ahora CERRADO:** se leyó
`services/api-gateway/proxy/proxy.py`. El gateway usa **ruteo por prefijos explícitos**; solo proxea
`/api/metadata/*` y `/api/enrichment/*` hacia metadata-service. La ruta propuesta en la revisión 1
(`/api/especificos/*`) **habría dado 404**. §6.1 corrige el endpoint a `POST /api/metadata/{id}/especificos`
(router nuevo con `prefix="/metadata"`, montado con `prefix="/api"` en `main.py`), que cae bajo el prefijo
ya proxeado sin tocar el gateway. Frontend (`carga.ts`) y §7 actualizados a la ruta corregida.

**Supuestos de la revisión aún pendientes de confirmar en implementación (no bloqueantes):**
- `document_parser` no segmenta (base del MVP de documentos como una sola `question` abierta): afirmado en
  `findings.md`; el implementador debe releer `app/parsing/document_parser.py` antes de codificar §1.4.
- `tabular_parser` normaliza celdas vía `header_utils.normalize_cell` (base del detector §1.3): citado en
  `findings.md`; releer antes de codificar `type_detector.py`.
