# Implementation Plan — Grafo de Recomendación de Instrumentos

> **Rama:** `elotro-back` (checkout principal `c:\Users\yarel\Documents\indagata\indagata`, SIN worktree, SIN rama nueva). NUNCA hacer push.
> **Fuente de verdad:** `.agents/tasks/grafo/design.md` (aprobado). Spec de contrato: `markdowns/SPEC_GRAFO_RECOMENDACION.md`.
> **Orden:** backend primero (core → router → schema/ORM), luego frontend (API → pantalla → ruta/nav), verificación al final. Cada ítem deja el repo compilable.

## Decisiones de implementación ya fijadas por el diseño (no re-decidir)
- Dos espacios de IDs: el grafo opera en `id_instrumento`; `/rag/index` opera en `id_crudo`. Los nodos exponen **ambos** (`id`=id_instrumento, `idCrudo`=id_crudo). `/grafo/investigacion` traduce id_instrumento→id_crudo y el **frontend** llama a `/rag/index` (design §1, §6.3).
- `sim_semantica`: por cada vector de A, UNA `chroma_client.query(summary, vector_a, top_k=len(acervo))`; por candidato, max `_distance_to_score`; candidato ausente de todas las queries → `0.0` (design §2.2).
- `solape_kpi`: Jaccard sobre conjuntos de KPIs (design §2.1). `UMBRAL_ALTO = 0.5` constante de módulo nombrada; regla de `razon` exacta de design §2.3.
- Degradación: Chroma caído → `w_sem=0`, `sim_semantica=0`, `degradado_semantico=true`, `logger.warning`, 200 (design §2.4).
- Comparación de autor siempre en espacio `int`: `autor_efectivo = int(autorId) if autorId not in (None,"") else usuario_actual.usuario_id`; `autorId` no convertible → 422 (design §3.1).

---

- [ ] 1. Crear el motor de score híbrido `grafo_recomendador.py` con sus funciones puras y el seam de cliente Chroma.
      Implementar en un módulo nuevo: `UMBRAL_ALTO = 0.5` (constante de módulo), `_jaccard(set_a, set_b) -> float` (unión vacía → 0.0), `_mapear_tipo(tipo_raw) -> str` (réplica local del dict de `instrument-service/app/services/map_instrumento.py::mapear_tipo`: `{encuesta→Encuesta, entrevista→Entrevista, prueba_estandarizada→Prueba estandarizada}`, desconocido → `"Encuesta"` + `logger.warning`), una función pura de etiquetado de `razon` (regla exacta de design §2.3 sobre scores crudos), una función pura de combinación de score, y la función principal `recomendar(db, instrumento_ids, *, autor_id=None, w_sem=0.6, w_kpi=0.4, top_n=10, min_score=0.15, excluir_propios=False, client=None) -> tuple[list, dict, bool]`. Reutilizar `chroma_client.get_or_create_collection` (con `client=client`), `chroma_client.query`, `chroma_client.get_point`, `kpi_search._distance_to_score`, `settings.CHROMA_COLLECTION_SUMMARY`. Los KPIs de cada instrumento salen de `KPIInferido` (join `id_procesado == id_instrumento`) unido a `KPI.nombre`. Degradación con gracia envolviendo el acceso a Chroma en try/except (fuerza `w_sem=0`, `sim_semantica=0`, flag `True`, `logger.warning`). Candidatos = instrumentos del acervo con fila en `kpi_inferido` y/o vector, excluyendo los de `instrumento_ids`; si `excluir_propios` excluir además los de `autor_efectivo` (comparación int). Filtrar por `min_score`, ordenar por score desc, cortar a `top_n` (clamp 1..100).
      Files: `services/analysis-service/app/vectorization/core/grafo_recomendador.py`
      Verify: ítem 2 añade los tests que lo ejercitan; tras el ítem 2, `cd services/analysis-service && python -m pytest tests/ -q` pasa.

- [ ] 2. Añadir tests unitarios/integración del motor y preparar el conftest para que `shared`/`app` resuelvan.
      En `tests/conftest.py` añadir la inserción de la **raíz del repo** en `sys.path` (hoy solo añade la raíz del servicio) para que `import shared...` y `app.vectorization...` resuelvan al correr pytest desde la carpeta del servicio (patrón de `scripts/seed_kpis.py::_candidatos_con_shared`). Crear `tests/test_grafo_recomendador.py` con: (a) unit puro de `_jaccard` (incluye unión vacía → 0.0); (b) unit del etiquetado de `razon` cubriendo las 5 ramas de design §2.3 (alta afinidad; KPIs compartidos con `score_kpi>=score_semantico`; contenido similar cuando domina lo semántico; etc.); (c) unit de la combinación de score y el clamp de `top_n`; (d) integración con `chromadb.EphemeralClient` sembrado con vectores conocidos inyectado vía `client=` para verificar `sim_semantica` numéricamente; (e) test de degradación inyectando un cliente cuyo `query` lanza → `degradado_semantico is True` y aún devuelve recomendaciones por KPI. Las pruebas que usan BD deben evitar Postgres real (usar la función pura o un `Session` fake/sqlite en memoria según lo que exponga el motor; preferir funciones puras sin IO para el Jaccard/score/razón).
      Files: `services/analysis-service/tests/conftest.py`, `services/analysis-service/tests/test_grafo_recomendador.py`
      Verify: `cd services/analysis-service && python -m pytest tests/ -q` — todos los tests nuevos y los existentes (`test_seed_kpis.py`) pasan.

- [ ] 3. Crear el router `grafo.py` con los 3 endpoints y schemas Pydantic con validación.
      Nuevo módulo `routers/grafo.py` con `router = APIRouter(prefix="/grafo", tags=["grafo-recomendacion"])`, espejando `kpi_calculo.py`/`espacio.py` (deps `UsuarioActual`, `DBSession`). Schemas Pydantic: `RecomendarRequest(instrumentoIds: list[str] = Field(min_length=1), autorId: str|None=None, w_sem: float=0.6, w_kpi: float=0.4, top_n: int=10, min_score: float=0.15, excluir_propios: bool=False)` con validador de pesos (suma 1.0 ± 1e-6, rango [0,1] → 422 en español) y `min_score` en [0,1]; `InvestigacionRequest(investigacionId: str [no vacío], instrumentoIds: list[str], grafo_snapshot: dict)` con cota de tamaño ≤ 1 MB serializado (design §3.2) → 422 español. Endpoints: **GET `/grafo/acervo`** (consulta ORM `RawData`+`InstrumentoProcesado`+`MetadatosDC`+`KPIInferido`+`KPI`+`Usuario` como design §5: nodos con `id`,`idCrudo`,`titulo` [`dc_title` fallback `nombre_archivo`],`tipo` [`_mapear_tipo` sobre `raw_data.tipo_instrumento`],`autorId`,`autorNombre`,`kpis`,`esPropio` [id_owner==usuario_actual.usuario_id en int]; aristas `kpi_compartido` entre instrumentos que comparten ≥1 KPI con `peso`=nº compartidos, agrupando por `kpi_id` para evitar O(n²)); **POST `/grafo/recomendar`** (llama `grafo_recomendador.recomendar(...)`, excluye los ids ya activos, devuelve `{recomendaciones, parametros, degradado_semantico}`); **POST `/grafo/investigacion`** (persiste fila en `GrafoInvestigacion` con rollback+`logger.exception`+500 en fallo como `registrar_calculo`; traduce `instrumentoIds`→`id_crudo` por JOIN; devuelve `{ok: true, grafoId, instrumentoIdsCrudo}`). IDs no convertibles a int se descartan con `logger.debug` (no 500). El ítem 4 debe existir antes de importar `GrafoInvestigacion`; implementar los ítems 3 y 4 juntos y registrar el router al final del ítem 3.
      Files: `services/analysis-service/app/vectorization/routers/grafo.py`, `services/analysis-service/main.py` (añadir `grafo` al import `from app.vectorization.routers import ...` y `app.include_router(grafo.router)` tras los existentes; conservar health, vectorizacion, espacio, kpis, kpi_calculo)
      Verify: `cd services/analysis-service && python -c "import main"` importa sin error (confirma que el router se registra y los imports resuelven). Luego `python -m pytest tests/ -q` sigue verde.

- [ ] 4. Añadir la tabla `grafo_investigacion` al schema SQL y su modelo ORM, y registrarlo.
      En `01_schema.sql`, dentro del bloque `BEGIN;…COMMIT;`, justo tras `CREATE TABLE IF NOT EXISTS kpi_calculo (...)` y antes de la sección «Índices», añadir `CREATE TABLE IF NOT EXISTS grafo_investigacion (grafo_id SERIAL PRIMARY KEY, investigacion_id TEXT NOT NULL, id_owner INTEGER REFERENCES usuario(usuario_id) ON DELETE CASCADE, instrumento_ids JSONB NOT NULL, grafo_snapshot JSONB NOT NULL, parametros JSONB, fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP);` (sin cualificar schema; el `search_path` ya es `tt_rag, public`). En la sección de índices añadir `CREATE INDEX IF NOT EXISTS idx_grafo_inv_owner ON grafo_investigacion(id_owner);`. Crear `shared/models/grafo_investigacion.py` espejando `kpi_calculo.py` pero con `fecha_creacion` usando `server_default=func.now()` (importar `func` de `sqlalchemy`), tipos `JSONB` de `sqlalchemy.dialects.postgresql`, `__table_args__ = {"schema": SCHEMA}`. Registrar en `shared/models/__init__.py` (import + entrada en `__all__`).
      Files: `infrastructure/postgres/init/01_schema.sql`, `shared/models/grafo_investigacion.py`, `shared/models/__init__.py`
      Verify: `cd services/analysis-service && python -c "import shared.models; from shared.models import GrafoInvestigacion; print(GrafoInvestigacion.__tablename__)"` imprime `grafo_investigacion` sin error (confirma que el ORM carga y queda en `Base.metadata`). Nota operativa: `01_schema.sql` solo corre en init de volumen Postgres limpio; en una BD ya poblada ejecutar el `CREATE TABLE IF NOT EXISTS` a mano o recrear el volumen de pruebas (design §9-B).

- [ ] 5. Crear el cliente de API del frontend `src/api/grafo.ts`.
      Nuevo archivo espejando `src/api/espacio.ts`: `import { ANALYSIS_URL, pedir } from "./client";`. Exportar interfaces `NodoGrafo` (`id, idCrudo, titulo, tipo: "Encuesta"|"Entrevista"|"Prueba estandarizada", autorId, autorNombre, kpis: string[], esPropio: boolean`), `AristaGrafo` (`origen, destino, tipo: "kpi_compartido", peso, kpis: string[]`), `Recomendacion extends NodoGrafo` (`score, score_semantico, score_kpi, razon, kpis_compartidos: string[]`), `RecomendarRequest` (`instrumentoIds: string[]; autorId?; w_sem?; w_kpi?; top_n?; min_score?; excluir_propios?`). Funciones: `getAcervoGrafo()` → `pedir<{nodos; aristas}>(\`${ANALYSIS_URL}/grafo/acervo\`, {auth:false})`; `recomendarGrafo(req)` → `pedir<{recomendaciones; parametros; degradado_semantico}>(..., {method:"POST", body:req, auth:false})`; `guardarGrafoInvestigacion(req:{investigacionId; instrumentoIds; grafo_snapshot})` → `pedir<{ok; grafoId; instrumentoIdsCrudo}>(..., {method:"POST", body:req, auth:false})` (design §8.1).
      Files: `pixel-perfect-pixel/src/api/grafo.ts`
      Verify: `cd pixel-perfect-pixel && npx tsc --noEmit` sin errores de tipo en el archivo nuevo (compilación TS; el build completo se corre en el ítem 8).

- [ ] 6. Instalar `@xyflow/react` y crear los componentes de la pantalla del grafo.
      `cd pixel-perfect-pixel && bun add @xyflow/react` (única dependencia nueva permitida). Crear `src/features/grafo/`: `GrafoPage.tsx` (al montar `getAcervoGrafo()` → render del grafo base con React Flow; estado `instrumentosActivos: string[]`=id_instrumento; zona de drop «investigación activa» que al `onDrop` añade el id y recalcula; `useEffect` sobre `instrumentosActivos` con debounce ~300 ms → `recomendarGrafo()` → agrega/actualiza nodos recomendados con estilo distinto agrupados por `razon`; botón «Comenzar investigación»), `NodoInstrumento.tsx` (nodo custom: color por tipo, tamaño por nº de KPIs, indicador propio/recomendado; solo tokens semánticos de `src/styles.css`), `FichaInstrumento.tsx` (panel lateral al click de nodo: título, tipo, KPIs, autor). Textos 100% en español. El botón «Comenzar investigación» espeja el flujo de `ChatPage.handleComenzar`: llama `guardarGrafoInvestigacion({investigacionId, instrumentoIds, grafo_snapshot})`, luego `guardarContexto(investigacionId, ctx, instrumentoIdsCrudo)` (de `src/api/chat.ts`, usando el `instrumentoIdsCrudo` devuelto) y navega a `/chat` con `useNavigate` de `@tanstack/react-router`.
      Files: `pixel-perfect-pixel/src/features/grafo/GrafoPage.tsx`, `pixel-perfect-pixel/src/features/grafo/NodoInstrumento.tsx`, `pixel-perfect-pixel/src/features/grafo/FichaInstrumento.tsx`, `pixel-perfect-pixel/package.json` (modificado por `bun add`)
      Verify: parte del build del ítem 8 (`bun run build`). No introducir clases de color literales (regla del proyecto). No romper el wizard de KPI-cálculo existente.

- [ ] 7. Añadir la ruta `_panel.grafo.tsx` y la entrada en el Sidebar.
      Crear `src/routes/_panel.grafo.tsx` espejando `_panel.espacio.tsx`: `createFileRoute("/_panel/grafo")` con `head`/meta en español apuntando a `GrafoPage`. En `src/components/layout/Sidebar.tsx` añadir `Share2` al import de `lucide-react` y una entrada a `OPCIONES`: `{ to: "/grafo", etiqueta: "Grafo de recomendación", icono: Share2 }` (referencia del componente, NO JSX — se desestructura como `icono: Icono` y se renderiza `<Icono .../>`).
      Files: `pixel-perfect-pixel/src/routes/_panel.grafo.tsx`, `pixel-perfect-pixel/src/components/layout/Sidebar.tsx`
      Verify: parte del build del ítem 8; la ruta aparece y el menú compila. El árbol de rutas de TanStack se regenera en el build.

- [ ] 8. Verificación integral.
      Backend: `cd services/analysis-service && python -m pytest tests/ -q` verde (Jaccard y similitud coseno verificables numéricamente; degradación responde solo-KPI con `degradado_semantico: true`). Si hay BD/Chroma sembrados disponibles, smoke manual: `GET /grafo/acervo` devuelve nodos+aristas; `POST /grafo/recomendar` con 2-3 ids activos devuelve recomendaciones ordenadas por score con `razon` y `kpis_compartidos`. Frontend: `cd pixel-perfect-pixel && bun run build` verde. Smoke manual opcional: arrastrar un nodo a la zona activa dispara recomendaciones (< 1.5 s) y «Comenzar investigación» indexa y abre el chat.
      Files: (ninguno nuevo)
      Verify: `python -m pytest tests/ -q` verde en analysis-service **y** `bun run build` verde en pixel-perfect-pixel.

## Notas / supuestos (design §9)
- **[B]** El `CREATE TABLE` solo corre en init de volumen limpio; una BD ya poblada necesita aplicar el DDL a mano o recrear el volumen de pruebas.
- **[F]** El gate de «recomendar devuelve candidatos reales» depende de que los instrumentos sembrados tengan vector en `summary_instrument` y filas en `kpi_inferido`. El motor degrada bien si falta alguno, pero la verificación con datos reales requiere acervo coherente; si no hay datos sembrados, la verificación se limita a los tests unitarios/integración con cliente efímero.
- **[G]** `/grafo/*` usa `auth:false` en dev (resuelve usuario por `DEV_USER_ID`), igual que `getEspacioVectorial`. En producción (JWT) se ajustaría como el resto del servicio.
- **sys.path en tests:** el `conftest.py` actual solo añade la raíz del servicio; el ítem 2 lo amplía a la raíz del repo para que `import shared` resuelva en los tests del motor.

---

## Verificación ejecutada (primera iteración — para el revisor)

> Ejecutado por el agente de implementación. Resultados reales; no re-ejecutar.
> Rama confirmada: `elotro-back` (checkout principal, sin worktree). SIN commit, SIN push.

**Backend — `ast.parse` de los tres archivos nuevos** (venv `.venv\Scripts\python.exe`):
`grafo_recomendador.py`, `routers/grafo.py`, `shared/models/grafo_investigacion.py` → `ast.parse OK`.

**Backend — ORM carga en `Base.metadata`** (desde la raíz del repo):
`import shared.models; from shared.models import GrafoInvestigacion; print(GrafoInvestigacion.__tablename__)` → imprime `grafo_investigacion`.
(Nota: debe correrse desde la raíz del repo, no desde la carpeta del servicio, igual que el resto de `import shared`.)

**Backend — registro del router** (desde `services/analysis-service`):
`python -c "import main"` → `import main OK`; las rutas registradas incluyen
`/grafo/acervo`, `/grafo/recomendar`, `/grafo/investigacion` junto con los routers previos
(health, vectorizacion, espacio, kpis, kpi_calculo conservados).

**Backend — pytest** (`cd services/analysis-service && python -m pytest tests/ -q`):
`20 passed`. Cubre: `_jaccard` (incl. unión vacía → 0.0 y valor conocido 1/3), las 5 ramas de
`_etiquetar_razon` (design §2.3), combinación de score + `min_score` + clamp de `top_n` (0→1, 999→100),
`excluir_propios`, integración `sim_semantica` con `chromadb.EphemeralClient` sembrado (idéntico→1.0,
ortogonal→0.0) y degradación (cliente que lanza en `get_or_create_collection` → `degradado_semantico=True`,
`w_sem=0`, aún devuelve recomendaciones solo-KPI). Incluye los tests previos (`test_seed_kpis.py`).
Conftest ampliado para insertar la raíz del repo en `sys.path`.

**Frontend — instalación de dependencia:** `bun add @xyflow/react` → `@xyflow/react@12.12.0`
(única dependencia nueva; registrada en `package.json`).

**Frontend — build:** `cd pixel-perfect-pixel && bun run build` → verde en los tres entornos
(client, SSR, nitro); se generan los chunks `_panel.grafo-*` sin errores de build.

**Frontend — type-check (`bunx tsc --noEmit`):** los archivos nuevos del grafo
(`src/features/grafo/*`, `src/api/grafo.ts`, `src/routes/_panel.grafo.tsx`) y `Sidebar.tsx`
no reportan errores. Quedan 7 errores de `tsc` PREEXISTENTES en archivos que esta feature NO tocó
(`src/api/chat.ts`, `src/api/client.ts`, `src/api/kpis.ts`), causados por `exactOptionalPropertyTypes`;
el gate real del proyecto es `vite build` (`bun run build`), que pasa en verde.

**Nota operativa [B]:** la tabla `grafo_investigacion` se añadió a `01_schema.sql` dentro del bloque
`BEGIN;…COMMIT;` con `CREATE TABLE IF NOT EXISTS` + índice `idx_grafo_inv_owner`. Ese script solo corre
en el init de un volumen Postgres limpio; en una BD ya poblada hay que aplicar el DDL a mano o recrear el
volumen de pruebas.
