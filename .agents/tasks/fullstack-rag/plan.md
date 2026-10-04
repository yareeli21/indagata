# Implementation Plan — Front/Back completo + RAG (worktree `fullstack-rag`)

Fuente de verdad: `.agents/tasks/fullstack-rag/design.md` (en el worktree). Si algo
aquí contradice el diseño, gana el diseño. Todo el trabajo ocurre en el worktree
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag` (rama
`fullstack-rag`, creada desde `pruebas`). Las rutas de código son **absolutas**
dentro del worktree. Los agentes corren con cwd = workspace principal, así que:

- Para git usa SIEMPRE `git -C c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag ...`.
- El Python del repo es `c:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe`
  (tiene `fastapi`, `httpx`, `sqlalchemy`, `chromadb`, `sentence_transformers`;
  **NO** tiene `pytest`). Por eso la verificación por defecto usa **smoke scripts
  con `TestClient`** (patrón de `services/TESTING.md` §1), que no requieren pytest
  ni Postgres. Si se prefiere pytest, instalarlo con
  `.venv\Scripts\python.exe -m pip install pytest` antes de usar `pytest`.
- Los smoke scripts se ejecutan desde la carpeta del servicio con
  `cwd=<...>\services\<svc>` y `-B` (sin `.pyc`), y se **borran** al terminar
  (archivos temporales de verificación).
- PowerShell encadena con `;` (no `&&`).
- Frontend: `pixel-perfect-pixel`; verificación con `npm run build` (hace
  typecheck vía `tsc`/plugin) y `npm run lint`. NO tocar JSX/estilos/layout.
- Todo el texto de dominio y los mensajes al usuario permanecen en **español**.

Convención de smoke scripts (forma #1 de TESTING.md): levantar `main.app` con
`TestClient`, sobreescribir `get_db`/`get_current_user` con fakes cuando el
endpoint toque BD o auth. No se requiere Postgres para las pruebas unitarias ni
de contrato en memoria.

---

## A. storage-service (:8004)

- [ ] 1. Crear los schemas Pydantic v2 del storage-service.
      Define `GuardarJsonRequest {instrumentoId:str, tipo:Literal["metadata","analysis"], contenido:dict[str,Any], nombre:str|None=None}`,
      `ArtefactoRef {key, tipo, instrumentoId:str|None, version:int, ruta_absoluta, ruta_relativa, size_bytes, nombre_original, creado:datetime}`,
      y `ArtefactoDetalle(ArtefactoRef) {contenido:dict[str,Any]|None=None}` (diseño §3.3).
      Archivos: crear `c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag\services\storage-service\app\__init__.py`,
      `...\services\storage-service\app\schemas\__init__.py`,
      `...\services\storage-service\app\schemas\almacenamiento.py`.
      Verify: desde `...\services\storage-service` corre
      `& "c:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe" -B -c "from app.schemas.almacenamiento import GuardarJsonRequest, ArtefactoRef, ArtefactoDetalle; print('ok')"` → imprime `ok`.

- [ ] 2. Crear el núcleo de almacenamiento (`core/index.py` + `core/store.py`).
      `index.py`: helper `_sanitize_filename` (copiado 1:1 de
      `services\instrument-service\app\storage\local_backend.py`: NFKD→ASCII,
      `[^A-Za-z0-9._-]→_`, trunca 120, fallback `"archivo"`), `slug(nombre)` para el
      `<slug>` de la clave, un `threading.Lock` de módulo, y el manifiesto JSON en
      `settings.json_path_abs/_index/artefactos.json` con lectura/escritura atómica
      (`.part`+`replace`) y cálculo de `version` autoincremental por `(tipo, instrumentoId)`
      (diseño §3.2/§3.6). `store.py`: `resolver_directorio(tipo)` →
      `raw→raw_path_abs, sav→sav_path_abs, metadata|analysis→json_path_abs, temp→temp_path_abs`;
      `guardar_bytes`/`guardar_json` con escritura atómica; `leer_json`;
      verificación de que la clave resuelta queda DENTRO de la raíz de storage
      (`settings.raw_path_abs.parent`, defensa path-traversal como en `local_backend.eliminar`).
      Tipos válidos: `{raw, sav, metadata, analysis, temp}` (sin `json` genérico, §3.2).
      Archivos: crear `...\services\storage-service\app\core\__init__.py`,
      `...\services\storage-service\app\core\index.py`,
      `...\services\storage-service\app\core\store.py`.
      Verify: smoke `tmp` que apunte `settings.RAW_PATH/JSON_PATH/...` a un dir temporal
      (monkeypatch de `settings` o `env` antes de importar), guarde un JSON `metadata`
      para `instrumentoId="42"` dos veces y confirme `version==1` luego `version==2`,
      y que un `tipo="json"` o una `key` con `..` sea rechazada. Script temporal
      ejecutado con el venv; borrar al terminar.

- [ ] 3. Crear los routers del storage-service.
      `health.py`: `GET /health` → `{"status":"ok","service":"storage-service"}` (igual
      que instrument-service). `almacenamiento.py` (prefix `/almacenamiento`):
      `POST /json` (body `GuardarJsonRequest` → `ArtefactoRef`),
      `POST /archivo` (multipart `archivo:UploadFile`, `tipo:Form`, `instrumentoId:Form|None`
      → `ArtefactoRef`; límite blando 50 MB → 413; `instrumentoId` ausente usa `"_"`),
      `GET /artefacto/{tipo}/{instrumentoId}?version=` → `ArtefactoDetalle` (incluye
      `contenido` si es JSON; 404 `"Artefacto no encontrado."` si falta),
      `GET /artefactos?instrumentoId=&tipo=` → `list[ArtefactoRef]`.
      Validaciones y mensajes en español exactamente como diseño §3.5/§3.6
      (422 `"Tipo de artefacto no soportado: <x>"`, 422 contenido `{}`/no-objeto,
      500 `"No se pudo almacenar el artefacto."`, 500 `"El artefacto almacenado no es
      un JSON válido."`, 500 `"Índice de artefactos corrupto."`).
      Archivos: crear `...\services\storage-service\app\routers\__init__.py`,
      `...\services\storage-service\app\routers\health.py`,
      `...\services\storage-service\app\routers\almacenamiento.py`.
      Verify: smoke `TestClient` (round-trip) — `POST /almacenamiento/json` con
      `{"instrumentoId":"42","tipo":"analysis","contenido":{"a":1}}` → 200 `ArtefactoRef`;
      `GET /almacenamiento/artefacto/analysis/42` → 200 con `contenido=={"a":1}`;
      `GET /almacenamiento/artefactos?instrumentoId=42` → lista con 1 elemento;
      `GET /almacenamiento/artefacto/analysis/999` → 404. Usa un storage temporal.

- [ ] 4. Reemplazar el stub de `main.py` del storage-service.
      Copiar el estilo de `services\instrument-service\main.py`: shim de `import shared`
      (bloque `sys.path` con `parents[2]`), `logging.basicConfig`, logger
      `storage-service`, `lifespan` que crea `raw_path_abs/json_path_abs/sav_path_abs/temp_path_abs`
      y `json_path_abs/_index`, CORS `allow_origins=["*"]`, `app.include_router(health.router)`
      + `app.include_router(almacenamiento.router)`, uvicorn en 8004.
      Archivos: sobrescribir `...\services\storage-service\main.py`.
      Verify: desde `...\services\storage-service`,
      `& "...\.venv\Scripts\python.exe" -B -c "from fastapi.testclient import TestClient; import main; c=TestClient(main.app); r=c.get('/health'); assert r.status_code==200 and r.json()['service']=='storage-service'; print('ok')"` → `ok`.

- [ ] 5. Añadir dependencias de runtime del storage-service.
      El stub actual (`requirements.txt`) solo trae fastapi/uvicorn/pydantic. Añadir
      `python-multipart==0.0.6` (necesario para `UploadFile`/`Form`) y, si falta,
      `sqlalchemy`/`psycopg` NO son necesarios (storage no toca BD). No añadir chromadb.
      Archivos: editar `...\services\storage-service\requirements.txt`.
      Verify: `& "...\.venv\Scripts\python.exe" -B -c "import multipart; print('multipart ok')"`
      (el venv del repo ya lo tiene; en Docker lo instala el Dockerfile). Confirmar
      además que el Dockerfile del servicio copia `services/storage-service/` y `shared/`.

---

## B. instrument-service — list/get/catálogo + helper de mapeo + seed

- [ ] 6. Crear `app/services/map_instrumento.py` (helper único DB+JSON→DTO).
      Implementa `mapear_instrumento(raw, procesado, instrumento_json: dict|None) -> InstrumentoDTO`
      con **lectura defensiva** (`.get` anidado, nunca aborta) y los defaults de
      degradación de diseño §2.3 (tabla campo-a-campo). Mapeos: `tipo` (§2.4:
      `encuesta→"Encuesta"`, `entrevista→"Entrevista"`, `prueba_estandarizada→"Prueba estandarizada"`,
      desconocido→`"Encuesta"`+`logger.warning`), `estado` (§2.5), `nivel` por
      heurística §2.3a (substring `posgrado|maestr|doctor|especialidad`→`"Posgrado"`,
      si no `"Licenciatura"`) sobre `metadata.dublin_core["dc:coverage"]` +
      `metadata.survey_specific["poblacion_objetivo"]`. Extrae `titulo`
      (`instrument.title`→`dc:title`→`nombre_archivo`), `anio` (año de `dc:date`→año de
      `fecha_carga`), `kpis` (`design_reference.kpi_hints`), `reactivos`
      (Σ `len(section["questions"])`), `descripcion` (`dc:description`→`instrument.objective`),
      `etiquetas` (`survey_specific.palabras_clave`→`dc:subject` split por `,`). `id=str(id_crudo)`,
      `idProcesado=str(id_instrumento)|None`. Exporta también
      `extraer_kpis(instrumento_json)` reutilizable por el catálogo (paso 8).
      Define el `InstrumentoDTO` (Pydantic v2) en `app/schemas/instrumentos.py` con
      `tipo:Literal[...]` (§2.4), `estado:Literal[...]` (§2.5),
      `nivel:Literal["Licenciatura","Posgrado"]`, los 12 campos de `Instrumento` + `idProcesado`.
      Archivos: crear `...\services\instrument-service\app\services\map_instrumento.py`,
      `...\services\instrument-service\app\schemas\instrumentos.py`.
      Verify: smoke que cargue `storage\raw\inst_01.v1.json` como `dict` y llame
      `mapear_instrumento` con un `raw`/`procesado` fake (SimpleNamespace con
      `id_crudo=1, id_owner=1, tipo_instrumento="encuesta", nombre_archivo="inst_01.v1.json",
      fecha_carga=datetime.now()`, `id_instrumento=1, estado="estandarizado"`): asserts
      `titulo` no vacío, `reactivos==10`, `len(kpis)==5`, `len(etiquetas)==7`,
      `tipo=="Encuesta"`, `estado=="Estandarizado"`, `nivel in {"Licenciatura","Posgrado"}`
      (diseño §2.3 test obligatorio). Script temporal con el venv; borrar al terminar.

- [ ] 7. Crear `app/services/instrumento_query.py` para resolver el JSON por `id_crudo`.
      Lógica compartida de resolución (§2.8 (b), orden): (1) si `procesado.ruta_json`
      existe en disco, cárgalo; (2) fallback `storage/raw`: traducir `id_crudo→inst_XX`
      vía `storage\raw\_seed_map.json` si existe, si no por `N→inst_{N:02d}`, y abrir la
      última versión con `glob("inst_<NN>.v*.json")` bajo `settings.raw_path_abs`.
      Devuelve `dict|None`. Encapsula el acceso para que `list.py` lo use por fila.
      Archivos: crear `...\services\instrument-service\app\services\instrumento_query.py`.
      Verify: smoke que, con `settings.raw_path_abs` apuntando a `storage\raw`,
      `resolver_json_por_id_crudo(1)` devuelva el dict de `inst_01` (assert
      `d["instrument_id"]=="inst_01"`). Script temporal; borrar al terminar.

- [ ] 8. Crear el router `app/routers/list.py` (GET list/get/catálogo), con auth.
      Prefix `/instrumentos`. Los tres endpoints usan
      `Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))` (§6, §2.17):
      `GET /instrumentos` → `list[InstrumentoDTO]` (lee `RawData` join `InstrumentoProcesado`
      por `id_crudo`; por fila resuelve el JSON con `instrumento_query` y mapea con
      `map_instrumento`); `GET /instrumentos/{id}` (`id`=`id_crudo:int`) →
      `InstrumentoDTO` o **404** si no existe; `GET /instrumentos/kpis/catalogo` →
      `list[str]` (unión ordenada de `design_reference.kpi_hints` de todos los JSON
      resueltos, `[]` si no hay). NO re-declarar DELETE (ya existe en `delete.py`).
      Registrar el router en `main.py` del instrument-service con
      `app.include_router(list.router)` (añadir el import junto a delete/health/upload).
      **Orden de rutas:** declarar `GET /instrumentos/kpis/catalogo` ANTES de
      `GET /instrumentos/{id}` para que `kpis` no se capture como `{id}` (o tipar `{id:int}`,
      que ya evita el choque; hacer ambas por seguridad).
      Archivos: crear `...\services\instrument-service\app\routers\list.py`;
      editar `...\services\instrument-service\main.py`.
      Verify: smoke `TestClient` con `get_db` y `require_rol`/`get_current_user`
      sobreescritos por fakes (patrón TESTING.md §1 y la nota "Saltarse la auth").
      Fake de `get_db` que devuelva una sesión con dos filas simuladas (o mockear la
      consulta): `GET /instrumentos` → 200 lista; `GET /instrumentos/9999` → 404;
      `GET /instrumentos/kpis/catalogo` → 200 `list[str]`; sin override de auth →
      `GET /instrumentos` responde 401. Script temporal; borrar al terminar.

- [ ] 9. (Opcional, best-effort) Añadir `GET /instrumentos/{id}/descarga?formato=crudo|json|sav`.
      En `list.py`: `json`→leer artefacto `analysis` (o `metadata`) vía storage/volumen y
      devolver `JSONResponse`; `crudo`/`sav`→`FileResponse` del binario original desde
      `raw_path_abs`/`sav_path_abs`. Mismo `require_rol`. Si por tiempo no entra, el
      frontend conserva su descarga por blob (paso 15) — NO bloquea el RAG.
      Archivos: editar `...\services\instrument-service\app\routers\list.py`.
      Verify: smoke `TestClient` (auth override) → `GET /instrumentos/1/descarga?formato=json`
      devuelve 200 con `content-type` JSON, o 404 si no hay artefacto. Script temporal.

- [ ] 10. Crear `scripts/seed_demo.py` (idempotente) para la demo.
      Por cada `storage\raw\inst_XX.v1.json`: asegurar fila en `raw_data`
      (`id_owner=settings.DEV_USER_ID`, `tipo_instrumento="encuesta"`,
      `nombre_archivo="inst_XX.v1.json"`, `raw_archivo`/`ruta` apuntando al archivo) y su
      `instrumento_procesado` (`estado="estandarizado"`,
      `ruta_json="storage/raw/inst_XX.v1.json"`), vía los modelos ORM de `shared`
      (respetan el schema `tt_rag`; NO SQL crudo contra `public`). Mantener/persistir
      `inst_XX→id_crudo` en `storage\raw\_seed_map.json`. Idempotente: si `inst_XX`
      ya mapeado, no duplica. Añadir el shim `import shared` como en los `main.py`.
      Documentar en el runbook (paso 20) que es parte de la EJECUCIÓN de la demo, no
      del runtime. Requiere Postgres levantado (`docker compose up -d postgres`).
      Archivos: crear `...\services\instrument-service\scripts\seed_demo.py` (+ `scripts\__init__.py` si hace falta).
      Verify: `& "...\.venv\Scripts\python.exe" -B -c "import ast; ast.parse(open(r'...\scripts\seed_demo.py',encoding='utf-8').read()); print('syntax ok')"`
      para compilar sin Postgres; la ejecución real (`python scripts\seed_demo.py`) se
      hace en la demo con Postgres arriba y se verifica que `_seed_map.json` tenga 21
      entradas. (El build no depende de ejecutarlo.)

---

## C. visualization-service (:8005) — RAG (centro de la demo)

- [ ] 11. Copiar embeddings/Chroma al visualization-service.
      `embeddings.py`: copia **1:1** de
      `...\services\analysis-service\app\vectorization\core\embeddings.py` (anotar origen
      en el docstring). `chroma_client.py`: copia de analysis-service con la ÚNICA
      desviación aditiva en `query(..., where: dict|None=None)` que pasa `where=where`
      a `collection.query` (diseño §4.3, anotar la desviación en el archivo). Añadir
      `nombre_coleccion(inv_id)` → `investigacion_<slug>` con `<slug>` saneado a
      `[a-z0-9_-]` (§4.4). `get_or_create_collection` con `{"hnsw:space":"cosine"}`,
      `upsert`, `get_point`, `_lock` copiados sin cambios.
      Archivos: crear `...\services\visualization-service\app\__init__.py`,
      `...\services\visualization-service\app\core\__init__.py`,
      `...\services\visualization-service\app\core\embeddings.py`,
      `...\services\visualization-service\app\core\chroma_client.py`.
      Verify: desde `...\services\visualization-service`,
      `& "...\.venv\Scripts\python.exe" -B -c "from app.core import embeddings, chroma_client; import inspect; assert 'where' in inspect.signature(chroma_client.query).parameters; print('ok')"`
      → `ok` (no carga el modelo ST ni conecta a Chroma: solo importa).

- [ ] 12. Crear `core/chunking.py` y `core/prompt.py`.
      `chunking.py`: `trocear(texto) -> list[str]` ventanas ~800 chars, solape 150,
      cortes preferentes por `\n\n` luego `. `, descartando chunks de <40 chars (§4.5).
      `prompt.py`: `construir(pregunta, chunks) -> str` con el prompt español
      fundamentado EXACTO del diseño §4.8 (incluye `CONTEXTO`, numeración de fuentes y
      `PREGUNTA`/`RESPUESTA`).
      Archivos: crear `...\services\visualization-service\app\core\chunking.py`,
      `...\services\visualization-service\app\core\prompt.py`.
      Verify: smoke — `trocear("a"*2000)` produce >1 chunk, todos ≤~950 chars y ≥40;
      `trocear("corto")` → `[]` (descarte <40); `construir("¿Q?", ["frag"])` contiene
      `"CONTEXTO"`, `"frag"` y `"¿Q?"`. Script temporal con el venv; borrar al terminar.

- [ ] 13. Crear `core/sources.py` (resolución y extracción de contenido).
      `resolver_artefacto(instrumentoId: str) -> dict|None` en el orden §4.2/§2.8:
      (1) storage-service `GET {STORAGE_BASE}/almacenamiento/artefacto/analysis/<id>` y
      si falta `/metadata/<id>` por `httpx` async, donde
      `STORAGE_BASE = os.getenv("STORAGE_SERVICE_URL","http://storage-service:8004")`
      (NUNCA `settings.STORAGE_SERVICE_URL`); (2) `instrumento_procesado.ruta_json` si
      hay BD vía `shared`; (3) fallback `storage/raw`: `_seed_map.json` o
      `N→inst_{N:02d}` + `glob("inst_<NN>.v*.json")` bajo `settings.raw_path_abs`.
      `extraer_texto(json) -> str`: concatena en orden `instrument.title`,
      `instrument.objective`, `instrument.dimensions_explored` (join `\n`), y por cada
      `instrument.sections[].questions[]`: `question.text` + `question.options` (join `\n`);
      fallback a `dc:description` si falta `instrument` (§4.2). `extraer_metadata(json, instrumentoId)
      -> dict`: `{instrumentoId, titulo, tipo (mapeado §2.4), investigador (str(id_owner) o ""),
      kpis:list[str]}` con los defaults de §2.3. Serializar `kpis` a JSON string al
      preparar metadata de Chroma (§4.6) — documentar en el archivo.
      Archivos: crear `...\services\visualization-service\app\core\sources.py`.
      Verify: smoke con `settings.raw_path_abs`→`storage\raw` y `STORAGE_SERVICE_URL`
      a un host inexistente (fuerza fallback): `resolver_artefacto("1")` devuelve el
      dict de `inst_01` (assert `instrument_id=="inst_01"`); `extraer_texto(d)` no vacío
      y produce `trocear(...)` con >0 chunks (test obligatorio §4.13). Script temporal.

- [ ] 14. Crear `core/ollama_client.py` (httpx stream + no-stream, degradación).
      `generar(prompt, modelo, stream) ` contra `settings.OLLAMA_HOST + "/api/generate"`
      con `{"model":modelo, "prompt":prompt, "stream":bool}`, `httpx.Timeout(connect=5, read=120)`.
      Stream: iterar NDJSON (`response`/`done`) y exponer un async generator de trozos.
      No-stream: devolver el texto completo. Capturar `httpx.ConnectError`/timeout y
      señalar degradación (§4.10). No valida el modelo contra catálogo.
      Archivos: crear `...\services\visualization-service\app\core\ollama_client.py`.
      Verify: smoke que importe el módulo y, mockeando `httpx` (o apuntando a un host
      caído), confirme que la ruta de error produce la degradación (no lanza). Import
      básico: `& "...\.venv\Scripts\python.exe" -B -c "from app.core import ollama_client; print('ok')"`.

- [ ] 15. Crear los schemas RAG (`app/schemas/rag.py`).
      `IndexRequest {investigacionId:str, instrumentoIds:list[str], reindexar:bool=False}`,
      `IndexInstrumentoResultado {instrumentoId, chunks:int, estado:Literal["indexado","omitido"], motivo:str|None=None}`,
      `IndexResponse {coleccion, total_chunks:int, instrumentos:list[...], mensaje}`,
      `ChatRequest {investigacionId, pregunta, instrumentoIds:list[str]|None=None, modelo:str|None=None, stream:bool=True, top_k:int=5}`
      con `field_validator("top_k")` que **clampa** a `[1,20]` (no rechaza, §4.7),
      `FuenteChatOut {instrumentoId, titulo, tipo:Literal["Encuesta","Entrevista","Prueba estandarizada"], investigador, kpis:list[str], fragmento}`,
      `ChatResponse {respuesta, fuentes:list[FuenteChatOut], modelo, degradado:bool=False}`.
      Validaciones §4.11 (`pregunta` 1..4000, `investigacionId` no vacío, `instrumentoIds`
      no vacío en index).
      Archivos: crear `...\services\visualization-service\app\schemas\__init__.py`,
      `...\services\visualization-service\app\schemas\rag.py`.
      Verify: `& "...\.venv\Scripts\python.exe" -B -c "from app.schemas.rag import ChatRequest; print(ChatRequest(investigacionId='x', pregunta='q', top_k=99).top_k)"`
      → imprime `20` (clamp). Desde `...\services\visualization-service`.

- [ ] 16. Crear el router RAG (`app/routers/rag.py`) + `health.py`.
      `health.py` igual que los demás servicios. `rag.py`:
      `POST /rag/index` (§4.6): resuelve colección (`nombre_coleccion`), si `reindexar`
      borra+recrea, por cada `instrumentoId` resuelve contenido (sources), trocea,
      `embed_texts`, `upsert` con ids `"<investigacionId>:<instrumentoId>:<n>"`,
      documents=chunk, metadatas con `kpis` serializado a JSON string + `tipo` mapeado;
      arma `IndexResponse` con resultados (`indexado`/`omitido`+motivo), sin abortar por
      uno que falte. `POST /rag/chat` (§4.7/§4.9): embed de la pregunta, `query` top_k con
      `where={"instrumentoId":{"$in":[...]}}` si vienen `instrumentoIds`, construye
      `fuentes` (dedup por `instrumentoId`, `kpis` deserializado, `tipo` ya mapeado),
      construye prompt, llama Ollama. `stream=true` → `StreamingResponse` SSE con
      `event: token`/`data:{"t":...}`, un `event: fuentes`/`data:{"fuentes":[...]}` y
      `event: fin`/`data:{}`. `stream=false` → `ChatResponse` JSON. Errores §4.12
      (409 `"La investigación no está indexada todavía."`, 502 `"Vector store no disponible."`,
      degradación Ollama 200). Registrar ambos routers.
      Archivos: crear `...\services\visualization-service\app\routers\__init__.py`,
      `...\services\visualization-service\app\routers\health.py`,
      `...\services\visualization-service\app\routers\rag.py`.
      Verify: smoke `TestClient` con `embeddings.embed_texts`/`embed_text`,
      `chroma_client.*` y `ollama_client.generar` **mockeados** (sin GPU/Chroma/Ollama):
      `POST /rag/index` con `instrumentoIds=["1"]` (fallback a `storage\raw`) → 200 y
      `total_chunks>0`; `POST /rag/chat` `stream:false` → 200 `ChatResponse` con
      `fuentes` no vacío; chat sobre colección inexistente (mock que lo simule) → 409.
      Script temporal con el venv; borrar al terminar.

- [ ] 17. Reemplazar `main.py` del visualization-service y fijar requirements/Dockerfile.
      `main.py`: estilo instrument-service (shim `shared`, lifespan que crea
      `raw_path_abs/temp_path_abs`, CORS, logger `visualization-service`, incluir
      `health` + `rag`, uvicorn 8005). `requirements.txt`: añadir las deps de RAG
      copiando de `services\analysis-service\requirements.txt` (`httpx==0.27.0`,
      `numpy==1.26.4`, `chromadb-client==1.0.0`, `sentence-transformers==3.0.0`,
      `sqlalchemy`/`psycopg[binary]` si se usa BD en sources, `python-multipart` no
      necesario). El Dockerfile ya copia `services/visualization-service/` + `shared/`
      (verificado); confirmar que no requiere cambios salvo las nuevas deps.
      Archivos: sobrescribir `...\services\visualization-service\main.py`;
      editar `...\services\visualization-service\requirements.txt`.
      Verify: desde `...\services\visualization-service`,
      `& "...\.venv\Scripts\python.exe" -B -c "from fastapi.testclient import TestClient; import main; c=TestClient(main.app); assert c.get('/health').json()['service']=='visualization-service'; print('ok')"`
      → `ok`.

- [ ] 18. Actualizar el bloque `visualization-service` de `docker-compose.yml`.
      Aplicar el YAML EXACTO de diseño §7: añadir `depends_on: ollama(service_started)`
      + `chromadb(service_started)`; envs `RAW_PATH=/app/storage/raw`,
      `TEMP_PATH=/app/storage/temp`, `OLLAMA_HOST=http://ollama:11434`,
      `OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2:3b}`, `CHROMA_HOST=chromadb`,
      `CHROMA_PORT=8000`,
      `EMBEDDING_MODEL=${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-mpnet-base-v2}`,
      `STORAGE_SERVICE_URL=http://storage-service:8004`,
      `INSTRUMENT_SERVICE_URL=http://instrument-service:8001`; montar
      `hf_cache:/root/.cache/huggingface` (volumen ya declarado, no redeclarar);
      conservar los envs de Postgres y los `*_PATH` ya presentes.
      Archivos: editar `c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag\docker-compose.yml`.
      Verify: `docker compose -f ...\docker-compose.yml config` (si Docker disponible)
      imprime el YAML resuelto sin error; si Docker no está, validar con
      `& "...\.venv\Scripts\python.exe" -B -c "import yaml; d=yaml.safe_load(open(r'...\docker-compose.yml',encoding='utf-8')); v=d['services']['visualization-service']; assert v['environment']['CHROMA_PORT']==8000 and 'ollama' in v['depends_on']; print('ok')"`.

---

## D. api-gateway (:8000) — proxy transparente

- [ ] 19. Reescribir `proxy/proxy.py` (transparente + SSE) y registrar el router.
      Reescribir `proxy_request` para devolver un `Response`/`JSONResponse` con
      `status_code=upstream.status_code`, `content=upstream.content`,
      `media_type=upstream.headers.get("content-type")` (sin envoltorio
      `{status_code,body}`); reenviar headers del request quitando `host` y
      `content-length`, conservando `Authorization` (§5.1). Eliminar el `except
      Exception→502` genérico y la función muerta `proxy_to_service` y los endpoints de
      ejemplo en inglés (`/instruments/*`). Rutas passthrough por prefijo (`{path:path}`,
      reenvía el path TAL CUAL, §5.2): `instrumentos` → `instruments` (:8001) para
      `GET/POST/DELETE /instrumentos/{path}`; `almacenamiento` → `storage` (:8004) para
      `/almacenamiento/{path}`; `rag` → `visualization` (:8005) para `/rag/{path}`, con
      `POST /rag/chat` usando `httpx.AsyncClient.stream` + `StreamingResponse`
      preservando `content-type: text/event-stream`. En `main.py` del gateway añadir
      `app.include_router(proxy_router)`. NO proxear `/metadata/*` ni `/vectorizacion/*`.
      Conservar `/auth/*` y `/health`.
      Archivos: editar `...\services\api-gateway\proxy\proxy.py`;
      editar `...\services\api-gateway\main.py`.
      Verify: smoke `TestClient` del gateway con los upstreams mockeados (monkeypatch de
      `httpx.AsyncClient`): `GET /instrumentos` reenvía a instrument-service y devuelve el
      body del upstream con su status (p.ej. 200 lista o 401 passthrough); `DELETE
      /instrumentos/5` reenvía a `/instrumentos/5`; `POST /rag/chat` con stream devuelve
      `text/event-stream`. Confirmar que `/health` y una ruta `/auth/*` siguen montadas.
      Script temporal; borrar al terminar.

---

## E. Frontend — de-mock sin tocar la UI

- [ ] 20. Re-tipar `ModeloLLM` y actualizar `MODELOS_DISPONIBLES`.
      En `src\types\index.ts`: `export type ModeloLLM = "llama3.2:3b";` (§8.3). En
      `src\api\chat.ts`: `MODELOS_DISPONIBLES = [{ id:"llama3.2:3b", etiqueta:"Llama 3.2 (3B) — local" }]`.
      Esto rompe `ChatPage.tsx:48` — se arregla en el paso 24.
      Archivos: editar `...\pixel-perfect-pixel\src\types\index.ts`,
      `...\pixel-perfect-pixel\src\api\chat.ts` (solo la constante por ahora).
      Verify: tras los pasos 20-24, `npm run build` en `pixel-perfect-pixel` compila sin
      errores de tipo (ver paso 25). Aislado: `npx tsc --noEmit` reportará el error de
      `ChatPage.tsx:48` hasta el paso 24 — es esperado.

- [ ] 21. Cablear `src\api\instrumentos.ts` a real (gateway) con map campo-a-campo.
      Importar `API_URL, pedir, ErrorHttp` de `./client`. Definir `InstrumentoDTO`
      (type local, 13 campos incl. `idProcesado?`). `mapear(d)` asigna explícitamente
      los 12 campos de `Instrumento` **descartando `idProcesado`** (§8.1, sin spread).
      `getInstrumentos()` → `pedir<InstrumentoDTO[]>(`${API_URL}/instrumentos`,{auth:true})`.map.
      `getInstrumento(id)` → try `pedir<InstrumentoDTO>(`${API_URL}/instrumentos/${id}`,{auth:true})`
      map; catch `ErrorHttp.status===404` → `null`, re-lanza el resto (firma
      `Promise<Instrumento|null>` intacta). `eliminarInstrumento(id)` →
      `pedir(`${API_URL}/instrumentos/${id}`,{method:"DELETE",auth:true})`.
      `getCatalogoKpis()` → `pedir<string[]>(`${API_URL}/instrumentos/kpis/catalogo`,{auth:true})`.
      `getInvestigadores()` y `buscarRelacionados()` quedan en mock/local con `// TODO`.
      `descargarInstrumento()` real si el endpoint del paso 9 entró; si no, mantener el
      blob local con `// TODO` (sin romper firma). Sin imports de `@/mocks` en las
      funciones ya reales.
      Archivos: reescribir `...\pixel-perfect-pixel\src\api\instrumentos.ts`.
      Verify: `npm run build` (paso 25) compila; revisar que `getInstrumentos`/`getInstrumento`
      no importan de `@/mocks` y que el map no incluye `idProcesado`.

- [ ] 22. Cablear `src\api\investigaciones.ts` a localStorage.
      `getInvestigaciones()` lee `indagata.investigaciones` (→ `[]` si vacío);
      `crearInvestigacion(nombre, propietarioId)` genera `id="res-"+Date.now()`, lo
      agrega a esa lista y lo devuelve (firmas intactas, §8.2). Sin `@/mocks`.
      Archivos: reescribir `...\pixel-perfect-pixel\src\api\investigaciones.ts`.
      Verify: `npm run build` compila; `getInvestigaciones` devuelve `Promise<Investigacion[]>`.

- [ ] 23. Cablear `src\api\chat.ts` al RAG (stream real + index + helpers).
      Añadir helpers exportados `setInstrumentosDeInvestigacion(investigacionId, ids)` /
      `getInstrumentosDeInvestigacion(investigacionId):string[]` sobre
      `indagata.instrumentosPorInvestigacion` (`Record<string,string[]>`). Ampliar firmas
      (§8.3): `enviarMensaje(pregunta, contexto, modelo, onToken, onDone, investigacionId, instrumentoIds?)`
      → `fetch` POST `${API_URL}/rag/chat` con token de `leerToken()`, body
      `{investigacionId, pregunta, instrumentoIds: instrumentoIds ?? getInstrumentosDeInvestigacion(investigacionId), modelo, stream:true, top_k:5}`,
      lee el `ReadableStream`, parsea SSE por líneas (`token`→`onToken(t)`,
      `fuentes`→guarda, `fin`→`onDone(fuentes)`), devuelve cancelador con
      `AbortController` (§4.9). `guardarContexto(investigacionId, contexto, instrumentoIds)`
      → `setInstrumentosDeInvestigacion(...)` + `fetch`/`pedir` POST
      `${API_URL}/rag/index` con `{investigacionId, instrumentoIds}` (`Promise<void>`).
      Sin `@/mocks`. Mantener texto en español.
      Archivos: reescribir `...\pixel-perfect-pixel\src\api\chat.ts`.
      Verify: `npm run build` compila; las firmas nuevas coinciden con las llamadas del
      paso 24.

- [ ] 24. Aplicar los 3 cambios acotados en `ChatPage.tsx` (sin tocar JSX/estilo).
      (a) NO tocar el `useEffect` que puebla `instrumentosFuentes`. (b) En
      `handleComenzar`: `await guardarContexto(activa.id, ctx, instrumentosFuentes.map(i=>i.id))`.
      En `handleEnviar`: `enviarMensaje(texto, contexto, modelo, onToken, onDone, activa.id)`.
      (c) Línea 48: `useState<ModeloLLM>("llama3.2:3b")`; añadir `activa` al array de deps
      del `useCallback` de `handleEnviar` (`[contexto, modelo, activa]`). Nada de
      cambios en el JSX, estilos ni layout (§8.3).
      Archivos: editar `...\pixel-perfect-pixel\src\features\chat\ChatPage.tsx`.
      Verify: `npm run build` compila sin el error previo de `:48`; `git -C <worktree> diff
      --stat pixel-perfect-pixel/src/features/chat/ChatPage.tsx` muestra solo cambios en
      esas líneas (ningún cambio de JSX).

- [ ] 25. Verificación del frontend (typecheck + lint).
      Desde `...\pixel-perfect-pixel`: `npm install` (si falta `node_modules`) y
      `npm run build` → compila sin errores de TypeScript. Luego `npm run lint` → sin
      errores nuevos. `carga.ts` y `kpis.ts` permanecen en `simularRed` con `// TODO`
      (§8.4/§8.5) — NO inventar endpoints.
      Archivos: ninguno nuevo (verificación).
      Verify: `npm run build` termina con éxito y `npm run lint` no reporta errores en
      los archivos tocados.

---

## F. Integración, verificación y merge

- [ ] 26. Verificación de integración (seams entre servicios).
      Smoke de contrato cruzado SIN levantar todo el stack: (1) `storage` round-trip
      (paso 3); (2) `visualization` index+chat con sources en fallback y Ollama/Chroma
      mockeados (paso 16); (3) `gateway` passthrough con upstreams mockeados (paso 19);
      (4) `instrument` list/get/catálogo con auth override (paso 8); (5) frontend
      `npm run build`+`npm run lint` (paso 25). Confirmar que todos los `main.app`
      importan y responden `/health`. Registrar el resultado en
      `c:\Users\yarel\Documents\indagata\indagata\.agents\tasks\fullstack-rag\verification.json`
      con `{"passed":true|false, ...}` (contrato del gate de runtime). Borrar todos los
      smoke scripts temporales creados.
      Verify: cada smoke descrito arriba pasa; `verification.json` escrito con
      `"passed":true` cuando todos pasen.

- [ ] 27. Commit local en la rama `fullstack-rag` (sin push).
      Preparar y confirmar los archivos nuevos/modificados con
      `git -C c:\Users\yarel\Documents\indagata\indagata\.worktrees\fullstack-rag add <rutas específicas>`
      (NO `git add .`; excluir artefactos de `.agents/tasks` y cualquier `_seed_map.json`
      generado si no se quiere versionar). Commit con mensaje convencional en español
      (p.ej. `feat: storage+visualization(RAG)+gateway+front de-mock`). NO hacer push;
      el usuario pidió explícitamente subir solo lo ya existente a `pruebas` por
      separado — esta rama se queda local hasta que el microservicio pendiente llegue.
      Verify: `git -C <worktree> status` limpio salvo lo intencionalmente sin versionar;
      `git -C <worktree> log --oneline -1` muestra el commit.

## Expectativas de verificación y merge

- **Build/typecheck mínimos para considerar hecho:** todos los `main.app` de los
  servicios tocados importan y responden `/health` por `TestClient`; los smoke de
  contrato de cada servicio pasan con el venv del repo; `pixel-perfect-pixel`
  compila (`npm run build`) y pasa `npm run lint`.
- **La demo end-to-end** (Postgres+Chroma+Ollama+servicios en Docker + `seed_demo.py`
  + `npm run dev`) es la validación completa, pero requiere infraestructura (GPU/modelo
  Ollama) fuera del alcance de la verificación automatizada; se documenta en el runbook.
- **Gate de review:** el revisor semántico escribe
  `c:\Users\yarel\Documents\indagata\indagata\.agents\tasks\fullstack-rag\review.json`
  con `{"verdict":"APPROVED"|"CHANGES_REQUESTED", findings, reviewDoc}`.
- **Gate de runtime:** se escribe
  `c:\Users\yarel\Documents\indagata\indagata\.agents\tasks\fullstack-rag\verification.json`
  con `{"passed":true|false}`.
- **Merge:** solo tras `verdict:"APPROVED"` y `passed:true`. El merge NO incluye push
  (el usuario mantiene esta rama local; `pruebas` ya recibió lo existente por separado).
