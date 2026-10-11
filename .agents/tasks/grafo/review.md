# Grafo de Recomendación de Instrumentos — motor híbrido, 3 endpoints, tabla aditiva y pantalla React Flow

La implementación en `elotro-back` añade la capa de inteligencia colaborativa sobre el acervo: un motor de score híbrido (`grafo_recomendador.py`) que combina similitud semántica (vectores `summary_instrument`) y solape de KPIs (Jaccard), un router `/grafo/*` con tres endpoints, la tabla aditiva `tt_rag.grafo_investigacion` con su ORM, el cliente `src/api/grafo.ts`, la pantalla React Flow (`features/grafo/`), la ruta `_panel.grafo.tsx` y la entrada en el Sidebar. El trabajo sigue el diseño aprobado con fidelidad alta: los dos espacios de IDs (`id_instrumento` vs `id_crudo`) se exponen y traducen correctamente, el motor reutiliza el acceso a Chroma de `kpi_search`/`chroma_client` sin reimplementar coseno, y el flujo "Comenzar investigación" encaja con las firmas reales de `guardarContexto`/`crear`/`seleccionar`.

Watch for:
- **(confirmed, no bloqueante)** La interacción de la pantalla es *clic → agregar desde la ficha*, no el *arrastrar-soltar* que describen RF-4/RF-6 de la spec y el `onDrop` del plan ítem 6. El contrato de comportamiento (agregar al set activo → recálculo con debounce) se preserva; es una desviación de UX, no de contrato.
- **(confirmed, no bloqueante)** `parametros` que devuelve `/grafo/recomendar` incluye `top_n` además de `{w_sem, w_kpi, min_score}` del literal de la spec. Es aditivo y el tipo TS lo acepta (`Record<string, number>`).
- **(confirmed, operativo)** `grafo_investigacion` solo se crea en init de volumen Postgres limpio; una BD ya poblada necesita el DDL a mano (documentado por el coder, flag design §9-B).

**Verdict**: APPROVED

## High-level view

El motor de score es fiel al diseño. `score = w_sem*sim + w_kpi*jaccard` con `UMBRAL_ALTO = 0.5` como constante de módulo nombrada, `_jaccard` con guardia de unión vacía, y `_etiquetar_razon` implementando exactamente las cinco ramas de design §2.3 (incluida la preferencia por "KPIs compartidos" en empate). La similitud semántica reutiliza `chroma_client.get_point`/`query` y `kpi_search._distance_to_score` sin duplicar lógica de vectores, hace una query por instrumento activo con `top_k = len(acervo)`, y asigna `0.0` a candidatos ausentes. La degradación envuelve el acceso a Chroma y, ante cualquier fallo, fuerza `w_sem=0`, `sim=0`, marca `degradado_semantico=True` y responde solo-KPI con `logger.warning`.

Los tres endpoints respetan los shapes del diseño y exponen `id` (= id_instrumento) e `idCrudo` (= id_crudo) en cada nodo/recomendación. La comparación de autor opera siempre en espacio `int`: `_autor_efectivo` coacciona `autorId` a int (y lanza 422 si no es numérico), y `esPropio`/`excluir_propios` comparan int con int. `/grafo/investigacion` persiste con rollback+`logger.exception` ante fallo, traduce `id_instrumento → id_crudo` por JOIN descartando los que no mapean con `logger.warning`, y devuelve `instrumentoIdsCrudo` para que el frontend dispare `/rag/index` — exactamente la rama elegida en design §6.3.

La validación de entradas vive en los schemas Pydantic: pesos en [0,1] que suman 1.0±1e-6, `min_score` en [0,1], `investigacionId` no vacío y cota de 1 MB del snapshot, todo con mensajes en español. El schema SQL es aditivo dentro del `BEGIN;…COMMIT;` con `CREATE TABLE IF NOT EXISTS` + índice de owner, y el ORM espeja `kpi_calculo.py` con `server_default=func.now()` y queda registrado en `Base.metadata`.

El frontend cumple las reglas del proyecto: todo acceso pasa por `src/api/grafo.ts` (nunca fetch directo desde la pantalla), textos 100% en español, solo tokens semánticos de color (`bg-chart-*`, `bg-primary`, `bg-accent`, etc. — ninguna clase de color literal), organización por features. El botón "Comenzar investigación" encaja con las firmas reales de `guardarGrafoInvestigacion` → `guardarContexto(id, ctx, idsCrudo)` → `navigate("/chat")`. El KPI-cálculo wizard no se toca y su router sigue registrado.

La única divergencia de interés es de UX, no de contrato: la pantalla agrega instrumentos por clic en la ficha en vez del arrastrar-soltar de la spec. No bloquea porque el diseño es la fuente de verdad y el comportamiento observable (agregar → recálculo en tiempo real con debounce de 300 ms) se mantiene íntegro.

<details>
<summary>Issues (3)</summary>

1. **Interacción clic vs arrastrar-soltar** — la pantalla agrega instrumentos desde la ficha por clic, no con `onDrop` de React Flow como piden RF-4/RF-6 de la spec y el plan ítem 6. No bloqueante (el diseño es la fuente de verdad y el comportamiento agregar→recálculo se preserva); considerar añadir drag-and-drop si se quiere literalidad con la spec.
2. **`parametros` con `top_n` extra** — `/grafo/recomendar` devuelve `top_n` además del `{w_sem, w_kpi, min_score}` del literal de la spec §4.2. Aditivo y compatible con el tipo TS; dejar como está o alinear si se desea literalidad.
3. **DDL en BD ya poblada** — `grafo_investigacion` solo se crea en init de volumen limpio; aplicar el `CREATE TABLE IF NOT EXISTS` a mano o recrear el volumen de pruebas antes de ejercer `/grafo/investigacion` contra una BD existente.

</details>

<details>
<summary>Details</summary>

### Motor de score híbrido — fiel al diseño, sin duplicar lógica de vectores

`grafo_recomendador.recomendar()` implementa `score(c) = w_sem*sim_semantica + w_kpi*solape_kpi` tal como el contrato de design §2.1. El Jaccard (`_jaccard`) tiene la guardia de unión vacía → `0.0`, verificado por tests (`test_jaccard_union_vacia_es_cero`, valor conocido `1/3`). `UMBRAL_ALTO = 0.5` es constante de módulo nombrada (no literal mágico), y `_etiquetar_razon` reproduce la regla exacta de design §2.3 sobre scores crudos: ambos altos → "Alta afinidad (contenido + KPIs)"; compartidos con `score_kpi >= score_semantico` → "KPIs compartidos: …" (la preferencia que evita el falso "Contenido similar" en empate); semántico estrictamente mayor → "Contenido similar"; y las dos ramas finales. Las cinco ramas están cubiertas por tests dedicados.

`sim_semantica` no reimplementa coseno: lee el vector de cada activo con `chroma_client.get_point`, hace **una** `chroma_client.query(coleccion, vector, top_k=len(acervo))` por activo, mapea cada resultado al candidato por `meta["id_instrumento"]` y toma el máximo `_distance_to_score`. Un candidato ausente de todas las queries conserva su `0.0` inicial — exactamente la decisión de design §2.2 (NIT #3). Verifiqué contra `chroma_client.py` que `query` devuelve `metadatas`/`distances` como listas anidadas (el motor indexa `[0]`) y que `get_point` entrega la clave `embedding` (el motor lee `punto["embedding"]`); ambos coinciden.

La degradación envuelve el bloque Chroma en try/except amplio: ante cualquier fallo devuelve `({c: 0.0}, True)`, y `recomendar` fuerza `w_sem_eff = 0`, de modo que el score queda `w_kpi * jaccard` y la respuesta marca `degradado_semantico=True` con `logger.warning`. El test `test_degradacion_responde_solo_kpi` lo confirma numéricamente (`score == 0.4` con `w_kpi=0.4` y Jaccard=1.0, `razon == "KPIs compartidos: A, B"`).

### Coerción de autor y espacios de IDs — comparaciones siempre en int

El fallo silencioso que señalaba design §3.1 (MEDIUM #1: `'3' == 3` es `False`) está cerrado. `_autor_efectivo` en el router convierte `autorId` a int o lanza 422 si no es numérico; `esPropio` compara `inst.id_owner == usuario_actual.usuario_id` (ambos int tras la carga, que castea `id_owner` a int); y `excluir_propios` compara `inst.id_owner == autor_id` en int. El test `test_excluir_propios` verifica que el instrumento del mismo owner queda fuera y el ajeno permanece.

Los dos espacios de IDs se manejan como manda design §1: los nodos y recomendaciones exponen `id` (= `id_instrumento`, clave del grafo/Chroma/`kpi_inferido`) e `idCrudo` (= `id_crudo`). `/grafo/investigacion` traduce el set activo con un JOIN `InstrumentoProcesado.id_crudo == RawData.id_crudo`, descarta con `logger.warning` los `id_instrumento` sin crudo asociado, y devuelve `instrumentoIdsCrudo`. El frontend pasa esa lista a `guardarContexto`, que es quien hace `POST ${API_URL}/rag/index` — verifiqué que `guardarContexto(investigacionId, contexto, instrumentoIds)` ya existe con esa firma y ya indexa, así que no hay acoplamiento nuevo cross-service.

### Los tres endpoints y sus shapes

`GET /grafo/acervo` arma nodos con `titulo` (`dc_title` con fallback `nombre_archivo`), `tipo` vía `_mapear_tipo`, `autorId`/`autorNombre`, `kpis` y `esPropio`, y aristas `kpi_compartido` agrupando por `kpi_id` para evitar el O(n²) denso (design §5). El `_mapear_tipo` del motor es réplica exacta del diccionario y default de `instrument-service/.../map_instrumento.py` (`encuesta→Encuesta`, `entrevista→Entrevista`, `prueba_estandarizada→Prueba estandarizada`, desconocido → `"Encuesta"` + `logger.warning`), confirmado leyendo ambos archivos. El router siempre emite el literal mapeado, nunca el crudo, respetando el union TS de `NodoGrafo.tipo`.

`POST /grafo/recomendar` reenvía los defaults, descarta ids no numéricos con `logger.debug`, y devuelve `{recomendaciones, parametros, degradado_semantico}`. Las recomendaciones salen de `vars(r)` sobre el dataclass `Recomendacion`, cuyo orden de campos reproduce el shape de design §6.2 (`id, idCrudo, titulo, tipo, autorId, autorNombre, kpis, score, score_semantico, score_kpi, razon, kpis_compartidos`). Nota aditiva: `parametros` incluye `top_n` además del trío del literal de la spec; es compatible con `Record<string, number>` del TS.

`POST /grafo/investigacion` persiste `GrafoInvestigacion` con el patrón de `registrar_calculo` (rollback + `logger.exception` + propagación → 500 ante `SQLAlchemyError`) y devuelve `{ok, investigacionId, grafoId, instrumentoIdsCrudo}` — la desviación justificada de design §9-E frente al `{ok, coleccion, total_chunks}` literal de la spec (analysis-service no puede producir `coleccion`/`total_chunks` porque no llama a `/rag/index`).

### Validación de entradas — Pydantic en español

`RecomendarRequest` valida `instrumentoIds` no vacía (`min_length=1`), `min_score` en [0,1], pesos en [0,1] y que sumen 1.0±1e-6, todo con `ValueError` en español que Pydantic convierte en 422. `InvestigacionRequest` exige `investigacionId` no vacío (field + strip), `instrumentoIds` no vacía, y acota el `grafo_snapshot` a 1 MB serializado (design §3.2), rechazando también snapshots no serializables. La coerción de ids a int con descarte tolerante (`_a_int` → `None` se filtra) evita 500 por ids basura.

### Schema aditivo y ORM

El `CREATE TABLE IF NOT EXISTS grafo_investigacion` se inserta dentro del `BEGIN;…COMMIT;` tras `kpi_calculo` y el índice `idx_grafo_inv_owner` en la sección de índices, sin cualificar schema (el `search_path` ya es `tt_rag, public`) — aditivo y no destructivo. El ORM `GrafoInvestigacion` espeja `kpi_calculo.py` (ORM 2.0, `JSONB`, `__table_args__={"schema": SCHEMA}`, FK con `ondelete="CASCADE"`) y usa `server_default=func.now()` para `fecha_creacion` como pedía el diseño (NIT #6). Queda registrado en `shared/models/__init__.py` (import + `__all__`), confirmado en el diff. La evidencia del coder (`import shared.models; GrafoInvestigacion.__tablename__ == "grafo_investigacion"`) demuestra que carga en `Base.metadata`.

### Frontend — reglas del proyecto respetadas

`src/api/grafo.ts` define las interfaces del diseño §8.1 (`NodoGrafo` con `idCrudo`, `AristaGrafo`, `Recomendacion`, `RecomendarRequest` con `excluir_propios?`) y las tres funciones con `auth:false` contra `ANALYSIS_URL`. La pantalla pasa todo por `src/api/`, no importa mocks ni hace fetch directo. Revisé `NodoInstrumento`, `FichaInstrumento` y `GrafoPage`: solo tokens semánticos de color (`bg-chart-1/2/4`, `bg-primary`, `bg-accent`, `bg-muted`, `bg-secondary`, `text-foreground`…), ninguna clase de color literal; textos 100% en español. El `useEffect` sobre `activos` aplica debounce de 300 ms (RNF-1) y limpia el temporizador. El `comenzarInvestigacion` encaja con las firmas reales verificadas: `crear(nombre) → Promise<Investigacion>`, `seleccionar(id)`, `guardarContexto(id, ctx, idsCrudo)`; el guard `comenzarRef` evita doble disparo.

La divergencia de interacción: RF-4/RF-6 de la spec y el `onDrop` del plan ítem 6 describen arrastrar-soltar a una zona activa; la implementación agrega por clic en el botón "Agregar a mi investigación" de la ficha. El comportamiento observable que el score y la spec exigen (agregar al set activo → recálculo en tiempo real agrupado por razón, quitar, "Comenzar investigación") está completo. Clasifico esto como desviación de UX no bloqueante porque el design (fuente de verdad) describe la interacción como "añade su id y recalcula" sin exigir el mecanismo de arrastre, y ningún contrato de datos cambia.

### Ruta, Sidebar y no-regresión del KPI-cálculo

`_panel.grafo.tsx` espeja `_panel.espacio.tsx` con `createFileRoute("/_panel/grafo")`, `head`/meta en español, y queda regenerada en `routeTree.gen.ts` (`PanelGrafoRoute`, path `/grafo`). El Sidebar añade `Share2` como referencia de componente (no JSX) y la entrada `{ to: "/grafo", etiqueta: "Grafo de recomendación", icono: Share2 }`, consistente con el patrón `icono: Icono` que desestructura y renderiza. El diff no toca ningún archivo de KPI-cálculo y `main.py` conserva el registro de `kpi_calculo.router` junto con el nuevo `grafo.router`, así que el wizard de KPI-cálculo no se rompe.

### Cobertura de pruebas

`test_grafo_recomendador.py` cubre: Jaccard (unión vacía, sin intersección, valor conocido, iguales); las cinco ramas de `_etiquetar_razon` y `UMBRAL_ALTO == 0.5`; combinación de score solo-KPI con orden desc; filtro por `min_score`; clamp de `top_n` (0→1, 999→100); `excluir_propios`; integración de `sim_semantica` con `chromadb.EphemeralClient` (idéntico→1.0, ortogonal→0.0); y degradación con cliente que lanza. El `conftest.py` ampliado inserta la raíz del repo en `sys.path` para que `import shared` resuelva. La evidencia del coder reporta `20 passed` y `bun run build` verde en los tres entornos.

Not tested (gaps conocidos y aceptados): los endpoints HTTP no tienen tests de integración con FastAPI TestClient (la lógica de BD se cubre vía monkeypatch de `cargar_acervo`, no vía Postgres real); la traducción `id_instrumento → id_crudo` de `/grafo/investigacion` y la construcción de aristas de `/grafo/acervo` no tienen test unitario directo (dependen de ORM/BD). El diseño §11 ya acota que las pruebas de BD requieren acervo sembrado y quedan fuera del gate automatizable; coherente con los flags [B]/[F].

</details>

<details>
<summary>Mapa de archivos</summary>

- `services/analysis-service/app/vectorization/core/grafo_recomendador.py` — motor de score híbrido (Jaccard, sim semántica reutilizando Chroma, degradación, `UMBRAL_ALTO`, `_etiquetar_razon`, `_mapear_tipo`, `cargar_acervo`, `recomendar`).
- `services/analysis-service/app/vectorization/routers/grafo.py` — router `/grafo/*` (3 endpoints, schemas Pydantic, coerción de autor a int, traducción de ids, aristas).
- `services/analysis-service/main.py` — registro del `grafo.router` (conserva los previos).
- `services/analysis-service/tests/test_grafo_recomendador.py` — suite del motor (Jaccard, razón, score, clamp, excluir_propios, semántica efímera, degradación).
- `services/analysis-service/tests/conftest.py` — añade la raíz del repo a `sys.path`.
- `infrastructure/postgres/init/01_schema.sql` — `grafo_investigacion` + índice, dentro del `BEGIN;…COMMIT;`.
- `shared/models/grafo_investigacion.py` — ORM `GrafoInvestigacion`.
- `shared/models/__init__.py` — registro del modelo.
- `pixel-perfect-pixel/src/api/grafo.ts` — cliente de API (interfaces + 3 funciones).
- `pixel-perfect-pixel/src/features/grafo/{GrafoPage,NodoInstrumento,FichaInstrumento}.tsx` — pantalla React Flow.
- `pixel-perfect-pixel/src/routes/_panel.grafo.tsx` + `routeTree.gen.ts` — ruta y árbol regenerado.
- `pixel-perfect-pixel/src/components/layout/Sidebar.tsx` — entrada de navegación.
- `pixel-perfect-pixel/package.json` + `bun.lock` — `@xyflow/react@^12.12.0`.

Diff completo: `git diff` en la rama `elotro-back` (sin commit).

</details>
