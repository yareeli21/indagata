# Revisión de diseño — Front/Back completo + RAG (iteración 3)

Documento revisado: `.agents/tasks/fullstack-rag/design.md`
Worktree de código: `.worktrees/fullstack-rag`
Revisor: subagente de revisión de diseño (sin contexto previo de generación)

Esta es la 3.ª iteración del diseño. Las dos afirmaciones falsas de la iteración
anterior (esquema JSON de instrumento y existencia de metadata-service) **se
verificaron directamente contra el repo y ahora son correctas**. La gran mayoría
de las afirmaciones del diseño resisten la verificación. Quedan, sin embargo,
hallazgos concretos — principalmente en la capa frontend (riesgo (d)) y un par de
inconsistencias/omisiones — que deben cerrarse antes de implementar.

---

## Áreas de riesgo evaluadas

- (a) Contratos de servicio (storage, visualization index/chat): esquemas
  request/response concretos y consistentes.
- (b) Reutilización real de `embeddings.py` / `chroma_client.py` (coseno,
  normalizado); naming de colección + chunking + llamada a Ollama por httpx.
- (c) Proxy del gateway transparente (status+JSON) acorde a cómo `pedir()` consume.
- (d) Plan de frontend mantiene firmas exportadas y evita cambios de UI/estilo.
- (e) Nombres reales de settings (`CHROMA_*`, `OLLAMA_*`, `*_PATH`), no inventados.

---

## Hallazgos

### HIGH

**1. [HIGH] (riesgo d) El plan reescribe la lógica del `useEffect` que puebla
`instrumentosFuentes` y afirma que es "visualmente idéntico", pero cambia los datos
que se renderizan y crea una dependencia circular sin estado inicial definido.**

Ubicación: §8.3 ("El `useEffect` que hoy llena `instrumentosFuentes` de forma
simulada se mantiene visualmente idéntico; solo deja de ser aleatorio al
leer/escribir esta clave").

Verificado contra `pixel-perfect-pixel/src/features/chat/ChatPage.tsx`:

```ts
useEffect(() => {
  if (!activa) return;
  getInstrumentos().then((todos) => {
    const propios = todos.filter((i) => i.autorId === miId).slice(0, 3);
    const ajenos = todos.filter((i) => i.autorId !== miId).slice(0, 2);
    setInstrumentosFuentes([...propios, ...ajenos]);
  });
}, [activa, miId]);
```

Problemas concretos:
- La lógica actual **NO es aleatoria**: es un filtro determinista (3 propios + 2
  ajenos). El diseño la describe como "aleatoria/simulada", lo cual es inexacto y
  oscurece el impacto real del cambio.
- `instrumentosFuentes` alimenta directamente `<ChipsFuentes instrumentos=
  {instrumentosFuentes} .../>`. Cambiar su fuente de datos (de "3 propios + 2
  ajenos" a "lo persistido en `indagata.instrumentosPorInvestigacion`") **cambia
  qué chips se muestran** — eso es un cambio de comportamiento de UI, no solo de
  datos. La afirmación "visualmente idéntico" no se sostiene.
- Dependencia circular sin arranque definido: §8.3 dice que `handleComenzar`
  **arma** la lista desde `instrumentosFuentes` y la persiste vía
  `guardarContexto`; pero si el `useEffect` ahora **lee** de la misma clave de
  localStorage, en el primer uso (clave vacía) `instrumentosFuentes` quedaría
  vacío y `handleComenzar` persistiría una lista vacía → el RAG indexaría 0
  instrumentos. El diseño no especifica el estado inicial de
  `instrumentosFuentes` cuando la clave aún no existe.

Fix concreto (elige una, documenta la elección):
- **Opción A (menor cambio, preferida):** NO tocar el `useEffect` ni su lógica de
  poblado (sigue llamando `getInstrumentos()` y filtrando 3+2). El único cambio en
  `ChatPage.tsx` es ampliar los **argumentos** de las dos llamadas existentes
  (`guardarContexto(activa.id, ctx, instrumentosFuentes.map(i => i.id))` y la
  llamada a `enviarMensaje`). `guardarContexto` persiste e indexa esa lista; el
  `useEffect` NO lee la clave. Así los chips se ven exactamente igual que hoy y el
  RAG recibe los ids que ya se muestran. Reescribe §8.3 para eliminar la frase
  "deja de ser aleatorio al leer/escribir esta clave".
- **Opción B:** si se quiere que el `useEffect` lea la clave, definir explícitamente
  el fallback: "si `getInstrumentosDeInvestigacion(activa.id)` devuelve `[]`, se
  conserva el poblado actual (3 propios + 2 ajenos) y se persiste de inmediato".
  Esto rompe el ciclo y preserva la vista inicial.

---

### MEDIUM

**2. [MEDIUM] (riesgo d) La heurística de `nivel` (§2.3a) puede emitir
`"Bachillerato"`, que NO es un valor válido de `NivelEducativo`.**

Ubicación: §2.3a ("`bachiller`/`preparatoria`/`media superior` → `"Bachillerato"`;
`posgrado`/`maestr`/`doctor` → el valor de posgrado correspondiente").

Verificado contra `pixel-perfect-pixel/src/types/index.ts`:

```ts
export const NIVELES_EDUCATIVOS = ["Licenciatura", "Posgrado"] as const;
export type NivelEducativo = (typeof NIVELES_EDUCATIVOS)[number];
```

`NivelEducativo` es una unión cerrada de **solo dos** valores:
`"Licenciatura" | "Posgrado"`. La heurística del diseño introduce `"Bachillerato"`
y habla de "el valor de posgrado correspondiente" (plural), ninguno de los cuales
es asignable a `NivelEducativo`. El `InstrumentoDTO` del backend que serializa
`nivel="Bachillerato"` produciría un valor que el frontend tipa como
`NivelEducativo` pero que no pertenece a la unión → inconsistencia de contrato
(el mismo tipo de bug que el diseño declara querer evitar con el mapeo cerrado de
`tipo` en §2.4).

Fix concreto: restringir la heurística al conjunto real
`{"Licenciatura", "Posgrado"}`:

```
contiene "posgrado"/"maestr"/"doctor"/"especialidad"  → "Posgrado"
en cualquier otro caso                                 → "Licenciatura"  (default)
```

Eliminar toda referencia a `"Bachillerato"` y a variantes de posgrado múltiples.
Documentar que `nivel` es `Literal["Licenciatura","Posgrado"]` en `InstrumentoDTO`,
igual que se hizo con `tipo` y `estado`.

**3. [MEDIUM] (riesgo d) El plan no especifica que `getInstrumento(id)` debe
preservar su retorno `Promise<Instrumento | null>` mapeando 404 → `null`.**

Ubicación: §8.1 ("`getInstrumento(id)` → `GET ${API_URL}/instrumentos/${id}` con
`{auth:true}`; aplica el mismo `mapear`") vs §9 (tabla: `GET /instrumentos/{id}` →
`InstrumentoDTO | 404`).

Verificado contra `pixel-perfect-pixel/src/api/instrumentos.ts`:

```ts
export function getInstrumento(id: string): Promise<Instrumento | null> {
  return simularRed(instrumentos.find((i) => i.id === id) ?? null);
}
```

La firma exportada actual devuelve `Instrumento | null`. El backend (§6) responde
`404` cuando no existe. `pedir()` **lanza** `ErrorHttp` con `status` en cualquier
no-2xx (verificado en `client.ts`), de modo que un 404 **no** se traduce
automáticamente a `null`: lanzaría excepción y rompería la firma/el contrato que
los consumidores esperan. El diseño "aplica el mismo `mapear`" pero no dice qué
pasa con el 404.

Fix concreto: en §8.1 especificar el manejo del 404:

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

Preserva la firma exportada `Promise<Instrumento | null>` sin cambios.

**4. [MEDIUM] (riesgo d) Riesgo de closure obsoleto: `handleEnviar` es un
`useCallback([contexto, modelo])` y el plan le añade `activa.id`, pero `activa` no
está en sus dependencias.**

Ubicación: §8.3 ("Llamada en `ChatPage.handleEnviar`: pasa `activa.id` (ya
disponible vía `useResearch()`)").

Verificado contra `ChatPage.tsx`:

```ts
const handleEnviar = useCallback((texto: string) => {
  ...
  const cancelar = enviarMensaje(texto, contexto, modelo, onToken, onDone);
  ...
}, [contexto, modelo]);
```

Si se añade `activa.id` dentro del cuerpo de `handleEnviar` sin añadir `activa` al
array de dependencias, el callback capturará un `activa` potencialmente obsoleto si
el usuario cambia de investigación activa sin que `contexto`/`modelo` cambien.
Puede enviar la pregunta a la colección equivocada. El diseño afirma "solo
argumentos, sin tocar JSX/estilo", pero omite el ajuste necesario del array de
dependencias — que es parte del cambio correcto y no afecta JSX ni estilo.

Fix concreto: en §8.3 indicar explícitamente que el array de dependencias de
`handleEnviar` pasa a `[contexto, modelo, activa]` (o `activa?.id`). Es un cambio
de lógica, no de UI; declararlo igual que ya se declaran los otros cambios
acotados de `ChatPage.tsx`.

---

### NIT

**5. [NIT] (riesgo a/e) El esquema de la base de datos vive en el schema
PostgreSQL `tt_rag`, no en `public`; el `scripts/seed_demo.py` nuevo (§2.8) que
inserta directo en `raw_data`/`instrumento_procesado` debe respetarlo.**

Verificado en `infrastructure/postgres/init/01_schema.sql`:
`CREATE SCHEMA IF NOT EXISTS tt_rag; SET search_path TO tt_rag, public;` y al final
`ALTER ROLE ... SET search_path TO tt_rag, public`. Los servicios acceden por ORM
(`shared`), así que funcionan; pero el seed propuesto en §2.8 inserta filas
directamente y debe fijar el `search_path`/schema correcto o usar los modelos de
`shared` para no fallar silenciosamente escribiendo en `public`.

Fix: §2.8 debe indicar que el seed usa los modelos ORM de `shared.models` (no SQL
crudo), o que fija `search_path=tt_rag` explícitamente.

**6. [NIT] (riesgo a) Inconsistencia menor de ruta de artefacto de JSON entre
`storage-service` (clave versionada por `instrumentoId`) y la realidad del repo
(`inst_XX`).**

§3.2 define la clave de storage como `<tipo>/<instrumentoId>/<version>__...` donde
`instrumentoId = str(id_crudo)`, pero los JSON reales existen como
`storage/raw/inst_XX.v1.json` (verificado). El diseño cubre esto con el fallback de
§2.8/§4.2 (resolución por `_seed_map.json` o `N → inst_{N:02d}`), así que no es
bloqueante; pero conviene una nota explícita de que, hasta correr el seed, el
`GET /almacenamiento/artefacto/analysis/<id>` del storage-service devolverá 404 y
el RAG dependerá del fallback a `storage/raw/`. Es coherente, solo falta decirlo en
§3.3/§4.2 para evitar confusión del implementador.

---

## Supuestos verificados (correctos contra el repo)

1. **Esquema JSON de instrumento** (§2.3): `storage/raw/inst_01.v1.json` tiene
   exactamente `instrument.title/objective/dimensions_explored`,
   `instrument.sections[].questions[].text/options`, `metadata.dublin_core[dc:*]`,
   `metadata.survey_specific.palabras_clave` (**7** elementos),
   `design_reference.kpi_hints` (**5** elementos), y **10** questions. Los números
   del test obligatorio (§2.3: `reactivos == 10`, `kpis` con 5, `etiquetas` con 7)
   son correctos. **VERIFICADO.**
2. **Columnas de `raw_data`** (§2.3): `id_crudo, id_owner, tipo_instrumento,
   nombre_archivo, raw_archivo, raw_archivo_original, fecha_carga`. Coincide con
   `01_schema.sql`. **VERIFICADO.**
3. **Columnas de `instrumento_procesado`** (§2.3): `id_instrumento, id_crudo,
   ruta_de_archivo_limpio, ruta_json, estado, fecha_procesamiento,
   fecha_aprobado`. Coincide. **VERIFICADO.**
4. **Valores de `estado`** (§2.5): el CHECK del schema lista exactamente
   `recibido, limpieza_en_proceso, limpio, metadatos_registrados, estandarizado,
   vectorizado, error`. El mapeo de §2.5 es consistente. **VERIFICADO.**
5. **`embeddings.py`** (§1, §4.1): `embed_texts`/`embed_text`, carga perezosa,
   `settings.EMBEDDING_MODEL`, `normalize_embeddings=True`. Copiable 1:1.
   **VERIFICADO.**
6. **`chroma_client.py`** (§4.3): `get_or_create_collection` con
   `{"hnsw:space": "cosine"}`, `upsert`, `query` (hoy **sin** `where`), `get_point`,
   `_lock`. La extensión aditiva `where=None` es necesaria y la afirmación de que
   NO es copia "1:1" (a diferencia de embeddings) es correcta. **VERIFICADO.**
7. **Proxy del gateway** (§5.1): `proxy_request` hoy devuelve
   `{status_code, body}`, tiene endpoints de ejemplo en inglés
   (`/instruments/upload`, `/instruments/{instrument_id}`), `except Exception →
   502`, y la función muerta `proxy_to_service` con `http://...:PORT/api`.
   **VERIFICADO.**
8. **`main.py` del gateway NO incluye el proxy router** (§5.2): solo
   `include_router(auth_router)`. Hay que añadir `include_router(proxy_router)`.
   **VERIFICADO.**
9. **`pedir()`** (§5.3): hace `fetch`, parsea JSON, fuerza
   `Content-Type: application/json`, mapea 401 y lee `detail` para otros status,
   adjunta `status` en `ErrorHttp`. El proxy transparente es la corrección
   correcta. **VERIFICADO.**
10. **`DELETE /instrumentos/{id_crudo}`** (§2.1, §6): existe en `delete.py`, keyea
    por `id_crudo`, exige `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)`.
    **VERIFICADO.**
11. **`POST /instrumentos/upload`** (§6): existe, `tipo_instrumento` Form,
    `archivo_original` opcional, mismo `require_rol`, devuelve `UploadResponse` con
    `id_crudo`/`id_instrumento`. **VERIFICADO.**
12. **`dependencies.py` del instrument-service** (§6): valida JWT siempre, "no hay
    bypass de desarrollo", NO consulta `AUTH_DEV_MODE`. **VERIFICADO.**
13. **`metadata-service` IMPLEMENTADO** (§2.3b, §5.2, §11, §12): `main.py` monta
    `metadata` y `enrichment` con `prefix="/api"`. La corrección de la afirmación
    falsa anterior es correcta. **VERIFICADO.**
14. **Settings reales** (§2.7, §4.2, §7): `RAW_PATH/JSON_PATH/SAV_PATH/TEMP_PATH` y
    `raw_path_abs/json_path_abs/sav_path_abs/temp_path_abs`; `CHROMA_HOST/PORT`
    (default 8008), `EMBEDDING_MODEL` (mpnet, 768), `OLLAMA_HOST/MODEL`;
    `STORAGE_PATH` **no** es campo; `INSTRUMENT_SERVICE_URL` **sí** es campo;
    `STORAGE_SERVICE_URL` **no** es campo (→ `os.getenv`); `AUTH_DEV_MODE=True` por
    defecto; `DEV_USER_ID=1`. Todo coincide con `shared/db/core/config.py`.
    **VERIFICADO.**
15. **Bloque `analysis-service` en compose** (§7): `depends_on [ollama, chromadb]
    (service_started)`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `CHROMA_HOST=chromadb`,
    `CHROMA_PORT=8000`, `EMBEDDING_MODEL` mpnet, `hf_cache:/root/.cache/
    huggingface`. El YAML copiado en §7 es fiel. El bloque actual de
    `visualization-service` carece de todo eso (solo tiene STORAGE/JSON/SAV_PATH).
    Volumen `hf_cache` declarado al final. **VERIFICADO.**
16. **chromadb** (§7): mapeo host `8008 → 8000` interno; `CHROMA_PORT=8000` dentro
    de Docker es correcto. **VERIFICADO.**
17. **Servicio `frontend` de compose** (§7): monta `./frontend` y expone 3000, no
    sirve `pixel-perfect-pixel/`. **VERIFICADO.**
18. **`ModeloLLM`** (§8.3): definido como
    `"gpt-4o" | "gpt-4o-mini" | "gemini-1.5-pro" | "claude-3-5-sonnet"`. Los únicos
    literales en componentes son `MODELOS_DISPONIBLES` (chat.ts) y
    `ChatPage.tsx` (`useState<ModeloLLM>("gpt-4o")`); `BarraEntrada.tsx` usa solo el
    tipo. La afirmación de §8.3 es correcta. **VERIFICADO.**
19. **`Instrumento`** (§8.1): interfaz de 12 campos exactos, **sin** `idProcesado`.
    El map campo a campo que descarta `idProcesado` es necesario. **VERIFICADO.**
20. **`FuenteChat.tipo`** (§2.4, §4.7): tipado como `TipoInstrumento` (unión
    cerrada), no `str`. El mapeo canónico y el `Literal` de `FuenteChatOut.tipo`
    son correctos. **VERIFICADO.**
21. **Firmas actuales de `chat.ts`** (§8.3): `enviarMensaje(_pregunta, _contexto,
    _modelo, onToken, onDone)` y `guardarContexto(_investigacionId, contexto)`;
    importan mocks de `@/mocks/data`. La ampliación de firmas propuesta y el
    de-mock son coherentes. **VERIFICADO.**
22. **`crearInvestigacion`/`getInvestigaciones`** (§8.2): hoy `res-${Date.now()}` y
    mock estático; migrables a localStorage sin cambio de firma. **VERIFICADO.**
23. **`espacio.ts`** (§1): llama `ANALYSIS_URL/vectorizacion/espacio` directo con
    `auth:false`; el gateway NO proxea `/vectorizacion/*`. **VERIFICADO.**
24. **`_sanitize_filename` / `eliminar`** (§2.7, §3.2, §3.5): existen en
    `local_backend.py`; `eliminar` usa `settings.raw_path_abs.parent` como raíz con
    defensa de path traversal (NFKD→ASCII→`[^..]→_`, trunc 120, fallback
    "archivo"). **VERIFICADO.**
25. **`ROL_INVESTIGADOR`/`ROL_ADMINISTRADOR`** (§6): `"investigador"` /
    `"administrador"` en `shared.auth`. **VERIFICADO.**
26. **`visualization-service/main.py`** (§4): stub health-only. **VERIFICADO.**
27. **`metadatos_dc`** (§2.3b): tiene `dc_title, dc_description, dc_subject,
    dc_coverage` (y 9 columnas DC más). **VERIFICADO.**

## Supuestos no verificados / fuera del repo

- **Formato NDJSON de `/api/generate` de Ollama** (§4.9, supuesto 13): contrato de
  un tercero, no verificable en el repo. El diseño lo declara como tal. Aceptable.
- **Comportamiento de Chroma con `where={"$in": [...]}`** (§4.3, §4.7): depende de
  la versión de `chromadb` en runtime; el patrón es estándar pero no se ejecutó.
  El propio diseño lo documenta como extensión aditiva; aceptable como supuesto.
- **Que el seed `inst_XX → id_crudo N`** produzca realmente `id_crudo` secuenciales
  1..21 (§2.8): depende del estado de la tabla al sembrar (SERIAL autoincrement).
  El fallback `N → inst_{N:02d}` solo es correcto si la DB está vacía antes del
  seed. No bloqueante (hay manifiesto `_seed_map.json`), pero es un supuesto de
  ejecución, no verificable estáticamente.

---

## Veredicto

Conteo: **1 HIGH + 3 MEDIUM + 2 NIT**.

Como hay hallazgos HIGH/MEDIUM (> 0), el veredicto es **CHANGES_REQUESTED**.

Los hallazgos se concentran en la capa frontend (riesgo d): el cambio al
`useEffect` que puebla las fuentes contradice el requisito de "no tocar la UI" y
tiene una dependencia circular sin estado inicial (HIGH 1); la heurística de
`nivel` emite un valor fuera de la unión `NivelEducativo` (MED 2); falta el manejo
de 404→null para preservar la firma de `getInstrumento` (MED 3); y falta ajustar
las dependencias del `useCallback` de `handleEnviar` para evitar un closure
obsoleto de `activa` (MED 4). Son correcciones acotadas y rápidas; el resto del
diseño (contratos de storage/RAG, reutilización de embeddings/Chroma, proxy
transparente, settings reales) está verificado y es sólido.
