# Diseño técnico — Cablear el pipeline de carga (pasos 1-4) al backend real

Iteración 2 de la integración front↔back. Este documento es la fuente de verdad
de implementación para cablear los pasos 1-4 del asistente de carga
(subir → limpieza → metadatos → asociación de KPIs) a los microservicios reales
ya existentes, más añadir el proxy del `metadata-service` en el api-gateway.

Todo se trabaja EXCLUSIVAMENTE en el worktree
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\cablear-pipeline`
(rama `cablear-pipeline`). El checkout principal queda intacto.

**Esta es una REVISIÓN del diseño.** La revisión actual (`design-review.json`,
veredicto `CHANGES_REQUESTED`: **2 MEDIUM + 3 NIT**, 0 HIGH) y su `design-review.md`
confirmaron en frío la gran mayoría de las afirmaciones del diseño y pidieron corregir
dos puntos (una afirmación incorrecta sobre qué valida el wizard en Dublin Core, y una
decisión de alcance que quedaba abierta sobre el arreglo de `dc_manager`) más tres NIT
de claridad. Todos los hallazgos se resuelven en el cuerpo (secciones corregidas) y se
listan con su resolución explícita en **§13.A**. El blocker de `metadata-service`
(atributos de modelo inexistentes), descubierto en la revisión previa y confirmado por
la actual, se documenta en §4.0/§11 y su arreglo queda **decidido como obligatorio** en
esta iteración (ya no "pendiente de scope").

Idioma: toda la interfaz, rutas de dominio e identificadores visibles al usuario
permanecen en español. No se rediseña UI/componentes/estilos; solo se cambia el
cuerpo de funciones en `pixel-perfect-pixel/src/api/*.ts` (firmas estables) y se
añaden rutas de proxy en el gateway.

---

## 0. Resumen ejecutivo y stack bloqueado

El acceso a datos del frontend pasa SIEMPRE por `pixel-perfect-pixel/src/api/*.ts`.
Cada función de esas capas o resuelve con `simularRed()` (mock) o llama a la API
real (`pedir()` para JSON, o `fetch`+`FormData`+Bearer para multipart). Las firmas
exportadas no cambian.

Stack (bloqueado una vez aprobado este diseño):
- Frontend: TypeScript + React + TanStack Router + Vite (ya existente). Fetch nativo.
- `pedir()` fuerza `Content-Type: application/json`; **no sirve para multipart**.
  Para multipart se usa `fetch` directo con `FormData` y header `Authorization:
  Bearer <token>` leído con `leerToken()` (patrón ya usado en `chat.ts`).
- Base URLs (de `src/api/client.ts`, sin cambios): `API_URL` (gateway :8000),
  `ANALYSIS_URL` (analysis-service :8002 directo). No se añade ninguna base URL nueva
  (metadatos entra por el gateway, §5).
- Backend: FastAPI por microservicio (ya existente). El gateway es la única puerta
  salvo `/vectorizacion/*`, que el frontend consume directo contra `ANALYSIS_URL`
  (patrón ya establecido por `espacio.ts`).

Decisiones principales (detalladas abajo):
1. Metadatos: se añade proxy en el gateway (patrón de puerta única) — **NO** se usa
   `METADATA_URL` directo. §5.2.
2. La "limpieza" (paso 2) se **deriva** del `parseo` de `UploadResponse`; no existe
   endpoint de limpieza y no se inventa uno. §3.
3. La asociación de KPIs (paso 4) se cablea directo a `ANALYSIS_URL`
   (`/vectorizacion/propuestas` + `/vectorizacion/confirmar`). §6.
4. Dashboard de KPIs: solo `getCatalogoKpis` obtiene fuente real (con fallback a mock
   si el catálogo viene vacío); `getKpis`, `getNoticias`, `getDatosGrafica` quedan en
   mock con TODO del endpoint faltante. §7.
5. **IDs: `id_crudo` ≠ `id_instrumento`.** Se propaga explícitamente cada uno a su
   destino. §1.1 y §4.0 (regla nueva por hallazgo HIGH-1).

### 0.1 Nota de numeración de pasos (resuelve NIT-3 de la revisión 2)

El `UploadWizard.tsx` real tiene **7 pasos** con índices de estado `paso` de 0 a 6
(verificado en `PASOS` y en los `paso === N`):

| Etiqueta UI ("Paso N de 7") | Nombre | Índice de estado `paso` |
|---|---|---|
| Paso 1 | Archivo | `paso === 0` |
| Paso 2 | Limpieza | `paso === 1` |
| Paso 3 | Dublin Core (metadatos) | `paso === 2` |
| Paso 4 | Metadatos del tipo | `paso === 3` |
| Paso 5 | Vista previa JSON | `paso === 4` |
| Paso 6 | KPIs | `paso === 5` |
| Paso 7 | Guardar | `paso === 6` |

Cuando este documento dice informalmente "paso 1 = subir", "paso 2 = limpieza",
"paso 3 = metadatos (Dublin Core)" y "paso 4 = KPIs", se refiere a las **etapas
lógicas del cableado**, no a las etiquetas de UI. Para evitar ambigüedad, **al citar
guardas del wizard se usa SIEMPRE el índice de estado**: limpieza = `paso === 1`,
Dublin Core = `paso === 2`, KPIs = `paso === 5`. Las guardas citadas por índice en
§3.1, §4 y §6 ya son correctas respecto a esta tabla (verificado contra
`UploadWizard.tsx`).

---

## 1. Mapa de funciones api → endpoint real (resumen)

| Función (archivo) | Hoy | Endpoint real | Transporte |
|---|---|---|---|
| `subirInstrumento` *(nueva, en `carga.ts`)* | — | `POST /instrumentos/upload` (gateway) | `fetch`+`FormData`+Bearer |
| `limpiarArchivo` (`carga.ts`) | mock | *(sin endpoint)* NO hace red; no sobreescribe el reporte real (§3) | — |
| `getMetadatosInit` *(nueva, en `carga.ts`)* | — | `GET /api/metadata/metadata/{id_instrumento}/init` (gateway) | `pedir({auth:true})` |
| `registrarMetadatos` *(nueva, en `carga.ts`)* | — | `POST /api/metadata/metadata/{id_instrumento}` (gateway) | `pedir({auth:true})` |
| `getKpisSugeridos` (`carga.ts`) | mock | *(delega en `proponerKpis`; ver §6.1)* | — |
| `proponerKpis` *(nueva, en `carga.ts`)* | — | `POST /vectorizacion/propuestas` (ANALYSIS_URL) | `fetch`+`FormData` (auth:false) |
| `confirmarKpis` *(nueva, en `carga.ts`)* | — | `POST /vectorizacion/confirmar` (ANALYSIS_URL) | `pedir({auth:false})` |
| `guardarInstrumento` (`carga.ts`) | mock | *(ver §6.4)* devuelve el id real | — |
| `getCatalogoKpis` (`kpis.ts`) | mock | `GET /instrumentos/kpis/catalogo` (gateway) → `list[str]`; fallback mock si vacío | `pedir({auth:true})` |
| `getKpis` (`kpis.ts`) | mock | *(sin endpoint)* queda mock | — |
| `getNoticias` (`kpis.ts`) | mock | *(sin endpoint)* queda mock | — |
| `getDatosGrafica` (`kpis.ts`) | mock | *(sin endpoint)* queda mock | — |

Nota de firmas: todas las funciones ya exportadas conservan su firma exacta. Las
funciones **nuevas** son adiciones; el componente `UploadWizard.tsx` necesitará
cambios mínimos y acotados para encadenar ids/archivos reales entre pasos (ver §8).

### 1.1 Regla de IDs (CRÍTICA — resuelve hallazgo HIGH-1)

Verificado contra los modelos ORM reales (`shared/models/`):
- `RawData` → PK `id_crudo`; contiene `tipo_instrumento`, `nombre_archivo`,
  `raw_archivo`, `raw_archivo_original`, `id_owner`, `fecha_carga`.
- `InstrumentoProcesado` → PK **`id_instrumento`**, FK `id_crudo` → `raw_data`.
  Contiene `ruta_de_archivo_limpio`, `ruta_json`, `estado`, fechas. **No** tiene
  `nombre`, `archivo_nombre`, `tipo_instrumento` ni `ruta_archivo`.
- `MetadatosDC` → PK `id_crudo` (hija de raw_data).

Consecuencias (todas verificadas en código, contradicen suposiciones del diseño v1):
- `/vectorizacion/propuestas` y `/vectorizacion/confirmar` reciben `id_instrumento`
  (PK de `instrumento_procesado`). Verificado en `app/.../vectorizacion.py` + schema.
- `metadata-service` (`dc_manager`) consulta por `id_instrumento` (ver §4.0 sobre el
  bug de atributos). El path param del router se llama `instrumento_id` y se usa como
  `id_instrumento`.
- `instrument-service GET /instrumentos/{id}` usa **`id_crudo`** como id canónico.
- `UploadResponse` devuelve **AMBOS** (`id_crudo` **e** `id_instrumento`).

Regla de propagación en el wizard:
- `subirInstrumento` devuelve ambos ids del `UploadResponse` y el wizard los guarda
  por separado (`idCrudo`, `idInstrumento`).
- A metadatos (§4) y a KPIs (§6) se pasa **`id_instrumento`**.
- A instrument-service (listados/detalle) se pasa **`id_crudo`**.

`_seed_map.json` (de `seed_demo.py`) mapea **`inst_XX → id_crudo`**, NO
`id_instrumento` (verificado: `seed_map[inst] = raw.id_crudo`). La igualdad
`id_crudo == id_instrumento == N` sólo se cumple en una BD recién truncada donde
ambas secuencias arrancan en 1 — es una suposición del script `post_propuestas.ps1`
(`$id = $n`), **no** un hecho del esquema. Para la demo (§8.b):
- opción A (recomendada): resolver `id_instrumento` desde `id_crudo` consultando
  `instrumento_procesado` (p. ej. ampliar `seed_demo.py` para que persista también
  `id_instrumento` en `_seed_map.json`), o
- opción B: documentar explícitamente que la demo asume BD recién sembrada y por eso
  `id_crudo == id_instrumento == N`, condicionando la igualdad (no presentándola como
  verificada).

Decisión: usar **opción A** para robustez (persistir ambos ids en `_seed_map.json`),
y aceptar **opción B** como atajo sólo si la demo corre contra una BD recién truncada,
dejándolo escrito como condición. (El cambio en `seed_demo.py` para persistir
`id_instrumento` es un edit acotado del script de siembra, no del runtime de los
servicios; ver §12.)

---

## 2. Paso 1 — Subir el instrumento (`carga.ts` → `/instrumentos/upload`)

### 2.1 Endpoint (verificado en `services/instrument-service/app/routers/upload.py`)
`POST /instrumentos/upload` (multipart/form-data). Vía gateway `API_URL` (el proxy
`/instrumentos/*` ya reenvía a instrument-service :8001, verificado en `proxy.py`).
Requiere `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` → **necesita Bearer**.

Campos del form (verificados en `upload.py`):
- `archivo` (UploadFile, requerido): el archivo RESPONDIDO (con respuestas).
- `tipo_instrumento` (Form str, requerido): `encuesta | entrevista | prueba_estandarizada`.
- `archivo_original` (UploadFile, opcional): el instrumento ORIGINAL (solo preguntas).

Respuesta `201` → `UploadResponse` (verificado en `app/schemas/upload.py`):
```
{
  id_crudo: int, id_instrumento: int, id_owner: int,
  tipo_instrumento: "encuesta"|"entrevista"|"prueba_estandarizada",
  estado: "recibido", fecha_carga: datetime|null,
  archivo_respondido: ArchivoRegistrado,
  archivo_original?: ArchivoRegistrado,
  mensaje: string
}
ArchivoRegistrado = {
  nombre_original, ruta_relativa, extension, mime_type,
  parser_family: "tabular"|"documento", size_bytes, parseo: ParseoArchivo|null
}
ParseoArchivo = {
  parser_family,
  // tabular: headers[], n_columns, n_rows, preview_rows[][], sheet
  // documento: n_chars, n_words, n_pages, text_preview
  // comunes: encoding, notes[]
}
```

### 2.2 Función nueva
```ts
// carga.ts
export interface ResultadoCarga {
  idCrudo: number;        // raw_data PK  (instrument-service)
  idInstrumento: number;  // instrumento_procesado PK (metadatos + KPIs)
  reporte: ReporteLimpieza; // derivado del parseo (ver §3)
}
export async function subirInstrumento(
  archivo: File,
  tipo: TipoInstrumento,          // etiqueta UI; se mapea al enum backend
  archivoOriginal?: File | null,
): Promise<ResultadoCarga>
```
Implementación: construir `FormData` con `archivo`, `tipo_instrumento` (mapeado,
§2.3) y, si viene, `archivo_original`; `fetch(`${API_URL}/instrumentos/upload`,
{method:'POST', body, headers:{Authorization: Bearer}})`. Mapear la respuesta a
`ResultadoCarga` capturando **ambos** ids (§1.1) y derivar `reporte` con
`mapearParseoALimpieza()` (§3). El token se obtiene con `leerToken()` (igual que
`chat.ts`); si falta, no se añade el header y el backend responderá 401 → se propaga
como `Error` con status.

### 2.3 Mapeo de `tipo` UI → enum backend (invariante de borde — frontend)
`TIPOS_INSTRUMENTO` del front es `["Encuesta","Entrevista","Prueba estandarizada"]`
(verificado en `src/types/index.ts`). El backend exige `encuesta | entrevista |
prueba_estandarizada` (verificado en `app/config/constants.py`). Mapa explícito
(constante `TIPO_UI_A_BACKEND`, reusada en §6):
```
"Encuesta" -> "encuesta"
"Entrevista" -> "entrevista"
"Prueba estandarizada" -> "prueba_estandarizada"
```
Dueño del invariante: la capa `carga.ts` (frontend), porque es la frontera donde la
etiqueta de UI se convierte en el vocabulario del dominio.

### 2.4 Validación de entrada (paso 1)
- `archivo`: requerido. El backend valida extensión por tipo (verificado en
  `constants.py`): encuesta → `.csv/.xlsx/.xls`; entrevista/prueba → `.pdf/.txt/.docx`.
  Límite 100 MB. En error el backend responde 4xx con `detail`; el front lo muestra.
- `tipo`: requerido, uno de los 3 valores UI.
- `archivoOriginal`: opcional; el backend lo trata best-effort (su parseo no bloquea
  la carga, verificado en `upload_service.py`).

### 2.5 Errores (paso 1)
| Condición | Recuperable | Qué recibe el caller | Log |
|---|---|---|---|
| 401 (sin/mal token) | sí (re-login) | `ErrorHttp status=401`, msg "Usuario o contraseña incorrectos" (para `fetch` manual se replica el mapeo) | no (cliente) |
| 403 (rol insuficiente) | no | `Error` con `detail` del backend | no |
| 4xx validación (extensión/tamaño) | sí (otro archivo) | `Error` con `detail` | no |
| 5xx / red | reintentar | `Error` genérico | consola (dev) |
El toast/estado de error ya existe en el wizard; no se rediseña.

### 2.6 ⚠️ Hallazgo de alcance de la demo (archivos .md/.json) — IDs corregidos
El endpoint de upload **no acepta `.md` ni `.json`** (verificado en `constants.py`:
solo `.csv/.xlsx/.xls/.pdf/.txt/.docx`). Los artefactos de la demo en
`storage/raw/` son `inst_XX.md` (original, solo preguntas) e `inst_XX.v1.json`
(instrumento enriquecido). Por tanto:
- El flujo de upload REAL funciona para archivos tabulares/documento legítimos
  (p. ej. un `.csv` de respuestas), pero **no** para subir el `.json` de la demo.
- Para la demo del paso 4 (asociación de KPIs) **no se depende del upload**: los
  instrumentos ya están sembrados por `seed_demo.py` (raw_data + instrumento_procesado).
  **Corrección (hallazgo HIGH-1):** `_seed_map.json` guarda `inst_XX → id_crudo`, NO
  `id_instrumento`. La asociación necesita `id_instrumento`; ver la regla de IDs §1.1
  (resolver `id_instrumento` desde `id_crudo`, o persistir ambos en el seed_map). La
  afirmación v1 "`inst_NN → id_instrumento = N` (verificado)" era incorrecta: sólo
  vale en BD recién truncada y es una suposición del script de demo, no del esquema.

Decisión: se cablea el upload tal cual (es el camino real para archivos soportados) y
se documenta que para demostrar los pasos 3-4 con los artefactos `.md/.json` se usan
los instrumentos sembrados, pasando siempre **`id_instrumento`** (resuelto según
§1.1). No se amplía el upload para aceptar `.json/.md`: queda fuera de alcance.
Ver §8.b para cómo el wizard obtiene un `id_instrumento` en la demo.

---

## 3. Paso 2 — Limpieza (derivada del `parseo`, sin endpoint propio)

No existe endpoint de limpieza en el backend (verificado: instrument-service solo
expone `/health`, `/instrumentos/upload`, `/instrumentos` (list/get/catálogo),
`DELETE /instrumentos/{id}`). La "limpieza" del paso 2 se **deriva** del resumen de
parseo que ya viene en `UploadResponse.archivo_respondido.parseo`. **No se inventa
endpoint**; `limpiarArchivo` conserva su firma pero su cuerpo deja de usar el mock.

### 3.1 Firma estable y comportamiento ÚNICO (resuelve hallazgo MEDIUM-4)
```ts
export function limpiarArchivo(_archivo: File): Promise<ReporteLimpieza>
```
Comportamiento fijado (una sola opción, sin "o/o"):
1. `subirInstrumento` (§2) calcula el `ReporteLimpieza` real derivado del parseo y lo
   devuelve en `ResultadoCarga.reporte`. **El wizard hace `setReporte(reporte real)`
   al confirmar el paso 0, ANTES de avanzar al paso 1.**
2. En el `useEffect` del paso 1 el guard existente es
   `if (paso === 1 && archivo && !reporte) limpiarArchivo(archivo).then(setReporte)`
   (verificado). Como el reporte real ya existe, el guard `!reporte` es **falso** y
   `limpiarArchivo` **no se invoca**. No hay carrera: el reporte real nunca se
   sobrescribe.
3. Además, para blindar el caso extremo (si por cualquier motivo el reporte no estaba
   puesto), se **elimina la invocación de `limpiarArchivo` del `useEffect`** y el
   reporte pasa a venir exclusivamente de `subirInstrumento`. (Edit acotado en
   `UploadWizard.tsx`, dentro del alcance §8/§12.) `limpiarArchivo` se mantiene
   exportada por compatibilidad de firma; su cuerpo devuelve un `ReporteLimpieza`
   derivado sólo de lo disponible del `File` (nombre/tamaño, con ceros y `cambios:[]`)
   y lleva comentario de que el reporte real lo produce `subirInstrumento` y de que
   esta función ya no se llama desde el wizard.

Decisión explícita: **se elimina la llamada en el `useEffect`** (no se deja "no-op
ambiguo"). Así el único productor del reporte es `subirInstrumento`.

### 3.2 Mapeo `ParseoArchivo` → `ReporteLimpieza` (verificado contra inst_01)
`ReporteLimpieza` (de `src/types/index.ts`):
```
{ duplicadosEliminados: number; nulosTratados: number;
  columnasNormalizadas: number; cambios: CambioLimpieza[] }
CambioLimpieza = { campo: string; antes: string; despues: string }
```
El `parseo` NO trae conteos de duplicados/nulos (no hay etapa de limpieza real), por
lo que el mapeo es **estructural y honesto**, derivado de lo que sí existe. Función
pura `mapearParseoALimpieza(parseo: ParseoArchivo | null): ReporteLimpieza`:

- `columnasNormalizadas` = `parseo?.headers?.length ?? 0`
  (nº de columnas detectadas; para `documento` queda 0).
- `duplicadosEliminados` = `0` (el backend no deduplica en esta fase; valor honesto).
- `nulosTratados` = `0` (ídem; en inst_01 las abiertas q9/q10 son `null` pero no se
  tratan en esta fase).
- `cambios`: lista derivada de observaciones reales del parser:
  - si hay `headers`: una entrada por cada header
    `{ campo: "Columna detectada", antes: header, despues: header }`;
  - si `parser_family === "documento"`: una sola entrada resumen
    `{ campo: "Texto extraído", antes: `${n_chars} caracteres`,
       despues: `${n_words} palabras` }`;
  - además, una entrada por cada string en `parseo.notes[]`:
    `{ campo: "Observación del parser", antes: nota, despues: "" }`.
  - si `parseo` es `null`: `cambios: []`.

Esto preserva la **forma** de `ReporteLimpieza`/`CambioLimpieza` sin inventar
métricas. Comentario obligatorio en el código: los conteos de duplicados/nulos son 0
porque **no hay etapa de limpieza con esos conteos**; cuando exista
`POST /instrumentos/limpieza` se reemplaza este derivado.

### 3.3 Validación / errores (paso 2)
No hay E/S nueva: todo se deriva en memoria del `UploadResponse`. Si
`archivo_respondido.parseo` es `null`, el reporte sale con ceros y `cambios: []`; no
es error. `puedeContinuar[1] = !!reporte` (verificado) ya se satisface porque el
reporte real se puso en el paso 0.

---

## 4. Paso 3 — Metadatos Dublin Core (`carga.ts` → `/api/metadata/metadata/{id}`)

### 4.0 ⚠️⚠️ BLOCKER NUEVO (no reportado por la revisión): `dc_manager` usa atributos de modelo inexistentes

Verificado leyendo `services/metadata-service/services/dc_manager.py` contra los
modelos ORM reales (`shared/models/instrumento_procesado.py`,
`shared/models/metadatos_dc.py`, `shared/models/raw_data.py`) y confirmando que
`services/metadata-service/models.py` está **vacío** (no hay override local; el
servicio importa los modelos de `shared.models`). Discrepancias:

| `dc_manager` usa | Realidad del modelo | Efecto en runtime |
|---|---|---|
| `InstrumentoProcesado.instrumento_id` (filtro) | la PK es `id_instrumento` | `AttributeError` → 500 |
| `instrumento.tipo_instrumento` | vive en `RawData` (vía `id_crudo`), no en `InstrumentoProcesado` | `AttributeError` → 500 |
| `instrumento.nombre` | no existe en `InstrumentoProcesado` | `AttributeError` → 500 |
| `instrumento.archivo_nombre` | no existe; el nombre es `RawData.nombre_archivo` | `AttributeError` → 500 |
| `instrumento.ruta_archivo` | el modelo tiene `ruta_json`/`ruta_de_archivo_limpio` | `init` degrada format a "unknown" |
| `MetadatosDC.instrumento_id` (filtro) | la PK/clave real es `id_crudo` | `AttributeError` → 500 |

Conclusión honesta: **el `metadata-service` NO es ejecutable contra el esquema real
tal cual**; `init`/`register`/`get` fallarían con 500 (AttributeError) antes de llegar
a devolver datos. Por tanto el **cableado del paso 3 por sí solo no basta**: requiere
reconciliar `dc_manager` con los modelos reales. Esto es un cambio de backend, no de
frontend puro.

**Decisión de alcance (RESUELTA — resuelve hallazgo MEDIUM-2 de la revisión 2).**
No se deja abierta: el objetivo explícito del usuario es "cablea todo" y "que sí
muestre … juntar instrumentos … metadatos …". Un paso 3 que responde 500 no cumple ese
objetivo. Por tanto **esta iteración SÍ incluye el arreglo mínimo de `dc_manager.py`**
como parte del cableado del paso 3. El frontend se cablea según §4.1-§4.5 (rutas,
payload, mapeos) **y** se reconcilia el backend. Instrucción única para el implementador
(no ramificación "según confirme el usuario"):

Arreglo obligatorio en `services/metadata-service/services/dc_manager.py` (en
`get_initial_data`, `register_dc`, `get_dc` y `delete_dc`):
1. **Filtrar `InstrumentoProcesado` por `id_instrumento`** (NO por `instrumento_id`,
   que no existe). El path param del router sigue llamándose `instrumento_id` pero se
   usa como valor de `id_instrumento`.
2. **`tipo_instrumento` y `nombre_archivo`**: obtenerlos con un lookup/join a `RawData`
   por `instrumento.id_crudo` (NO `instrumento.tipo_instrumento` / `instrumento.nombre`
   / `instrumento.archivo_nombre`, inexistentes). `tipo_instrumento ← RawData.tipo_instrumento`;
   el nombre para el título sugerido ← `RawData.nombre_archivo`.
3. **Ruta de archivo**: usar `instrumento.ruta_json` o `instrumento.ruta_de_archivo_limpio`
   (NO `instrumento.ruta_archivo`, inexistente). El `dc_format` deja de degradar a
   "unknown" cuando hay `ruta_json`.
4. **`MetadatosDC`**: filtrar/crear por **`id_crudo`** (PK real), resolviendo `id_crudo`
   desde el `InstrumentoProcesado` cargado (NO `MetadatosDC.instrumento_id`). Eliminar
   cualquier `instrumento.nombre = …` del update (atributo inexistente) o sustituirlo
   por un atributo real.

Este arreglo es un edit **acotado** del servicio de metadatos (sólo reconcilia nombres
de atributos ORM; no cambia el contrato HTTP ni la forma de respuesta), por lo que es
coherente con la restricción de "edits acotados". Se marca como **ítem obligatorio del
paso 3** en §11/§12 (ya no "pendiente de confirmación de scope").

⚠️ Suposición a confirmar: que el esquema SQL de `metadatos_dc` en Postgres coincide
con el modelo `shared` (`id_crudo` PK). No se leyó el DDL de `metadatos_dc`; se marca
como pendiente.

### 4.1 Rutas reales (doble segmento `metadata`) — verificado
El enunciado indica `GET /api/metadata/{id}/init` y `POST /api/metadata/{id}`, pero el
código real tiene **doble segmento** (verificado en `routers/metadata.py` +
`main.py`): el router usa `APIRouter(prefix="/metadata")` y decoradores
`@router.get("/metadata/{instrumento_id}/init")`, y se monta con `prefix="/api"`.
Composición real:
- `GET  /api/metadata/metadata/{instrumento_id}/init`
- `POST /api/metadata/metadata/{instrumento_id}`
- `GET  /api/metadata/metadata/{instrumento_id}`
- `GET  /api/metadata/metadata`
- `DELETE /api/metadata/metadata/{instrumento_id}`

(Análogo para `enrichment`: `/api/enrichment/enrichment/...`.)
El frontend llama a las rutas **reales** con el doble `metadata`; el proxy (§5) hace
passthrough del path AS-IS, preservando el doble segmento de punta a punta. Comentario
en `carga.ts` explicando el doble `metadata` para que nadie lo "corrija". El
`instrumento_id` del path se alimenta con **`id_instrumento`** (§1.1).

### 4.2 Funciones nuevas
```ts
// carga.ts
export interface MetadatosInit {
  dc_creator: string; dc_publisher: string; dc_type: string;
  dc_format: string; dc_date: string; dc_language: string;
  dc_title_sugerido: string;
}
export function getMetadatosInit(idInstrumento: number): Promise<MetadatosInit>

export interface RegistroMetadatos {
  dc_title: string;              // requerido (sólo por el wizard; backend no valida)
  dc_subject: string[];          // requerido (sólo por el wizard; backend no valida)
  dc_creator?: string;           // el creador real lo envía el frontend (ver §4.4)
  dc_description?: string; dc_coverage?: string; dc_rights?: string;
  dc_source?: string; dc_relation?: string;
}
export function registrarMetadatos(
  idInstrumento: number, datos: RegistroMetadatos,
): Promise<Record<string, unknown>>  // backend devuelve los 13 campos DC
```
Transporte: `pedir<...>(`${API_URL}/api/metadata/metadata/${idInstrumento}/init`,
{auth:true})` y `pedir(..., {method:"POST", body: datos, auth:true})` (JSON ⇒ `pedir`
sirve). El gateway reenvía `Authorization` tal cual (verificado en `proxy.py`); el
metadata-service **no** tiene dependencia de auth propia (sus endpoints sólo dependen
de `get_db`, verificado en `metadata.py`), así que el Bearer es inofensivo. Se envía
`auth:true` por consistencia con el resto del panel.

### 4.3 Pre-poblado de init (CORREGIDO — resuelve hallazgo HIGH-2 y NIT-5)
`init` devuelve 7 campos (verificado en `get_initial_data`, **asumiendo** reconciliado
el blocker §4.0): `dc_creator`, `dc_publisher`, `dc_type`, `dc_format`, `dc_date`,
`dc_language` (`"es"`), `dc_title_sugerido`.

Correcciones respecto a v1:
- **`dc_creator` NO es el usuario autenticado.** `get_initial_data` **hardcodea**
  `usuario_nombre = "Sistema"` (con `# TODO: from authentication context`) y devuelve
  `dc_creator: "Sistema"` (verificado). Por tanto **NO** se usa `init.dc_creator` para
  pre-rellenar `dc.creador`. El wizard **conserva** su default `creador: usuario?.nombre
  ?? ""` (verificado en `UploadWizard.tsx`). (Hallazgo HIGH-2.)
- **`dc_title_sugerido` puede ser "Sin título".** `get_initial_data` usa
  `instrumento.nombre or instrumento.archivo_nombre or "Sin título"`; para instrumentos
  sembrados `InstrumentoProcesado` no tiene `nombre` ni `archivo_nombre` (verificado:
  el modelo real carece de ambos; el nombre vive en `RawData.nombre_archivo`). Tras
  reconciliar §4.0, el título debería venir de `RawData.nombre_archivo`; mientras no se
  reconcilie, el título sugerido cae en "Sin título". (Hallazgo NIT-5.) El pre-rellenado
  es best-effort: si `dc_title_sugerido` llega vacío/"Sin título", el campo `dc.titulo`
  del wizard queda editable por el usuario.

Pre-rellenado efectivo (sin rediseñar el formulario `StepDublinCore`):
- `dc.titulo` ← `dc_title_sugerido` **solo si** no es "Sin título"/vacío; si no, se
  deja lo que el usuario escriba.
- `dc.creador` ← **NO se toca** (se conserva `usuario?.nombre`).
- `dc.fecha` ← `dc_date`.
- `dc.idioma` ← mapear `"es"` → "Español" (la UI usa "Español").
Los demás (`tema`, `descripcion`, `derechos`, `cobertura`) los captura el usuario.

### 4.4 Registro (POST), creador explícito e inmutabilidad (CORREGIDO)
`register_dc` registra los 13 campos DC; es **inmutable**: una 2ª llamada → 409
(verificado). **El `dc_creator` lo envía el frontend**: `register_dc` lee
`request.get("dc_creator", "Sistema")` y lo persiste tal cual (verificado). Por eso el
payload DEBE incluir `dc_creator` con el creador real; si se omite se persiste
"Sistema". (Hallazgo HIGH-2.)

Mapeo UI → payload (dueño del mapeo: `carga.ts`):
- `dc_title` ← `dc.titulo`
- `dc_creator` ← `dc.creador` (**AÑADIDO** por HIGH-2; p. ej. `usuario?.nombre`)
- `dc_subject` ← `dc.tema` dividido por comas → `string[]`. Para inst_01, `dc:subject`
  real es `"calidad académica, exigencia, estándares, …"` (verificado), que al dividir
  da la lista esperada. ⚠️ **Importante (hallazgo MEDIUM-1):** `dc.tema` **NO** está en
  la guarda `puedeContinuar[2]` del wizard (ver §4.5), así que puede llegar **vacío**;
  en ese caso `dc_subject` se envía como `[]` y el backend lo persiste con 200 (no
  valida). Si se desea `dc_subject` obligatorio, es un edit acotado del wizard
  (`puedeContinuar[2] += "&& !!dc.tema.trim()"`, ver §4.5 y §12).
- `dc_description` ← `dc.descripcion`
- `dc_coverage` ← `dc.cobertura`
- `dc_rights` ← `dc.derechos`
- `dc_source`, `dc_relation`: no hay campo en el formulario actual → se omiten
  (opcionales). TODO: si se quieren capturar, ampliar el form (fuera de alcance).

Invariante de inmutabilidad: lo **posee el backend** (409 en 2ª llamada), porque es
regla de dominio persistida. El frontend sólo debe **no reintentar** un registro ya
hecho y mapear el 409 a mensaje claro.

### 4.5 Validación / errores (paso 3) — CORREGIDO (resuelve hallazgos MEDIUM-1 y MEDIUM-3)
Hecho verificado: `register_dc` recibe `request: dict` (sin modelo Pydantic) y lee
`dc_subject` con `request.get("dc_subject", [])`; **no valida obligatoriedad** de
`dc_title`/`dc_subject` → acepta vacío/`null` y responde **200**. **No hay 422.**

**Qué valida realmente el wizard (verificado en `UploadWizard.tsx`, hallazgo
MEDIUM-1):** la guarda del paso Dublin Core es
```ts
// puedeContinuar[2]  (índice de estado paso === 2)
!!dc.titulo.trim() && !!dc.creador.trim() && !!dc.descripcion.trim() && !!dc.cobertura
```
Es decir, el wizard exige LOCALMENTE **`titulo`, `creador`, `descripcion` y
`cobertura`**. **`dc.tema` (= `dc_subject`) NO está en la guarda**, así que puede
avanzar vacío. Por tanto **no existe ninguna validación local que garantice
`dc_subject` no vacío**; con la UI actual un `dc_subject: []` llega al POST y el
backend lo persiste con 200. La afirmación de la revisión 1 ("validación local sustituye
a la del servidor para `dc_subject`") era falsa y queda corregida aquí.

Decisión de esta revisión: **`dc_subject` NO se declara obligatorio** (se respeta el
comportamiento actual del wizard, que no lo exige; el backend tampoco). Si en una
iteración futura se requiere obligatorio, el cambio es un edit acotado del wizard
—añadir `&& !!dc.tema.trim()` a `puedeContinuar[2]`— listado como ítem opcional en §12.

| Condición | Recuperable | Caller recibe | Log |
|---|---|---|---|
| `titulo`/`creador`/`descripcion`/`cobertura` vacíos | sí | **El wizard no deja avanzar** (`puedeContinuar[2]`, validación LOCAL de esos 4 campos). | no |
| `dc_subject`/`tema` vacío | sí | **NO está en la guarda** → avanza; se envía `dc_subject: []`; el backend lo persiste con **200** (no valida). No aplica 422. | no |
| 2º registro (ya existe) | no | `ErrorHttp status=409` → "Los metadatos ya fueron registrados y son inmutables." | no |
| 404 instrumento inexistente | no | `ErrorHttp status=404` → "Instrumento no encontrado." | no |
| 500 (AttributeError §4.0 si no se reconcilia) | no | `Error` genérico | consola |
| 5xx | reintentar | `Error` genérico | consola |

Resumen del invariante: la obligatoriedad de `titulo`/`creador`/`descripcion`/`cobertura`
es **del wizard** (guarda local); el backend no valida ninguno de los 13 campos DC. No
hay garantía de servidor para ningún requerido y una garantía de servidor sería un
cambio de dominio fuera de alcance. Mapeo status→mensaje español en `carga.ts` leyendo
`ErrorHttp.status`.

---

## 5. API Gateway — proxy del metadata-service

### 5.1 Qué se añade (en `services/api-gateway/proxy/proxy.py`)
Rutas passthrough nuevas, forwardeando el path **tal cual** a
`SERVICES["metadata"]` (= `http://metadata-service:8003`, verificado). Siguiendo el
patrón exacto de iteración 1 (status+body del upstream, Authorization passthrough, sin
envoltorio, rutas base + `{path:path}` para evitar el 307 de FastAPI):

```python
@router.get("/api/metadata")
@router.get("/api/metadata/{path:path}")
async def metadata_get(request, path=""):
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "GET")

@router.post("/api/metadata")
@router.post("/api/metadata/{path:path}")
async def metadata_post(request, path=""):
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "POST")

@router.delete("/api/metadata")
@router.delete("/api/metadata/{path:path}")
async def metadata_delete(request, path=""):
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "DELETE")

# idéntico para /api/enrichment (prioridad menor; mismo patrón)
```
Como el frontend llamará a `/api/metadata/metadata/{id}/init`, el proxy capturará
`path = "metadata/{id}/init"` y reenviará `/api/metadata/metadata/{id}/init` AS-IS al
metadata-service, que lo resuelve con su doble prefijo (§4.1). El doble `metadata`
queda contenido y correcto.

(Nota: el helper real de construcción de ruta y la firma de `proxy_request` deben
replicar los de los prefijos ya existentes en `proxy.py`; se usa el mismo mecanismo
que `/instrumentos/*` y `/almacenamiento/*` sin inventar firmas.)

### 5.2 Decisión: proxy en gateway vs `METADATA_URL` directo
Se elige **proxy en el gateway** (puerta única), NO una `METADATA_URL` directa.
Rationale:
- Mantiene el patrón de iteración 1: una sola puerta HTTP, passthrough de
  `Authorization` y de status reales (401/404/409).
- Evita exponer :8003 al navegador y añadir CORS/otra base URL.
- `/vectorizacion/*` es la única excepción directa (ya establecida por `espacio.ts`).
Consecuencia: `client.ts` **no** cambia; metadatos usa `API_URL`.

### 5.3 Qué NO se toca
No se proxea `/vectorizacion/*` (sigue directo a ANALYSIS_URL). Se preservan intactas
`/auth/*`, `/instrumentos/*`, `/almacenamiento/*`, `/rag/*`, `/health` (verificadas).

### 5.4 Errores del proxy
El proxy ya reenvía status+body del upstream transparentemente (verificado). Un
upstream caído produce excepción httpx → 500 del gateway; el front lo trata como
`Error` genérico. No se añade manejo especial (coherente con el resto).

---

## 6. Paso 4 — Asociación de KPIs (`carga.ts` → `/vectorizacion/*`, ANALYSIS_URL directo)

Este es el hueco principal de la iteración. Dos llamadas secuenciales con decisión
humana entre ambas (verificado en `vectorizacion.py` y schemas).

### 6.1 Propuestas — `getKpisSugeridos` + `proponerKpis`
Firma estable: `getKpisSugeridos(_descripcion: string): Promise<KpiSugerido[]>`.
La propuesta real necesita **JSON del instrumento + .md original + tipo +
id_instrumento**, no sólo una descripción. La firma no cambia; se añade una función
nueva explícita y `getKpisSugeridos` queda como **stub de compatibilidad**.

**Comportamiento único fijado (resuelve hallazgo MEDIUM-4/NIT-4, mismo criterio que
§3.1).** La invocación actual del `useEffect`
`if (paso === 5 && !sugeridos) getKpisSugeridos(dc.descripcion).then(setSugeridos)`
(verificado en `UploadWizard.tsx`) **se REEMPLAZA** por una llamada a `proponerKpis({
idInstrumento, archivoJson, instrumentoOriginal, tipo })` (ver §8, ítem 4 y §12). No
se deja ambigua: tras el reemplazo, `getKpisSugeridos` **queda exportada por
compatibilidad de firma pero SIN invocador** (ningún camino del wizard la llama), de
modo que su `[]` nunca produce un paso de KPIs vacío "silencioso". Su cuerpo devuelve
`[]` con un TODO que indica que la propuesta real la produce `proponerKpis` y que esta
función ya no se llama desde el wizard. Firma y uso:
```ts
// carga.ts  (nueva)
export async function proponerKpis(args: {
  idInstrumento: number;              // id_instrumento (§1.1)
  archivoJson: File | Blob;           // el inst_XX.v1.json
  instrumentoOriginal: File | Blob;   // el inst_XX.md
  tipo: TipoInstrumento;              // mapeado a enum backend
}): Promise<KpiSugerido[]>
```
Endpoint (verificado): `POST /vectorizacion/propuestas` (multipart) contra
`ANALYSIS_URL`. Campos del form (verificados):
`archivo_json` (UploadFile), `instrumento_original` (UploadFile),
`tipo_instrumento` (Form), `id_instrumento` (Form int).
Auth: `/vectorizacion/*` usa `get_current_user`, y con `AUTH_DEV_MODE=True`
(verificado en `shared/db/core/config.py` + `dependencies.py`) resuelve `DEV_USER_ID`
**sin token**. Igual que `espacio.ts`, se llama **sin** Authorization. Multipart con
`fetch`+`FormData`. MIME: `archivo_json` como `application/json`,
`instrumento_original` como `text/markdown` (verificado en `post_propuestas.ps1`,
HTTP 200).

Respuesta `200` → `PropuestasResponse` (verificado):
```
{ id_instrumento, tipo_instrumento, metadatos_clave:{str:str},
  propuestas:[{ kpi_id:int, nombre_kpi:str, categoria?:str|null,
               ambito?:str|null, score:float }], mensaje }
```

### 6.2 Mapeo `PropuestaKPI` → `KpiSugerido` (verificado contra el shape real)
`KpiSugerido` (de `types/index.ts`): `{ id:string; nombre:string; coincidencia:number }`.
`StepKpis.tsx` usa `k.id`, `k.nombre`, `k.coincidencia` (barra 0-100). Mapeo:
- `id` ← `String(kpi_id)`,
- `nombre` ← `nombre_kpi`,
- `coincidencia` ← `Math.round(score * 100)` (score ∈ [0,1]).
`categoria`/`ambito` no tienen destino en `KpiSugerido` (3 campos) → se descartan;
TODO: ampliar el tipo si se quieren mostrar (fuera de alcance).

### 6.3 Confirmar — `confirmarKpis` (nueva)
```ts
export interface DecisionKpiApi { kpiId: number; aceptado: boolean; score?: number }
export async function confirmarKpis(args: {
  idInstrumento: number;                       // id_instrumento (§1.1)
  decisiones: DecisionKpiApi[];
  jsonInstrumento: Record<string, unknown>;    // el mismo JSON del instrumento
}): Promise<{ kpisAgregados: {kpiId:number; nombreKpi:string; score?:number}[];
             jsonEnriquecido: Record<string, unknown> }>
```
Endpoint (verificado): `POST /vectorizacion/confirmar` (JSON) contra `ANALYSIS_URL`.
Payload `ConfirmarRequest` (verificado): `{ id_instrumento:int,
decisiones:[{kpi_id:int, aceptado:bool, score?:float}], json_instrumento:dict }`.
JSON + sin auth ⇒ `pedir(`${ANALYSIS_URL}/vectorizacion/confirmar`,
{method:"POST", body, auth:false})`. Respuesta `ConfirmarResponse` (verificado):
`{ id_instrumento, kpis_agregados:[{kpi_id, nombre_kpi, score?}],
json_enriquecido:dict (añade clave 'inferred_kpis'), mensaje }`.
Mapeo salida: `kpi_id→kpiId`, `nombre_kpi→nombreKpi`, `json_enriquecido→jsonEnriquecido`.

El wizard construye `decisiones` desde su estado `decisiones: Record<string,
DecisionKpi>` (verificado): por cada sugerido `k`,
`{ kpi_id: Number(k.id), aceptado: estado[k.id]==="aceptado", score: k.coincidencia/100 }`.
`json_instrumento` = contenido parseado de `inst_XX.v1.json`.

### 6.4 `guardarInstrumento` — qué significa "guardar"
Firma estable: `guardarInstrumento(documento: unknown): Promise<{ id: string }>`.
`storage-service` expone `/almacenamiento/*` por el gateway (verificado en `proxy.py`),
pero el contrato `POST /almacenamiento/json?tipo=analysis` **no está verificado** (no
se leyó el router de storage-service). Decisión honesta:
- El "guardado" real del paso 4 es el `json_enriquecido` que devuelve `confirmarKpis`
  (el `/confirmar` persiste los KPIs aceptados en BD). Es decir, **confirmar ya es el
  "guardar"** del dominio de KPIs.
- `guardarInstrumento` conserva su firma; su cuerpo devuelve `{ id: String(idInstrumento) }`
  con el id real (en vez del `ins-${Date.now()}` del mock), con **TODO explícito**: "si
  se requiere persistir `json_enriquecido` como artefacto en storage-service, cablear
  `POST /almacenamiento/...` tras verificar su contrato real (router no leído)".
⚠️ Suposición a validar: contrato de storage-service `/almacenamiento/json` no
verificado; pendiente.

### 6.5 Validación / errores (paso 4)
| Operación | Condición | Recuperable | Caller recibe | Log |
|---|---|---|---|---|
| propuestas | sin KPIs sembrados / sin reindex | sí (sembrar) | `propuestas: []` o 4xx | consola |
| propuestas | 5xx (Chroma/embeddings caído) | reintentar | `Error` | consola |
| propuestas | `id_instrumento` inexistente | no | 4xx `detail` | — |
| confirmar | id inexistente | no | 4xx `detail` | — |
| confirmar | decisiones vacías | sí | 200 con `kpis_agregados: []` | — |
Si `propuestas` devuelve lista vacía, `StepKpis` muestra la grilla vacía (no es
error). Entrada validada: `score∈[0,1]`, `kpi_id` entero, `tipo_instrumento` del
vocabulario cerrado (§2.3).

---

## 7. Dashboard de KPIs (`kpis.ts`) — qué se cablea y qué queda mock

| Función | Estado | Fuente real / razón |
|---|---|---|
| `getCatalogoKpis(): Promise<KpiCatalogo[]>` | **cableada (parcial, con fallback)** | `GET /instrumentos/kpis/catalogo` (gateway, `auth:true`) → `list[str]` (verificado en `instrument-service/app/routers/list.py`). |
| `getKpis(): Promise<Kpi[]>` | **queda mock** | No existe endpoint de KPIs de tablero. |
| `getNoticias(): Promise<Noticia[]>` | **queda mock** | No existe endpoint de noticias. |
| `getDatosGrafica(kpiId, fuenteIds)` | **queda mock** | No existe endpoint de datos de gráfica. |

### 7.1 `getCatalogoKpis` — mapeo `list[str]` → `KpiCatalogo[]` + fallback (resuelve NIT-7)
El backend devuelve sólo **nombres** (`list[str]`, unión de KPIs de los instrumentos;
verificado). `KpiCatalogo` es más rico (`id, nombre, descripcionCorta, queEs, queMide,
comoSeMide, formula, infoGeneral, icono, etiquetas[]`). Mapeo honesto (cada string →
un `KpiCatalogo`):
- `id` ← slug del nombre (`nombre.toLowerCase().replace(/\s+/g,"-")`),
- `nombre` ← el string,
- `descripcionCorta/queEs/queMide/comoSeMide/formula/infoGeneral` ← `""` con **TODO**:
  "sin fuente en backend; `tt_rag.kpi` tiene descripcion/categoria/ambito/formula, pero
  no hay endpoint que los exponga — falta `GET /instrumentos/kpis/catalogo-detallado`".
- `icono` ← valor por defecto (p. ej. `"ChartBar"`),
- `etiquetas` ← `[]`.

**Fallback decidido (NIT-7):** `/instrumentos/kpis/catalogo` puede venir **vacío**
(antes de confirmar KPIs). Regla fijada: **si la respuesta tiene `length === 0`, se
degrada a `simularRed()` (mock)** para no dejar la página en blanco; si tiene ≥1
elemento, se mapea la fuente real. (Decisión única, no "o/o".)

### 7.2 Las otras tres funciones (mock + TODO)
Quedan en `simularRed` con TODO que nombra el endpoint faltante:
- `getKpis`: `// TODO: no hay endpoint de KPIs de tablero (p. ej. GET /kpis/tablero).`
- `getNoticias`: `// TODO: no hay endpoint de noticias (p. ej. GET /noticias).`
- `getDatosGrafica`: `// TODO: no hay endpoint de datos de gráfica (p. ej. GET /kpis/{id}/datos?instrumentIds=...).`
No se inventa ninguno.

---

## 8. Cambios acotados en el wizard (`UploadWizard.tsx`)

El cableado exige encadenar ids/archivos reales. Cambios mínimos (sin rediseñar
UI/estilos/pasos):
1. Nuevo estado: `idInstrumento: number | null`, `idCrudo: number | null`,
   `jsonInstrumento: Record<string,unknown> | null`, `archivoOriginal: File | null`.
2. Paso 0→1: al confirmar el archivo se llama `subirInstrumento(archivo, tipo,
   archivoOriginal)` → guarda `idInstrumento`, `idCrudo` y hace `setReporte(reporte
   real)` ANTES de avanzar. **Se elimina la invocación de `limpiarArchivo` del
   `useEffect` del paso 1** (§3.1), de modo que el reporte proviene sólo del upload.
   - El `archivoOriginal` opcional `.md`: `StepArchivo` hoy acepta un solo archivo.
     Añadir un 2º input sería cambio de UI mayor → en esta iteración `archivoOriginal`
     se pasa `undefined` en el flujo real; para la demo con instrumentos sembrados se
     usa la ruta §8.b.
3. Paso 3 (Dublin Core): al entrar, `getMetadatosInit(idInstrumento)` para pre-rellenar
   **sin tocar `dc.creador`** (§4.3). Al salir/"Guardar", `registrarMetadatos(idInstrumento,
   { ..., dc_creator: dc.creador })` (incluye el creador real, §4.4).
4. Paso KPIs (`paso === 5`): **sustituir** la invocación `getKpisSugeridos(dc.descripcion)`
   del `useEffect` por `proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal,
   tipo })` (reemplazo explícito, §6.1; `getKpisSugeridos` queda sin invocador). ⚠️ Ver
   §8.c: `archivoJson`/`instrumentoOriginal` **sólo existen por la ruta de artefactos
   sembrados**; en el flujo de upload puro no hay fuente para ellos.
5. Paso Guardar (`paso === 6`): `confirmarKpis(...)` con `decisiones` reales y
   `jsonInstrumento`, luego `guardarInstrumento` (id real). Toast y navegación
   existentes se conservan.

### 8.c Alcance real del paso de KPIs — SÓLO ejecutable con artefactos sembrados (resuelve NIT-5)

Declaración explícita (recorte honesto, coherente con el resto del diseño): el paso de
KPIs (`paso === 5`) y el confirmar del paso Guardar **sólo son ejecutables con los
artefactos sembrados** `storage/raw/inst_XX.v1.json` (el `archivoJson`) y
`storage/raw/inst_XX.md` (el `instrumentoOriginal`). **El flujo de upload puro NO
produce esos artefactos**: `POST /instrumentos/upload` sólo devuelve `UploadResponse`
(con `parseo`), nunca un JSON de instrumento enriquecido (verificado en §2.1/§2.6, y
confirmado por la revisión). En consecuencia:
- En el flujo de upload normal (`.csv`/`.pdf`), `archivoJson` **queda sin fuente** →
  `proponerKpis` no se puede invocar end-to-end desde el upload; el paso de KPIs se
  **omite / queda mock** con un TODO que nombra la carencia (no hay endpoint que
  devuelva el JSON enriquecido tras el upload).
- El paso de KPIs **sólo** es demostrable por la **ruta de demo** (§8.b): se cargan los
  artefactos sembrados y se pasa el `id_instrumento` resuelto (§1.1). Esta es la única
  forma de ver propuestas/confirmar reales en esta iteración.

Esto es idéntico en espíritu a los demás recortes honestos (limpieza derivada,
dashboard mock): se cablea lo que tiene fuente real y se declara explícitamente lo que
no la tiene, sin inventar endpoints.

### 8.a Mapeo `DecisionKpi` (UI) → `decisiones` (API)
`StepKpis` maneja `decisiones: Record<string,"aceptado"|"rechazado">` (verificado). En
confirmar: por cada `k`, `{ kpi_id: Number(k.id), aceptado: estado[k.id]==="aceptado",
score: k.coincidencia/100 }`.

### 8.b Ruta de demo con instrumentos sembrados (archivos .md/.json) — IDs corregidos
El upload no acepta `.json/.md` (§2.6). Para demostrar pasos 3-4 con artefactos reales:
- Se necesita **`id_instrumento`** (no `id_crudo`). `_seed_map.json` guarda `id_crudo`
  (§1.1), así que: (A) ampliar `seed_demo.py` para persistir también `id_instrumento`,
  o (B) asumir BD recién sembrada (`id_crudo==id_instrumento==N`) dejándolo escrito.
- `archivoJson` = contenido de `storage/raw/inst_NN.v1.json`;
  `instrumentoOriginal` = `storage/raw/inst_NN.md`.
Decisión: dejar el camino de upload intacto para archivos soportados y documentar que
la **verificación** del paso 4 se hace llamando `proponerKpis`/`confirmarKpis`
directamente con el `id_instrumento` correcto (como hace `post_propuestas.ps1`, pero
usando el id resuelto, no `$n` a ciegas). Si se quiere botón de demo en UI, es un
cambio adicional a decidir aparte (fuera del cableado core).

---

## 9. Prerrequisitos de siembra y reindexado (para la verificación)

Verificado en `.agents/tasks/chroma-viz/scratch/`:
- `seed_kpis.sql`: filas `INSERT INTO tt_rag.kpi (nombre_kpi, descripcion, categoria,
  ambito, formula)` con `TRUNCATE ... RESTART IDENTITY CASCADE` (idempotente). Puebla
  `tt_rag.kpi`, que alimenta las propuestas.
- `instrument-service/scripts/seed_demo.py`: siembra raw_data + instrumento_procesado
  y escribe `storage/raw/_seed_map.json` (**`inst_XX → id_crudo`**, verificado). Para
  la demo de metadatos/KPIs hay que resolver `id_instrumento` (§1.1); **recomendado**
  ampliar el seed para persistir también `id_instrumento`.
- `_seed_map.json` **no existe aún** en el worktree → ejecutar el seed en la demo.

Comandos exactos (requieren Postgres + servicios levantados; en el entorno de demo):
1. `docker compose up -d postgres chromadb` (+ servicios instrument/analysis/metadata/
   gateway según el compose).
2. Sembrar instrumentos (desde `services/instrument-service/`):
   `python scripts/seed_demo.py` → filas + `storage/raw/_seed_map.json`.
3. Sembrar KPIs: `psql "$DATABASE_URL" -f .agents/tasks/chroma-viz/scratch/seed_kpis.sql`
   (o `docker compose exec -T postgres psql -U postgres -d indagata_db -f -` por stdin).
4. Reindexar la colección de KPIs (una vez tras sembrar):
   `POST ${ANALYSIS_URL}/vectorizacion/kpis/reindex` →
   `ReindexResponse { coleccion:"kpis", n_kpis, mensaje }`. P. ej.
   `curl -s -X POST http://localhost:8002/vectorizacion/kpis/reindex`.
5. (Humo) reproducir `post_propuestas.ps1`, **pero** pasando el `id_instrumento`
   resuelto (§1.1), no `$n` a ciegas, para confirmar HTTP 200.

⚠️ Si `tt_rag.kpi` está vacío o no se reindexa, `/vectorizacion/propuestas` devuelve
`propuestas: []` y el paso 4 se ve vacío (no es error de cableado).
⚠️ El paso 3 (metadatos) además requiere reconciliar `dc_manager` (§4.0) antes de que
`init`/`register` respondan 200.

---

## 10. Testabilidad

Unitario (sin backend):
- `mapearParseoALimpieza(parseo)`: casos tabular (headers), documento (n_chars/n_words)
  y `parseo=null`. Verificar forma `ReporteLimpieza`.
- Mapeo `PropuestaKPI → KpiSugerido` (`score→coincidencia`, `kpi_id→String`).
- Mapeo `KpiCatalogo` desde `list[str]` (slug, campos vacíos) y **fallback a mock con
  lista vacía** (§7.1).
- Mapeo `tipo` UI→enum backend y `DecisionKpi`→`decisiones`.
- Propagación de ids: que metadatos/KPIs reciben `id_instrumento` y no `id_crudo`.
Se testean mockeando `fetch`/`pedir`.

Integración (con servicios + seed):
- upload real de un `.csv` soportado → 201 + parseo coherente + ambos ids.
- `init` + `register` de metadatos (y 2º register → 409) — **sólo tras reconciliar
  §4.0**.
- `proponerKpis` + `confirmarKpis` con `id_instrumento` sembrado → `inferred_kpis`.
- gateway: `GET /api/metadata/metadata/{id}/init` llega al servicio (doble segmento
  preservado) con status/body transparentes.
Difícil de unit-testear: SSE del chat (fuera de alcance) y el multipart extremo a
extremo (se cubre con integración).

---

## 11. Suposiciones no verificadas y blockers (a validar en implementación/verificación)

1. **BLOCKER §4.0 — `dc_manager` referencia atributos inexistentes**
   (`InstrumentoProcesado.instrumento_id/.nombre/.archivo_nombre/.tipo_instrumento/.ruta_archivo`
   y `MetadatosDC.instrumento_id`). Verificado contra `shared/models/*`. El paso 3 no
   funciona (500) sin reconciliar `dc_manager`. **Decisión RESUELTA (ya no pendiente):
   esta iteración INCLUYE el arreglo mínimo de `dc_manager`** (§4.0), como prerequisito
   obligatorio del paso 3. No es una pregunta abierta.
2. **DDL de `metadatos_dc`** (PK real en Postgres): no se leyó el schema SQL; se asume
   que coincide con el modelo `shared` (`id_crudo` PK). Pendiente.
3. **storage-service `/almacenamiento/json?tipo=analysis`**: contrato no verificado;
   `guardarInstrumento` no lo cablea (§6.4).
4. **MIME en multipart del navegador**: `application/json`/`text/markdown` tomados de
   `post_propuestas.ps1`; en `fetch`+`FormData` el `File` del navegador puede diferir →
   enviar `Blob`/`File` con `type` explícito.
5. **`dc_language` "es" ↔ UI "Español"**: mapear al pre-rellenar.
6. **Catálogo de KPIs potencialmente vacío** antes de confirmar (§7.1): mitigado con
   fallback a mock.
7. **Auth del metadata-service**: endpoints sólo dependen de `get_db` (verificado); el
   Bearer que reenvía el proxy es inofensivo.
8. **IDs de la demo** (§1.1): `id_crudo==id_instrumento` sólo en BD recién truncada;
   recomendado persistir ambos en `_seed_map.json`.

---

## 12. Archivos a tocar (checklist de implementación)

Frontend (`.worktrees/cablear-pipeline/pixel-perfect-pixel/src/`):
- [ ] `api/carga.ts`: cuerpos de `limpiarArchivo`, `getKpisSugeridos`,
  `guardarInstrumento` (firmas intactas) + nuevas `subirInstrumento`,
  `getMetadatosInit`, `registrarMetadatos`, `proponerKpis`, `confirmarKpis` + helper
  `mapearParseoALimpieza` + constante `TIPO_UI_A_BACKEND`.
- [ ] `api/kpis.ts`: cuerpo de `getCatalogoKpis` (real + fallback a mock si vacío);
  TODOs en `getKpis`, `getNoticias`, `getDatosGrafica`.
- [ ] `features/upload/UploadWizard.tsx`: estado de ids/archivos; `subirInstrumento`
  con `setReporte` antes de avanzar; **eliminar la llamada a `limpiarArchivo` del
  `useEffect` (`paso === 1`)**; **reemplazar la llamada a `getKpisSugeridos` del
  `useEffect` (`paso === 5`) por `proponerKpis`** (deja `getKpisSugeridos` sin
  invocador, §6.1/NIT-4); `getMetadatosInit` sin tocar `dc.creador`;
  `registrarMetadatos` con `dc_creator`; `confirmarKpis`; sin tocar estilos ni
  estructura.
- [ ] *(OPCIONAL — sólo si se quiere `dc_subject` obligatorio, §4.5)*
  `features/upload/UploadWizard.tsx`: añadir `&& !!dc.tema.trim()` a `puedeContinuar[2]`.
  No se aplica en esta iteración (se respeta el comportamiento actual del wizard).
- [ ] `api/client.ts`: **sin cambios**.

Backend (`.worktrees/cablear-pipeline/services/`):
- [ ] `api-gateway/proxy/proxy.py`: añadir passthrough `/api/metadata` (+`{path:path}`)
  y `/api/enrichment` (+`{path:path}`) para GET/POST/DELETE → `SERVICES["metadata"]`.
- [ ] `api-gateway/proxy/proxy.py`: **actualizar el docstring y el párrafo de
  "Prefijos passthrough"** que dicen que metadata "NO se proxea" (resuelve NIT-6).
- [ ] **(OBLIGATORIO — prerequisito del paso 3, §4.0)**
  `metadata-service/services/dc_manager.py`: reconciliar con los modelos reales en
  `get_initial_data`/`register_dc`/`get_dc`/`delete_dc` — filtrar `InstrumentoProcesado`
  por `id_instrumento`; obtener `tipo_instrumento`/`nombre_archivo` por lookup/join a
  `RawData` vía `id_crudo`; usar `ruta_json`/`ruta_de_archivo_limpio`; filtrar/crear
  `MetadatosDC` por `id_crudo`; eliminar `instrumento.nombre = …`. (Decisión resuelta;
  ya NO pendiente de scope.)
- [ ] *(recomendado, §1.1/§8.b)* `instrument-service/scripts/seed_demo.py`: persistir
  también `id_instrumento` en `_seed_map.json`.

Sin otros cambios de dominio en instrument/analysis-service (sólo cableado).

---

## 13. Respuesta a los hallazgos de revisión

### 13.A — Revisión actual (`design-review.json`, veredicto CHANGES_REQUESTED: 2 MEDIUM + 3 NIT)

Esta es la revisión que condiciona el veredicto actual. Cada hallazgo se resuelve en el
cuerpo y se lista aquí.

| # | Sev | Resolución | Dónde |
|---|---|---|---|
| 1 | MEDIUM | **Resuelto (corregido hecho incorrecto).** `puedeContinuar[2]` valida LOCALMENTE `titulo/creador/descripcion/cobertura`, **NO** `dc.tema` (= `dc_subject`) — verificado en `UploadWizard.tsx`. Se corrige la afirmación: no hay validación local que garantice `dc_subject`; con la UI actual puede llegar `[]` y el backend lo persiste con 200. Tabla de errores rehecha (fila `dc_subject` separada). Decisión: **no se declara obligatorio** `dc_subject` (se respeta la UI actual); si se requiriera, es un edit acotado (`&& !!dc.tema.trim()`) listado como ítem OPCIONAL en §12. | §4.4, §4.5, §12 |
| 2 | MEDIUM | **Resuelto (decisión tomada).** Se elimina la ramificación "según confirme el usuario". Coherente con "cablea todo", **esta iteración INCLUYE el arreglo mínimo de `dc_manager.py`** (reconciliar `id_instrumento`, lookup a `RawData` por `id_crudo`, `MetadatosDC.id_crudo`, usar `ruta_json`). Instrucción única y acotada para el implementador; marcado OBLIGATORIO en §11/§12. | §4.0, §11.1, §12 |
| 3 | NIT | **Resuelto.** Añadida tabla de equivalencia de pasos (§0.1): "Paso N de 7" (etiqueta UI) ↔ índice de estado `paso = N-1`. Dublin Core = `paso === 2`, KPIs = `paso === 5`, limpieza = `paso === 1`. Las guardas se citan por índice. | §0.1 |
| 4 | NIT | **Resuelto (mismo criterio que §3.1).** Declarado explícitamente que la invocación de `getKpisSugeridos` en el `useEffect` (`paso === 5`) **se REEMPLAZA** por `proponerKpis`; `getKpisSugeridos` queda como stub de compatibilidad **sin invocador** (su `[]` nunca produce un paso vacío silencioso). Añadido como ítem concreto del checklist. | §6.1, §8 (ítem 4), §12 |
| 5 | NIT | **Resuelto.** Declarado explícitamente que el paso de KPIs **sólo** es ejecutable con los artefactos sembrados (`inst_XX.v1.json` + `.md`); en el flujo de upload puro `archivoJson` **queda sin fuente** → se omite/mock con TODO, recorte honesto coherente con el resto. | §8.c, §8.b |

### 13.B — Revisión previa (histórico; hallazgos ya incorporados en el cuerpo)

| # | Sev | Resolución | Dónde |
|---|---|---|---|
| 1 | HIGH | **Resuelto.** `_seed_map.json` mapea `inst_XX → id_crudo`; metadatos/KPIs requieren `id_instrumento` (PK de `instrumento_procesado`), que NO es necesariamente igual a `id_crudo`. Se añade regla de IDs explícita y propagación por el wizard; para la demo se resuelve `id_instrumento` (recomendado: persistirlo en el seed_map) o se condiciona la igualdad a BD recién truncada. Verificado en `seed_demo.py` y los modelos ORM. | §1.1, §2.6, §8.b |
| 2 | HIGH | **Resuelto.** `init.dc_creator` es "Sistema" hardcodeado (verificado en `dc_manager.get_initial_data`), NO el usuario; ya NO se usa para pre-rellenar `dc.creador` (se conserva `usuario?.nombre`). Se **añade** `dc_creator ← dc.creador` al payload del POST para persistir el creador real (`register_dc` lo lee del body). | §4.3, §4.4 |
| 3 | MEDIUM | **Resuelto.** `register_dc` recibe `request: dict` sin validación → acepta vacío/`null` y responde 200; NO hay 422. La obligatoriedad de `dc_title`/`dc_subject` es sólo del wizard (`puedeContinuar[2]`). Tabla de errores corregida (fila 422 → "no aplica"). | §4.5 |
| 4 | MEDIUM | **Resuelto.** Comportamiento único fijado: `subirInstrumento` hace `setReporte(reporte real)` ANTES de avanzar y **se elimina la invocación de `limpiarArchivo` del `useEffect`** del paso 1 (ya no hay "o/o"). El reporte real nunca se sobrescribe. | §3.1, §8 |
| 5 | NIT | **Resuelto/anotado.** `InstrumentoProcesado` no tiene `nombre` ni `archivo_nombre` (verificado en el modelo real); el nombre vive en `RawData.nombre_archivo`. Para instrumentos sembrados el título sugerido cae en "Sin título" mientras no se reconcilie `dc_manager` (§4.0). Pre-rellenado best-effort (no se escribe título si llega "Sin título"). | §4.3, §4.0 |
| 6 | NIT | **Resuelto.** Actualizar el docstring de `proxy.py` y el párrafo de "Prefijos passthrough" es ahora un ítem explícito del checklist. | §12 |
| 7 | NIT | **Resuelto.** Fallback decidido: si `/instrumentos/kpis/catalogo` devuelve `length === 0`, `getCatalogoKpis` degrada a `simularRed()` (mock) para no dejar la página en blanco; con ≥1 elemento usa la fuente real. | §7.1 |

**Hallazgo nuevo (surgió en la revisión previa, confirmado por la actual):** la
verificación en frío de `dc_manager` contra los modelos ORM reales reveló que el
`metadata-service` referencia atributos inexistentes (`instrumento_id`, `nombre`,
`archivo_nombre`, `tipo_instrumento`, `ruta_archivo`), por lo que `init`/`register`/`get`
fallan con 500 contra el esquema real. Es un prerequisito de backend para el paso 3,
documentado en §4.0/§11/§12. **La decisión de alcance quedó RESUELTA en la revisión
actual (hallazgo MEDIUM-2 de §13.A): el arreglo mínimo de `dc_manager` se incluye como
obligatorio en esta iteración** (ya no es una decisión abierta para el usuario).
