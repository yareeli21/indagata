# Plan de implementación — Cablear el pipeline de carga (pasos 1-4) al backend real

Iteración 2. Cablear los pasos 1-4 del asistente de carga (subir → limpieza →
metadatos Dublin Core → asociación de KPIs) a los microservicios reales, más el
proxy de `metadata-service` en el api-gateway. Fuente de verdad: `design.md`
(aprobado, veredicto APPROVED). Todo se trabaja EXCLUSIVAMENTE en el worktree
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\cablear-pipeline` (rama
`cablear-pipeline`). El checkout principal queda intacto.

Idioma: toda la interfaz, rutas de dominio e identificadores visibles permanecen en
español. Las firmas exportadas de `pixel-perfect-pixel/src/api/*.ts` NO cambian; solo
se cambia el cuerpo de funciones y se añaden funciones nuevas. Los cambios en
`UploadWizard.tsx` son mínimos y acotados (sin rediseñar UI/estilos/pasos). No se
inventan endpoints: los flujos sin fuente real quedan mock con TODO explícito.

## Hechos verificados en el worktree (base del plan)

- Frontend: Vite 8 + React 19 + TanStack Router, gestor **Bun 1.4.2** (hay `bun.lock`).
  **No existe framework de tests** (no hay vitest ni jest en `package.json`).
  `node_modules` **no está instalado** en el worktree → hay que instalar antes de
  compilar. Verificación de front = typecheck (`tsc --noEmit`), build (`vite build`)
  y lint (`eslint`).
- `src/api/client.ts`: `pedir()` fuerza `Content-Type: application/json` (sirve para
  JSON, NO para multipart). `API_URL` (gateway :8000), `ANALYSIS_URL` (:8002),
  `leerToken()`, `ErrorHttp.status`. Multipart = `fetch`+`FormData`+Bearer (patrón de
  `chat.ts`). No se toca `client.ts`.
- `src/api/carga.ts` hoy: `limpiarArchivo`, `getKpisSugeridos`, `guardarInstrumento`
  (todas mock vía `simularRed`).
- `src/api/kpis.ts` hoy: `getKpis`, `getNoticias`, `getCatalogoKpis`, `getDatosGrafica`
  (todas mock).
- `UploadWizard.tsx`: `useEffect` con
  `if (paso === 1 && archivo && !reporte) limpiarArchivo(archivo).then(setReporte)` y
  `if (paso === 5 && !sugeridos) getKpisSugeridos(dc.descripcion).then(setSugeridos)`.
  `puedeContinuar[2] = !!dc.titulo.trim() && !!dc.creador.trim() &&
  !!dc.descripcion.trim() && !!dc.cobertura`. `dc.tema` (= `dc_subject`) NO está en la
  guarda. Default `creador: usuario?.nombre ?? ""`.
- Backend upload (`instrument-service/app/routers/upload.py` + `schemas/upload.py`):
  `POST /instrumentos/upload` multipart (`archivo`, `tipo_instrumento`,
  `archivo_original?`), role-gated → necesita Bearer; 201 → `UploadResponse` con
  **ambos** `id_crudo` e `id_instrumento` + `archivo_respondido.parseo`.
- Gateway (`api-gateway/proxy/proxy.py`): proxea `/instrumentos/*`, `/almacenamiento/*`,
  `/rag/*`. `metadata` **NO** se proxea aún (docstring lo dice). `SERVICES["metadata"]
  = http://metadata-service:8003`. Helpers `_ruta_upstream`, `proxy_request`,
  `_headers_reenvio` (conserva Authorization). Patrón: ruta base + `{path:path}`.
- Metadatos (`metadata-service/routers/metadata.py` + `main.py`): router
  `prefix="/metadata"` con decoradores `/metadata/{instrumento_id}/init`, montado con
  `prefix="/api"` → rutas reales con **doble** `metadata`:
  `/api/metadata/metadata/{id}/init`, `POST /api/metadata/metadata/{id}`, etc. Los
  endpoints solo dependen de `get_db` (sin auth propia). `register` recibe `request: dict`
  (sin Pydantic): no valida obligatoriedad; vacío/omitido → 200 (salvo `dc_title`, que es
  NOT NULL en modelo y DDL).
- **BLOCKER backend confirmado** (`metadata-service/services/dc_manager.py` vs
  `shared/models/*`): `dc_manager` usa atributos inexistentes y filtra por claves
  equivocadas, por lo que `init`/`register`/`get`/`delete` fallan con 500 contra el
  esquema real (ver paso 4 abajo). `shared/models/instrumento_procesado.py` → PK
  `id_instrumento`, FK `id_crudo`, `ruta_json`, `ruta_de_archivo_limpio`, `estado`,
  fechas (NO `instrumento_id`/`nombre`/`archivo_nombre`/`tipo_instrumento`/`ruta_archivo`).
  `shared/models/raw_data.py` → `tipo_instrumento`, `nombre_archivo`.
  `shared/models/metadatos_dc.py` → PK `id_crudo`, `dc_title` NOT NULL.
- **BUG adicional detectado (no listado en design.md)**: `register_dc` hace
  `instrumento.estado = "metadata_registrado"`, pero el CHECK de `instrumento_procesado`
  (en el modelo ORM y en `infrastructure/postgres/init/01_schema.sql`) solo admite
  `'metadatos_registrados'` (plural, con 's'). Con el valor actual la inserción viola
  el CHECK → IntegrityError → 500, incluso tras arreglar los atributos. El arreglo de
  `dc_manager` DEBE corregir también el valor de `estado` a `'metadatos_registrados'`.
- DDL (`infrastructure/postgres/init/01_schema.sql`): `metadatos_dc` PK `id_crudo`
  (coincide con el modelo `shared`); `instrumento_procesado` CHECK de `estado` incluye
  `'metadatos_registrados'`. Confirma la suposición §11.2 del diseño.
- Vectorización (`analysis-service/app/vectorization/routers/vectorizacion.py` +
  `schemas/vectorizacion.py`): `POST /vectorizacion/propuestas` multipart (`archivo_json`,
  `instrumento_original`, `tipo_instrumento`, `id_instrumento`), auth `get_current_user`
  (modo dev resuelve sin token). `POST /vectorizacion/confirmar` JSON (`ConfirmarRequest`:
  `id_instrumento`, `decisiones[{kpi_id,aceptado,score?}]`, `json_instrumento`). Respuestas
  `PropuestasResponse`/`ConfirmarResponse` según §6. `POST /vectorizacion/kpis/reindex`.
- Catálogo (`instrument-service/app/routers/list.py`): `GET /instrumentos/kpis/catalogo`
  role-gated → `list[str]` (unión de KPIs). `GET /instrumentos/{id}` usa `id_crudo`.
- `services/TESTING.md`: verificación backend sin levantar todo = TestClient de FastAPI
  (forma #1) desde la carpeta del servicio con el venv del repo
  (`c:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe`); realista con
  `uvicorn` + `docker compose up -d postgres` (forma #2); integración con
  `docker compose up -d` (forma #3). En local `POSTGRES_HOST=localhost`.

## Regla de IDs (CRÍTICA — propaga id_crudo e id_instrumento por separado)

`subirInstrumento` devuelve AMBOS ids. El wizard los guarda por separado:
- **`id_instrumento`** → metadatos (paso 3) y KPIs (paso 4).
- **`id_crudo`** → instrument-service (listados/detalle).

---

# Orden de ejecución

El orden hace fluir el `id_crudo`/`id_instrumento` reales desde la carga hacia limpieza,
metadatos y KPIs, y agrupa el proxy del gateway con el cableado de metadatos. Cada ítem
deja el worktree compilable. Los ítems backend (3-4) y frontend (5-9) son en gran parte
independientes entre sí salvo las dependencias indicadas; se ordenan para que las bases
(cliente de upload, ids) existan antes de sus consumidores.

- [ ] 1. **Instalar dependencias del frontend** para poder compilar/typechear.
      Ejecutar la instalación una vez en el worktree del front; es prerequisito de toda
      verificación de TypeScript (no hay `node_modules`).
      Files: *(ninguno; solo genera `pixel-perfect-pixel/node_modules`)*
      Verify: desde `pixel-perfect-pixel/`, `bun install` termina sin error y
      `bunx tsc --noEmit` compila el proyecto actual sin errores (línea base verde antes
      de tocar código).

- [ ] 2. **Añadir el proxy de `metadata-service` en el api-gateway.**
      En `services/api-gateway/proxy/proxy.py` añadir rutas passthrough GET/POST/DELETE
      para `/api/metadata` (+ `/api/metadata/{path:path}`) y, con el mismo patrón, para
      `/api/enrichment`, reenviando el path tal cual a `SERVICES["metadata"]` con
      `_ruta_upstream("/api/metadata", path)` / `_ruta_upstream("/api/enrichment", path)`
      y `proxy_request(...)`, replicando exactamente el patrón de `/instrumentos/*`
      (ruta base + `{path:path}` para evitar el 307). Actualizar el docstring del módulo
      y el párrafo "Prefijos passthrough" para que ya no digan que metadata "NO se proxea".
      Así `/api/metadata/metadata/{id}/init` se reenvía AS-IS preservando el doble segmento.
      Files: `services/api-gateway/proxy/proxy.py`
      Verify: desde `services/api-gateway/`, prueba TestClient en memoria (forma #1 de
      TESTING.md) con el venv del repo: montar `main.app`, mockear/omitir el upstream y
      confirmar que las rutas `GET/POST/DELETE /api/metadata/...` y `/api/enrichment/...`
      existen en `app.routes` (no 404 de ruta no registrada). Borrar el script smoke al
      terminar. Alternativa de integración (forma #3): `docker compose up -d` y
      `GET http://localhost:8000/api/metadata/metadata` llega al servicio.

- [ ] 3. **Reconciliar `dc_manager.py` con los modelos reales (arreglo obligatorio del
      backend de metadatos, prerequisito del paso 3 del wizard).**
      En `services/metadata-service/services/dc_manager.py`, en `get_initial_data`,
      `register_dc`, `get_dc` y `delete_dc`:
      1. Filtrar `InstrumentoProcesado` por **`id_instrumento`** (no `instrumento_id`).
         El path param del router sigue llamándose `instrumento_id` pero se usa como
         valor de `id_instrumento`.
      2. Obtener `tipo_instrumento` y el nombre del archivo con lookup/join a `RawData`
         por `instrumento.id_crudo`: `tipo_instrumento ← RawData.tipo_instrumento`;
         título sugerido ← `RawData.nombre_archivo` (en vez de
         `instrumento.tipo_instrumento` / `.nombre` / `.archivo_nombre`, inexistentes).
      3. Para `dc_format` usar `instrumento.ruta_json` o `instrumento.ruta_de_archivo_limpio`
         (no `instrumento.ruta_archivo`, inexistente).
      4. Filtrar/crear `MetadatosDC` por **`id_crudo`** (PK real), resolviendo `id_crudo`
         desde el `InstrumentoProcesado` cargado (no `MetadatosDC.instrumento_id`).
         Eliminar el `instrumento.nombre = …` del `register_dc` (atributo inexistente).
      5. **Corregir el valor de estado**: `instrumento.estado = "metadatos_registrados"`
         (plural, con 's'), para no violar el CHECK de `instrumento_procesado` (ver hechos
         verificados). No cambiar el contrato HTTP ni la forma de respuesta.
      Files: `services/metadata-service/services/dc_manager.py`
      Verify: desde `services/metadata-service/`, prueba TestClient en memoria (forma #1)
      con el venv del repo y una sesión fake/override de `get_db`, o integración (forma #2):
      `docker compose up -d postgres`, sembrar un `instrumento_procesado`, y comprobar que
      `GET /api/metadata/metadata/{id_instrumento}/init` responde **200** (no 500) y que
      `POST /api/metadata/metadata/{id_instrumento}` persiste y responde 200, y un 2.º POST
      devuelve 409. Confirmar que `estado` queda en `'metadatos_registrados'` sin error de
      CHECK. Borrar cualquier script smoke al terminar.

- [ ] 4. **Cablear el paso 1 (subir) + derivar la limpieza en `carga.ts`.**
      En `pixel-perfect-pixel/src/api/carga.ts`:
      - Añadir constante `TIPO_UI_A_BACKEND` (`"Encuesta"→"encuesta"`,
        `"Entrevista"→"entrevista"`, `"Prueba estandarizada"→"prueba_estandarizada"`).
      - Añadir helper puro `mapearParseoALimpieza(parseo)` según §3.2 (columnas =
        `headers.length ?? 0`; duplicados/nulos = 0 con comentario de que no hay etapa de
        limpieza con esos conteos; `cambios` derivados de headers/documento/notes; `null`
        → `cambios: []`).
      - Añadir `subirInstrumento(archivo, tipo, archivoOriginal?)` → `ResultadoCarga`
        (`{ idCrudo, idInstrumento, reporte }`), vía `fetch(`${API_URL}/instrumentos/upload`)`
        multipart+Bearer (`leerToken()`), mapeando AMBOS ids y derivando `reporte` con
        `mapearParseoALimpieza(archivo_respondido.parseo)`. Mapear errores a mensajes
        español por `status` (401/403/4xx/5xx) según §2.5.
      - Reemplazar el cuerpo de `limpiarArchivo(_archivo)` (firma intacta) para que
        devuelva un `ReporteLimpieza` honesto derivado solo del `File` (ceros, `cambios:[]`)
        con comentario de que el reporte real lo produce `subirInstrumento`.
      Files: `pixel-perfect-pixel/src/api/carga.ts`
      Verify: desde `pixel-perfect-pixel/`, `bunx tsc --noEmit` sin errores (firmas y tipos
      correctos). Confirmar que `limpiarArchivo` y `getKpisSugeridos`/`guardarInstrumento`
      conservan su firma exportada.

- [ ] 5. **Cablear el paso 3 (metadatos Dublin Core) en `carga.ts`.**
      Depende del proxy del gateway (ítem 2). En `pixel-perfect-pixel/src/api/carga.ts`
      añadir `MetadatosInit`, `getMetadatosInit(idInstrumento)` (GET
      `${API_URL}/api/metadata/metadata/${idInstrumento}/init`, `pedir({auth:true})`) y
      `RegistroMetadatos`, `registrarMetadatos(idInstrumento, datos)` (POST
      `${API_URL}/api/metadata/metadata/${idInstrumento}`, `pedir({method:"POST", auth:true})`).
      Incluir el **doble `metadata`** con comentario para que no se "corrija". El payload del
      POST DEBE incluir `dc_creator` (creador real). Mapear 409/404/500 a mensajes español
      por `ErrorHttp.status` (§4.5).
      Files: `pixel-perfect-pixel/src/api/carga.ts`
      Verify: desde `pixel-perfect-pixel/`, `bunx tsc --noEmit` sin errores. (Integración
      real del init/register se cubre en el ítem 3 y en la verificación de runtime.)

- [ ] 6. **Cablear el paso 4 (asociación de KPIs) en `carga.ts`.**
      En `pixel-perfect-pixel/src/api/carga.ts`:
      - `proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal, tipo })` → POST
        `${ANALYSIS_URL}/vectorizacion/propuestas` multipart (`fetch`+`FormData`, auth:false,
        campos `archivo_json`/`instrumento_original`/`tipo_instrumento`/`id_instrumento`),
        enviando `Blob`/`File` con `type` explícito (`application/json`, `text/markdown`).
        Mapear `PropuestaKPI → KpiSugerido` (`id=String(kpi_id)`, `nombre=nombre_kpi`,
        `coincidencia=Math.round(score*100)`).
      - `confirmarKpis({ idInstrumento, decisiones, jsonInstrumento })` → POST
        `${ANALYSIS_URL}/vectorizacion/confirmar` JSON (`pedir({method:"POST", auth:false})`),
        payload `ConfirmarRequest`; mapear salida (`kpi_id→kpiId`, `nombre_kpi→nombreKpi`,
        `json_enriquecido→jsonEnriquecido`).
      - Reemplazar el cuerpo de `getKpisSugeridos(_descripcion)` (firma intacta) para que
        devuelva `[]` con TODO de que la propuesta real la hace `proponerKpis` y que ya no
        se invoca desde el wizard.
      - Reemplazar el cuerpo de `guardarInstrumento(documento)` (firma intacta) para que
        devuelva `{ id: String(idInstrumento) }` con el id real; dado que la firma recibe
        solo `documento`, mantener la firma y documentar con TODO que el "guardado" de
        dominio es el `json_enriquecido` de `confirmarKpis` y que persistir en
        storage-service requiere verificar el contrato real de `/almacenamiento/*` (router
        no leído). *(Si el wizard necesita el id real, lo obtiene del estado tras
        `confirmarKpis`; `guardarInstrumento` no cambia de firma.)*
      Files: `pixel-perfect-pixel/src/api/carga.ts`
      Verify: desde `pixel-perfect-pixel/`, `bunx tsc --noEmit` sin errores.

- [ ] 7. **Cablear `getCatalogoKpis` con fallback y marcar las demás de `kpis.ts`.**
      En `pixel-perfect-pixel/src/api/kpis.ts`, reemplazar el cuerpo de `getCatalogoKpis`
      (firma intacta): GET `${API_URL}/instrumentos/kpis/catalogo` con `pedir({auth:true})`
      → `list[str]`; mapear cada string a `KpiCatalogo` (`id` = slug, `nombre` = string,
      campos de texto `""` con TODO del endpoint detallado faltante, `icono` por defecto,
      `etiquetas: []`); **si la respuesta tiene `length === 0`, degradar a `simularRed()`
      (mock)**. Añadir TODO en `getKpis`, `getNoticias`, `getDatosGrafica` nombrando el
      endpoint faltante (quedan mock). No inventar endpoints.
      Files: `pixel-perfect-pixel/src/api/kpis.ts`
      Verify: desde `pixel-perfect-pixel/`, `bunx tsc --noEmit` sin errores.

- [ ] 8. **Encadenar ids/archivos y llamadas reales en `UploadWizard.tsx` (cambios
      mínimos).** Depende de los ítems 4-7.
      En `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`:
      - Nuevo estado: `idInstrumento`, `idCrudo`, `jsonInstrumento`, `archivoOriginal`.
      - Paso 0→1: al confirmar el archivo, llamar `subirInstrumento(archivo, tipo,
        archivoOriginal ?? undefined)`, guardar `idInstrumento`/`idCrudo` y hacer
        `setReporte(resultado.reporte)` ANTES de avanzar. **Eliminar del `useEffect` la
        invocación `limpiarArchivo(archivo).then(setReporte)` del `paso === 1`** (el
        reporte real ya viene del upload). Mantener el manejo de error/toast existente.
      - Paso 3 (Dublin Core, `paso === 2`): al entrar, `getMetadatosInit(idInstrumento)`
        para pre-rellenar `dc.titulo` (solo si el sugerido no es vacío/"Sin título"),
        `dc.fecha` ← `dc_date`, `dc.idioma` ← mapear `"es"`→"Español"; **NO tocar
        `dc.creador`** (se conserva `usuario?.nombre`). Al salir del paso, `registrarMetadatos(
        idInstrumento, { dc_title, dc_creator: dc.creador, dc_subject: dc.tema dividido por
        comas → string[], dc_description, dc_coverage, dc_rights })`.
      - Paso KPIs (`paso === 5`): **sustituir** en el `useEffect` la invocación
        `getKpisSugeridos(dc.descripcion).then(setSugeridos)` por
        `proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal, tipo }).then(setSugeridos)`.
        Como `archivoJson`/`instrumentoOriginal` solo existen por la ruta de artefactos
        sembrados (§8.c), en el flujo de upload puro quedan sin fuente: dejar el paso
        omitido/mock con TODO que nombre la carencia (no hay endpoint que devuelva el JSON
        enriquecido tras el upload). No romper el render de `StepKpis` cuando `sugeridos`
        es `null` o `[]`.
      - Paso Guardar (`paso === 6`): construir `decisiones` reales desde `decisiones`
        (`{ kpi_id: Number(k.id), aceptado: estado[k.id]==="aceptado", score: k.coincidencia/100 }`),
        llamar `confirmarKpis({ idInstrumento, decisiones, jsonInstrumento })` y luego
        `guardarInstrumento(documento)` (conserva toast y navegación).
      - No tocar estilos, estructura de pasos ni `puedeContinuar` (se respeta que
        `dc_subject` no es obligatorio, §4.5).
      Files: `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`
      Verify: desde `pixel-perfect-pixel/`, `bunx tsc --noEmit` sin errores y
      `bun run build` (vite build) termina correctamente; `bun run lint` sin errores nuevos.

- [ ] 9. **Verificación integral de front** (puerta final de construcción del frontend).
      Depende de todos los ítems de frontend (4-8).
      Files: *(ninguno)*
      Verify: desde `pixel-perfect-pixel/`, en orden: `bunx tsc --noEmit` (sin errores),
      `bun run build` (build de producción OK) y `bun run lint` (sin errores). Confirmar
      que las firmas de `limpiarArchivo`, `getKpisSugeridos`, `guardarInstrumento`,
      `getCatalogoKpis`, `getKpis`, `getNoticias`, `getDatosGrafica` no cambiaron.

---

## Flujos que quedan mock/omitidos (recortes honestos, con TODO explícito)

- Limpieza: no hay endpoint propio; se deriva del `parseo` del upload (ítem 4).
- Paso de KPIs end-to-end desde upload puro: el upload no produce JSON enriquecido; solo
  es demostrable con artefactos sembrados `storage/raw/inst_XX.v1.json` + `inst_XX.md`
  (§8.b/§8.c). Queda omitido/mock con TODO en el flujo de upload puro.
- `getKpis`, `getNoticias`, `getDatosGrafica` (dashboard): sin endpoint → mock + TODO.
- `guardarInstrumento`: persistir `json_enriquecido` en storage-service queda como TODO
  (contrato de `/almacenamiento/json` no verificado).
- `seed_demo.py` persistir `id_instrumento` en `_seed_map.json`: recomendado para la demo
  (§1.1/§8.b) pero es cambio del script de siembra, no del runtime; fuera del cableado core.

## Nota sobre verificación de runtime (gate del workflow)

La verificación de runtime (gate `verification.json passed==true`) debe apoyarse en los
procedimientos de `services/TESTING.md`: forma #1 (TestClient en memoria con el venv del
repo) para el gateway (ítem 2) y para `dc_manager` (ítem 3) sin levantar todo, y, cuando
se requiera integración real (init/register 200, propuestas/confirmar con instrumentos
sembrados), forma #2/#3 con `docker compose up -d postgres` (+ servicios) y
`POST /vectorizacion/kpis/reindex` tras sembrar `tt_rag.kpi` (§9). El frontend se verifica
con `bunx tsc --noEmit` + `bun run build` + `bun run lint`.

---

## Registro de verificación (iteración 2 — implementación)

Ejecutado en el worktree `cablear-pipeline`:

- **Build frontend (gate):** `bun install` (395 paquetes) + `bun run build` (`vite build`)
  → las tres fases transforman y compilan (`✓ built`: 2641 + 150 + 2614 módulos). El
  `exit code 1` es un comportamiento PRE-EXISTENTE de nitro/vite-start en Windows (ya
  presente en la línea base antes de tocar código, con el build igualmente `✓ built`),
  no un fallo de compilación.
- **Type-check frontend:** `bunx tsc --noEmit` reporta ÚNICAMENTE 6 errores PRE-EXISTENTES
  en `src/api/client.ts` y `src/api/chat.ts` (TS4111/TS2769 por `exactOptionalPropertyTypes`),
  archivos NO tocados en esta iteración (`client.ts` es "sin cambios"). Mis tres archivos
  (`carga.ts`, `kpis.ts`, `UploadWizard.tsx`) compilan con **0 errores** nuevos. En
  `carga.ts` se usó notación de corchete para `headers["Authorization"]` para no reproducir
  el patrón TS4111.
- **Firmas estables confirmadas:** `limpiarArchivo(File)→Promise<ReporteLimpieza>`,
  `getKpisSugeridos(string)→Promise<KpiSugerido[]>`, `guardarInstrumento(unknown)→Promise<{id:string}>`,
  `getCatalogoKpis()→Promise<KpiCatalogo[]>`, `getKpis`, `getNoticias`, `getDatosGrafica`
  sin cambios de firma.
- **Lint:** `bun run lint` falla con ~11.7k errores `prettier/prettier` "Delete `␍`"
  (fin de línea CRLF↔LF) repartidos por TODO el repo, incluido `vite.config.ts`. Es una
  condición PRE-EXISTENTE y repo-amplia (no introducida por esta iteración); no es un
  error de lógica/tipos de los archivos tocados.
- **Backend `dc_manager` (reconciliación, ítem 3):** smoke TestClient en memoria (SQLite
  con `ATTACH DATABASE ':memory:' AS tt_rag`, override de `get_db`, venv del repo,
  TESTING.md forma #1) sobre `metadata-service/main.app`. Resultado `SMOKE_OK` (exit 0):
  `GET /api/metadata/metadata/{id}/init` → **200** (`dc_type` desde `RawData`,
  `dc_format` desde `ruta_json`, título desde `RawData.nombre_archivo`);
  `POST /api/metadata/metadata/{id}` → **200** con `estado: 'metadatos_registrados'` y
  `dc_creator` enviado por el frontend persistido; 2.º POST → **409** (inmutable por
  `id_crudo`); `GET` → **200**; `DELETE` → **200**. Ningún `AttributeError`/500. El script
  smoke se borró al terminar.
- **Backend gateway (proxy, ítem 2):** smoke TestClient en memoria (forma #1) sobre
  `api-gateway/main.app` → `ROUTES_OK`: registradas `/api/metadata`,
  `/api/metadata/{path:path}`, `/api/enrichment`, `/api/enrichment/{path:path}`. El script
  smoke se borró al terminar.
- **Pendiente de runtime (step dedicado):** integración extremo-a-extremo con Docker
  (`docker compose up -d`), siembra (`seed_demo.py` + `seed_kpis.sql`) y
  `POST /vectorizacion/kpis/reindex` para propuestas/confirmar reales (§9). Fuera del
  alcance de este step (solo código correcto + build limpio).
