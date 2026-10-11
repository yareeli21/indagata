# Diseño técnico — Grafo de Recomendación de Instrumentos

> **Rama de trabajo:** `elotro-back` (no cambiar de rama).
> **Fuente de verdad del contrato:** `markdowns/SPEC_GRAFO_RECOMENDACION.md`.
> **Alcance de este documento:** validar los contratos y puntos de integración
> de la spec contra el código real del repositorio y aterrizar las decisiones de
> implementación que la spec dejó abiertas. Nombres de endpoint/campo exactamente
> como en la spec; contenido de cara al usuario en español.

---

## 0. Resumen ejecutivo

El Grafo de Recomendación se implementa como un router nuevo `/grafo/*` en
**analysis-service** (dueño del dominio KPI + vectores `summary_instrument`), más
una tabla aditiva `tt_rag.grafo_investigacion`, un módulo de score híbrido
reutilizando el acceso a Chroma de `kpi_search.py`, y una pantalla React Flow en
el frontend. El stack queda **bloqueado** así:

- **Backend:** FastAPI (patrón de los routers existentes), SQLAlchemy ORM 2.0
  (`Mapped`/`mapped_column`), ChromaDB vía `app.vectorization.core.chroma_client`,
  embeddings vía `app.vectorization.core.embeddings`. Python ≥ 3.12.
- **Frontend:** TanStack Router + React, `@xyflow/react` v12 (única dependencia
  nueva), helper `pedir()` de `src/api/client.ts` contra `ANALYSIS_URL`.
- **Persistencia:** PostgreSQL schema `tt_rag`, tabla nueva en el bloque
  transaccional existente de `01_schema.sql`.

La verificación contra el código reveló **cuatro discrepancias con la spec** que
este diseño resuelve explícitamente (ver §9). La más importante: **la spec asume
un único espacio de IDs de instrumento, pero el código real tiene dos**
(`id_crudo` vs `id_instrumento`), y el grafo vive en el espacio `id_instrumento`
mientras que `/rag/index` vive en el espacio `id_crudo`.

---

## 1. Hallazgo crítico — los dos espacios de IDs

Verificado leyendo el código, no asumido:

- **`summary_instrument` (Chroma)** se indexa con `id = str(id_instrumento)` →
  `kpi_search.index_summary(id_instrumento, ...)` hace
  `upsert(ids=[str(id_instrumento)], ...)`.
- **`kpi_inferido`** se relaciona por `id_procesado`, que es FK a
  `instrumento_procesado.id_instrumento` (ver `shared/models/kpi_inferido.py` y
  `01_schema.sql` §10). O sea, el grafo (vectores + KPIs) vive en el espacio
  **`id_instrumento`**.
- **`/rag/index`** (visualization-service) resuelve cada `instrumentoId` como
  `str(id_crudo)`: `sources.resolver_artefacto()` → `_resolver_desde_bd()` hace
  `select(InstrumentoProcesado).where(InstrumentoProcesado.id_crudo == id_crudo)`
  y el docstring dice literalmente «clave = `str(id_crudo)`». El chat del
  frontend (`src/api/chat.ts`) también persiste y envía `str(id_crudo)`.

**Consecuencia:** los `id` de los nodos del grafo (`id_instrumento`) **NO** son los
mismos que `/rag/index` espera (`id_crudo`). Si `POST /grafo/investigacion`
reenviara directamente los ids de los nodos a `/rag/index`, indexaría instrumentos
equivocados o ninguno.

**Decisión de diseño (bloqueante para la implementación):**

1. Los nodos del grafo exponen **ambos** identificadores. El campo `id` del nodo
   (contrato de la spec) es `str(id_instrumento)` — es la clave del grafo, de
   `summary_instrument` y de `kpi_inferido`. Se añade un campo auxiliar
   `idCrudo: str` (= `str(raw_data.id_crudo)`) en cada nodo, obtenido por el JOIN
   `instrumento_procesado.id_crudo`.
2. `POST /grafo/investigacion` **traduce** el set activo de `id_instrumento` →
   `id_crudo` antes de disparar el indexado RAG (ver §6 y §9-D).

Esta traducción es un JOIN trivial (`instrumento_procesado.id_crudo`) que el
backend ya tiene a mano en todas las consultas del grafo.

---

## 2. El motor de score híbrido — `core/grafo_recomendador.py`

Archivo nuevo: `services/analysis-service/app/vectorization/core/grafo_recomendador.py`.
**No duplica lógica de vectores:** reutiliza `chroma_client.get_or_create_collection`,
`chroma_client.query`, `chroma_client.get_point` y `kpi_search._distance_to_score`.

### 2.1 Contrato de la función de score

```
score(c) = w_sem * sim_semantica(c, A) + w_kpi * solape_kpi(c, A)
```

- `A` = conjunto de instrumentos activos (ids = `id_instrumento`).
- `c` = instrumento candidato del acervo, no en `A`.
- **`sim_semantica(c, A)`** = máxima similitud coseno entre el vector de `c` y los
  vectores de los instrumentos en `A`, ambos leídos de `summary_instrument`.
  Se obtiene con `_distance_to_score(distancia)` (= `1 - distancia`, acotado a
  [0,1]). Rango [0, 1].
- **`solape_kpi(c, A)`** = Jaccard entre `KPIs(c)` y `⋃ KPIs(A)`:
  `|KPIs(c) ∩ KPIs(A)| / |KPIs(c) ∪ KPIs(A)|`. KPIs salen de `kpi_inferido`
  joineado a `kpi.nombre` por `kpi_id`. Rango [0, 1]. Si la unión es vacía → 0.0
  (sin división por cero).
- **Pesos por defecto:** `w_sem = 0.6`, `w_kpi = 0.4`. Deben sumar 1.0.
- **Umbral:** solo candidatos con `score >= min_score` (default `0.15`).
- **Corte:** ordena por `score` desc y recorta a `top_n` (default `10`).

### 2.2 Cómo se calcula `sim_semantica` sin duplicar vector logic

La spec dice «query a Chroma» por candidato. Para evitar `N` queries y espejar el
patrón de `kpi_search.py` (lectura directa de vectores, no re-embedding):

- Se leen los vectores de los instrumentos de `A` con
  `chroma_client.get_point(coleccion_summary, str(id_instrumento))` (ya devuelve
  el embedding; Chroma solo lo entrega con `include=["embeddings"]`, lo cual
  `get_point` ya hace).
- Para cada vector de `A`, se hace **una** `chroma_client.query(coleccion_summary,
  vector_a, top_k=K)` con **`K = len(acervo)`** (cobertura total del acervo objetivo,
  ~30 instrumentos; se elimina la variante "K generoso"), y de los resultados se toma,
  por cada candidato `c`, la máxima `_distance_to_score(dist)` sobre todos los `a ∈ A`.
- **Default (resuelve revisión final, NIT #3):** un candidato que no aparezca en el
  resultado de ninguna query recibe `sim_semantica = 0.0` (no queda sin asignar).
- La metadata de los puntos de `summary_instrument` trae `id_instrumento`
  (verificado en `index_summary`: `metadatas=[{"id_instrumento": ...}]`), así que
  el mapeo query-result → candidato es directo.

Esto es `|A|` queries (no `|candidatos|`), que para un set activo pequeño (2-3) y
RNF-1 (< 1.5 s) es holgado.

**Alternativa considerada y descartada:** calcular coseno en memoria con numpy
tras leer todos los vectores con `collection.get(include=["embeddings"])` (como
hace `espacio.py`). Es viable y determinista, pero re-implementaría el cálculo de
similitud fuera de Chroma; la spec pide explícitamente reutilizar
`_distance_to_score` y el `query`, así que se usa `query`. Si el acervo creciera
mucho, migrar a la variante numpy es un cambio local.

### 2.3 Razón de recomendación (etiquetas de cara al usuario, en español)

`razon` es un **campo del contrato de respuesta** que el usuario ve (§4.2 spec),
así que la regla que lo decide es parte del contrato observable, no un detalle
libre de implementación. Se fija de forma determinista **sobre los scores crudos**
de cada señal en `[0, 1]` (`score_semantico = sim_semantica(c, A)` y
`score_kpi = solape_kpi(c, A)`), **no** sobre los aportes ponderados `w*score`:

`UMBRAL_ALTO` se declara como **constante nombrada y ajustable del módulo**
(`grafo_recomendador.UMBRAL_ALTO = 0.5`), no un literal mágico embebido en la lógica
(resuelve revisión final, MEDIUM #2a). El desempate, además, **prefiere "KPIs
compartidos"** cuando el vínculo real son los KPIs: si hay `kpis_compartidos` no vacío
y `score_kpi >= score_semantico`, la razón es "KPIs compartidos", dejando "Contenido
similar" solo cuando domina de verdad lo semántico (resuelve MEDIUM #2b — evita que un
candidato cuyo único vínculo son KPIs compartidos se etiquete como "Contenido similar"
por un empate `>=`).

```python
UMBRAL_ALTO = 0.5            # constante de módulo, ajustable; sobre score crudo, no ponderado
alto_sem = score_semantico >= UMBRAL_ALTO
alto_kpi = score_kpi        >= UMBRAL_ALTO

if alto_sem and alto_kpi:
    razon = "Alta afinidad (contenido + KPIs)"
elif kpis_compartidos and score_kpi >= score_semantico:
    # Hay KPIs compartidos reales y la señal KPI domina (o empata): esa es la razón.
    razon = "KPIs compartidos: " + ", ".join(kpis_compartidos)
elif score_semantico > score_kpi:
    razon = "Contenido similar"
elif kpis_compartidos:
    razon = "KPIs compartidos: " + ", ".join(kpis_compartidos)
else:
    razon = "Contenido similar"
```

Donde `kpis_compartidos = KPIs(c) ∩ KPIs(A)` (nombres desde `kpi.nombre`). El
umbral `0.5` es sobre el score **crudo** de cada señal (no ponderado por `w_sem`/
`w_kpi`): un candidato con mucho solape de KPIs y poco parecido semántico, o
viceversa, no debe etiquetarse como «alta afinidad» aunque su score combinado sea
alto por el peso. En degradación semántica (`degradado_semantico == true`,
§2.4) `score_semantico = 0` para todos, por lo que `alto_sem` siempre es falso y la
rama efectiva es «KPIs compartidos» (o «Contenido similar» solo si ambos son 0, lo
cual no ocurre bajo un `min_score > 0`).

> Se elimina deliberadamente la idea anterior de «normalizar por su peso»: dividir
> `w*score` entre `w` devuelve `score`, con lo que esa normalización no hacía nada.
> La regla fijada arriba es la única fuente de verdad para `razon`.

### 2.4 Degradación con gracia (RNF-4, spec §4.2)

Si al acceder a Chroma falla cualquier operación (conexión, colección, query):

- Se fuerza `w_sem = 0` (todo el peso pasa a KPI → `w_kpi = 1.0` efectivo para que
  los scores sigan en [0,1]).
- `sim_semantica = 0` para todos.
- La respuesta incluye `degradado_semantico: true`.
- Se registra `logger.warning` (no error fatal). El fallo es **recuperable**: el
  endpoint responde 200 con recomendaciones solo-KPI.

### 2.5 Testabilidad (inyección de cliente)

La función principal acepta `client=None` y lo propaga a
`get_or_create_collection(name, client=client)`, igual que el seam ya existente en
`chroma_client` y `kpi_search`/`espacio`. Esto permite:

- **Unit test** del Jaccard con conjuntos de KPIs fijos (sin BD ni Chroma):
  función pura `_jaccard(set_a, set_b) -> float`.
- **Unit test** de la combinación de score y el etiquetado de razón con
  `sim_semantica`/`solape_kpi` precomputados (función pura de combinación).
- **Integration test** con un cliente Chroma efímero (`chromadb.EphemeralClient`)
  sembrado con vectores conocidos → verifica `sim_semantica` numéricamente
  (gate §9 de la spec: «Jaccard y similitud coseno verificables numéricamente»).
- **Test de degradación:** inyectar un cliente que lanza en `query` → verificar
  `degradado_semantico: true` y que aún devuelve recomendaciones por KPI.

Firma propuesta (seam explícito):

```python
def recomendar(
    db: Session,
    instrumento_ids: list[int],      # id_instrumento (espacio del grafo)
    *,
    autor_id: int | None = None,
    w_sem: float = 0.6,
    w_kpi: float = 0.4,
    top_n: int = 10,
    min_score: float = 0.15,
    excluir_propios: bool = False,
    client=None,                     # inyección de cliente Chroma (tests)
) -> tuple[list[Recomendacion], dict, bool]:  # (recos, parametros, degradado_semantico)
    ...
```

---

## 3. Validación de entradas (todas las entradas externas)

Owner de la validación: la capa Pydantic del router (schemas) + comprobaciones de
negocio en el core. Para cada entrada:

| Campo | Regla | Comportamiento en fallo |
|---|---|---|
| `instrumentoIds` | lista no vacía de strings numéricos; `≥ 1` | 422 (Pydantic) si vacía/mal tipada. En el core, ids que no existen en `summary_instrument`/`kpi_inferido` se **omiten silenciosamente** (no rompen el cálculo); si tras filtrar queda vacío → recomendaciones `[]` con `parametros` ecoados. |
| `w_sem`, `w_kpi` | floats en [0,1]; deben sumar ~1.0 (tolerancia 1e-6) | 422 si fuera de rango o la suma ≠ 1.0 (validador Pydantic). Mensaje en español. |
| `top_n` | int ≥ 1, ≤ 100 (clamp, no rechazo — mismo *patrón* que `_clamp_top_k` del RAG) | se normaliza al rango. La cota superior **100** es defensa propia del grafo contra requests abusivos; es **independiente** del `[1, 20]` de `_clamp_top_k` del RAG (verificado en `rag.py`: `max(1, min(20, v))`), cuyo dominio son *chunks* y es distinto del nº de instrumentos recomendados. |
| `min_score` | float en [0,1] | 422 si fuera de rango. |
| `autorId` | string numérico opcional | si ausente, se toma `usuario_actual.usuario_id`; si presente y no numérico → 422. |
| `excluir_propios` | bool opcional, default `false` | sin fallo posible; es un bool. Default `false` = no excluye nada por autor. Ver §3.1 para el camino request→core y la regla. |
| `investigacionId` (en `/grafo/investigacion`) | string no vacío | 422 si vacío (espeja `IndexRequest._investigacion_no_vacia`). |
| `grafo_snapshot` | objeto JSON | se valida con una **cota de tamaño pragmática** (ver §3.2); su estructura interna no se valida campo a campo (es un snapshot opaco para trazabilidad), pero sí se rechaza un payload abusivo. |

### 3.1 Wiring de `excluir_propios` (resuelve hallazgo HIGH #1)

El core `recomendar()` ya expone `excluir_propios: bool = False` (§2.5), pero
**ningún contrato de request lo transportaba**. Se declara explícitamente en los
tres niveles para cerrar el contrato (la spec §4.2 dice «excluye… los del propio
autor, según el flag»; aquí se aterriza qué es ese flag):

- **Schema Pydantic del router** (`RecomendarRequest`): campo booleano explícito.
  ```python
  class RecomendarRequest(BaseModel):
      instrumentoIds: list[str] = Field(min_length=1)
      autorId: str | None = None
      w_sem: float = 0.6
      w_kpi: float = 0.4
      top_n: int = 10
      min_score: float = 0.15
      excluir_propios: bool = False   # ← declarado explícitamente
  ```
- **TS** (`RecomendarRequest`, §8.1): se añade `excluir_propios?: boolean`.
- **Core** (§2.5): ya tiene `excluir_propios: bool = False`; el router lo pasa tal
  cual, sin interpretarlo.

**Coerción de tipos del autor (resuelve revisión final, MEDIUM #1).** `raw_data.id_owner`
es `INTEGER` y `usuario_id` es `int`, pero `request.autorId` llega como string. En
Python `'3' == 3` es `False`, así que la comparación de autor fallaría en silencio.
Se fija: el autor efectivo se resuelve SIEMPRE a `int` antes de comparar:
```python
autor_efectivo = int(request.autorId) if request.autorId not in (None, "") else usuario_actual.usuario_id
# comparar id_owner (int) == autor_efectivo (int)
# autorId presente pero no convertible a int -> 422
```
Tanto `esPropio` (en `/grafo/acervo`) como la exclusión por `excluir_propios` operan en
el espacio `int` de `usuario_id`. Nunca se comparan str con int.

**Regla única (sin ambigüedad):** si `excluir_propios == true`, el core excluye del
conjunto de candidatos los instrumentos cuyo `autorId == (request.autorId ??
usuario_actual.usuario_id)`. Es decir: la presencia de `autorId` **no** activa por
sí sola la exclusión; solo sirve para decidir *de quién* se excluyen los
instrumentos cuando el flag está activo. Con el default `false`, no se excluye
nada por autor (solo se excluyen siempre los ids ya presentes en `instrumentoIds`,
que es independiente de este flag).

### 3.2 Cota de tamaño de `grafo_snapshot` (resuelve hallazgo NIT #6)

`grafo_snapshot` llega como JSON del cliente y se persiste en JSONB. Aceptarlo sin
cota es un vector de abuso menor (payload gigante → fila JSONB enorme). Como el
diseño afirma «validación de todas las entradas externas», se añade una cota
pragmática en el schema Pydantic del router de `/grafo/investigacion`:

- Rechazo (422) si el `grafo_snapshot` serializado supera **1 MB**
  (`len(json.dumps(snapshot)) > 1_048_576`), con mensaje en español.
- Alternativamente/además, límite blando de nº de nodos+aristas si la estructura
  trae `nodos`/`aristas` como listas (p. ej. ≤ 2000 elementos combinados); si no
  trae esa forma, la cota de bytes basta.

Esto es defensa en profundidad para un entorno de tesis/demo de un solo usuario de
confianza, no una validación estructural completa: el snapshot sigue siendo opaco
para trazabilidad.

Los `instrumentoIds` llegan como **string** en el contrato JSON (igual que
`/rag/index`), pero internamente son `int` (`id_instrumento`). El router convierte
con tolerancia: ids no convertibles a int se descartan con un `logger.debug`, no
tiran 500.

---

## 4. Guard de autenticación y patrón de router

Espeja exactamente `kpi_calculo.py` / `espacio.py`:

```python
router = APIRouter(prefix="/grafo", tags=["grafo-recomendacion"])
```

- Cada endpoint recibe `usuario_actual: UsuarioActual` y, si consulta BD,
  `db: DBSession` (ambos de `app.vectorization.dependencies`).
- En `AUTH_DEV_MODE` el usuario se resuelve por `DEV_USER_ID` (sin token), igual
  que el resto del servicio. `esPropio` / `autorId` por defecto se derivan de
  `usuario_actual.usuario_id`.
- Registro en `services/analysis-service/main.py`:
  `from app.vectorization.routers import ..., grafo` y
  `app.include_router(grafo.router)` tras los existentes.

> **Nota de ruta verificada:** el entrypoint es `services/analysis-service/main.py`
> (NO `app/main.py` como decía el prompt del paso). Los routers viven en
> `services/analysis-service/app/vectorization/routers/`. Ver §9-A.

---

## 5. Construcción del grafo del acervo (fuentes de datos reales)

Para armar nodos y aristas, el backend consulta Postgres vía ORM (patrón
`listar_calculos` de `kpi_calculo.py`: `db.query(...).join(...)`). Un nodo del
acervo necesita: título, tipo, autor, KPIs. De dónde sale cada campo:

| Campo del nodo | Origen real |
|---|---|
| `id` | `instrumento_procesado.id_instrumento` (str) |
| `idCrudo` (auxiliar, §1) | `raw_data.id_crudo` (str) vía JOIN `instrumento_procesado.id_crudo → raw_data.id_crudo` |
| `titulo` | `metadatos_dc.dc_title` (JOIN por `raw_data.id_crudo`); fallback `raw_data.nombre_archivo` |
| `tipo` | `raw_data.tipo_instrumento` mapeado a {Encuesta, Entrevista, Prueba estandarizada} con la **misma lógica que `map_instrumento.mapear_tipo`** (ver nota de normalización abajo) |
| `autorId` | `raw_data.id_owner` (str) |
| `autorNombre` | `usuario.nombre` (JOIN por `raw_data.id_owner → usuario.usuario_id`) |
| `kpis` | `kpi.nombre` por cada fila de `kpi_inferido` con `id_procesado = id_instrumento` (JOIN `kpi_inferido → kpi`) |
| `esPropio` | `raw_data.id_owner == usuario_actual.usuario_id` |

**Aristas (`kpi_compartido`):** se calculan en memoria tras cargar el mapa
`{id_instrumento → set(kpi_ids)}`. Para cada par de instrumentos que comparten
≥ 1 KPI, se emite una arista con `peso = |KPIs compartidos|` y `kpis = [nombres]`.
Para evitar O(n²) sobre un acervo grande, se agrupa por `kpi_id` → lista de
instrumentos que lo tienen, y se generan solo los pares dentro de cada grupo
(sparse). Con 30 instrumentos (volumen objetivo de la spec §10) es trivial.

**Normalización del `tipo` del nodo (resuelve hallazgo MEDIUM #2).** El `tipo` del
nodo DEBE respetar el union estricto del frontend
`NodoGrafo.tipo: "Encuesta" | "Entrevista" | "Prueba estandarizada"` (§8.1). La
fuente canónica y verificada es `raw_data.tipo_instrumento`, almacenado
lowercase-snake (`encuesta | entrevista | prueba_estandarizada`; lo valida al
escribir `upload_service._parse_tipo`). La lógica de mapeo a usar es la de
`services/instrument-service/app/services/map_instrumento.py::mapear_tipo`
(keyed sobre `raw_data.tipo_instrumento` lowercase-snake), **no** la de
`visualization-service/app/core/sources.py::_mapear_tipo`, que parte de
`metadata.dublin_core["dc:type"]` y es la que el propio `sources.py` reconoce como
informativa/poco fiable (cae a `"Encuesta"` cuando `dc:type` no mapea).

Dado que `map_instrumento` vive en **instrument-service** (otro microservicio) y no
es importable desde analysis-service, el grafo **replica el mismo diccionario y la
misma regla** (no inventa una nueva), con un helper local trivial:

```python
_TIPO_MAP = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_TIPO_DEFAULT = "Encuesta"

def _mapear_tipo(tipo_raw: str | None) -> str:
    clave = (tipo_raw or "").strip().lower()
    tipo = _TIPO_MAP.get(clave)
    if tipo is None:
        logger.warning("tipo_instrumento desconocido %r; se mapea a %r.", tipo_raw, _TIPO_DEFAULT)
        return _TIPO_DEFAULT
    return tipo
```

- **Valor desconocido → `"Encuesta"` + `logger.warning`** (idéntico a
  `map_instrumento.mapear_tipo`, verificado).
- **Garantía de contrato:** el router SIEMPRE emite el literal mapeado
  ({Encuesta, Entrevista, Prueba estandarizada}); **nunca** el valor crudo
  (`"encuesta"`, `"prueba_estandarizada"`, …), para no violar silenciosamente el
  union TS de `NodoGrafo.tipo`.

> **Discrepancia menor (§9-C):** `tipo` sí está disponible de forma canónica en
> `raw_data.tipo_instrumento` — mejor fuente que la que usa `sources.py`
> (`dc:type`). El grafo usa `raw_data.tipo_instrumento` con la regla de
> `map_instrumento.mapear_tipo` replicada localmente.

---

## 6. Los tres endpoints

Todos bajo prefijo `/grafo`, llamados directo a `ANALYSIS_URL` (el api-gateway no
proxea `/vectorizacion/*` ni `/grafo/*`, confirmado en `espacio.ts` y el docstring
de `kpi_calculo.py`).

### 6.1 `GET /grafo/acervo`

Respuesta exacta de la spec §4.1 (nodos + aristas), **más** `idCrudo` en cada
nodo (§1):

```json
{
  "nodos": [
    { "id": "12", "idCrudo": "9", "titulo": "...", "tipo": "Encuesta",
      "autorId": "3", "autorNombre": "Investigador Demo",
      "kpis": ["Learner Engagement Metrics"], "esPropio": true }
  ],
  "aristas": [
    { "origen": "12", "destino": "7", "tipo": "kpi_compartido", "peso": 2,
      "kpis": ["Student Retention Rate", "Dropout Rate"] }
  ]
}
```

- Errores: si Postgres falla → la `SQLAlchemyError` se propaga (se loggea con
  `logger.exception`) y FastAPI responde 500, igual que `kpi_calculo.listar_calculos`.
  Fatal y no recuperable (sin acervo no hay grafo). No depende de Chroma.

### 6.2 `POST /grafo/recomendar`

Request/response exactos de la spec §4.2. El request añade los defaults ya
descritos; la respuesta añade `degradado_semantico` (ya previsto en la spec §4.2
como flag de degradación):

```json
{
  "recomendaciones": [
    { "id": "21", "idCrudo": "18", "titulo": "...", "tipo": "Entrevista",
      "autorId": "5", "autorNombre": "...", "kpis": [...],
      "score": 0.73, "score_semantico": 0.68, "score_kpi": 0.80,
      "razon": "Alta afinidad (contenido + KPIs)",
      "kpis_compartidos": ["Student Retention Rate"] }
  ],
  "parametros": { "w_sem": 0.6, "w_kpi": 0.4, "min_score": 0.15 },
  "degradado_semantico": false
}
```

- Excluye siempre los instrumentos ya en `instrumentoIds`. Si `excluir_propios ==
  true` (campo booleano explícito del request, default `false`), excluye además los
  instrumentos cuyo `autorId == (request.autorId ?? usuario_actual.usuario_id)`.
  Regla y wiring completos en §3.1.
- Ordena por `score` desc, corta a `top_n`.
- Errores: Chroma caído → NO es error; degrada (§2.4). Postgres caído → 500
  (sin KPIs no hay nada que recomendar). Set activo vacío tras filtrar → 200 con
  `recomendaciones: []`.
- Logging: degradación → `warning`; fallo de BD → `exception`.

### 6.3 `POST /grafo/investigacion`

Request de la spec §4.3 (`investigacionId`, `instrumentoIds`, `grafo_snapshot`).
Acción:

0. Valida el request (Pydantic): `investigacionId` no vacío, `instrumentoIds` no
   vacía, y `grafo_snapshot` dentro de la cota de tamaño de §3.2 (≤ 1 MB
   serializado) → 422 en español si falla.
1. Persiste una fila en `tt_rag.grafo_investigacion` (snapshot + params + owner).
2. **Traduce** `instrumentoIds` (= `id_instrumento`) a `id_crudo` (JOIN §1).
3. Devuelve `instrumentoIdsCrudo` para que el frontend dispare `/rag/index`.

**Decisión sobre quién llama a `/rag/index` (requerida por el prompt del paso):**

> **El FRONTEND llama a `/rag/index`, no el servidor.** Elegido por ser la opción
> más simple y correcta a la luz del flujo real de chat.

Justificación desde el código real:

- `/rag/index` vive en **visualization-service**, expuesto por el **api-gateway**
  en `API_URL` (`src/api/chat.ts` hace `fetch(\`${API_URL}/rag/index\`)`). El
  grafo vive en **analysis-service** (`ANALYSIS_URL`). Que analysis-service llame
  server-to-server a `/rag/index` introduciría un acoplamiento nuevo
  cross-service (analysis → gateway/visualization) que hoy **no existe** y una
  dependencia de red/credenciales adicional. El único precedente server-to-server
  del servicio es `kpi_calculo` → Ollama, no entre microservicios de dominio.
- El frontend **ya tiene** `guardarContexto()` en `src/api/chat.ts`, que persiste
  la selección en cliente y hace `POST ${API_URL}/rag/index` con
  `{ investigacionId, instrumentoIds }`. El grafo reutiliza esta función tal cual.
- El contrato de `/rag/index` (`IndexRequest`) espera `instrumentoIds` en el
  espacio **`id_crudo`** (verificado en §1). Por tanto, `POST /grafo/investigacion`
  **devuelve en su respuesta la lista `instrumentoIdsCrudo` ya traducida**, y el
  frontend la pasa a `guardarContexto()` → `/rag/index`. Así la traducción de
  espacios de IDs la hace quien tiene el JOIN (analysis-service), pero el indexado
  lo dispara quien ya sabe hablar con el gateway (el frontend).

Flujo resultante del botón «Comenzar investigación»:

```
guardarGrafoInvestigacion({investigacionId, instrumentoIds(id_instrumento), snapshot})
   → POST ANALYSIS_URL/grafo/investigacion
   → respuesta { ok, grafoId, instrumentoIdsCrudo }
guardarContexto(investigacionId, contexto, instrumentoIdsCrudo)   // ya existe
   → POST API_URL/rag/index
navega a /chat
```

Respuesta de `POST /grafo/investigacion`:

```json
{ "ok": true, "grafoId": 7, "instrumentoIdsCrudo": ["9", "18", "4"] }
```

> **Desviación justificada del literal de la spec §4.3.** La spec dice que el
> endpoint «devuelve `{ ok, coleccion, total_chunks }`» y «llama internamente a
> `/rag/index` (o devuelve los ids para que el frontend llame — decisión de
> implementación)». La spec dejó esta decisión abierta; se elige la segunda rama.
> Como analysis-service ya **no** llama a `/rag/index`, no puede conocer
> `coleccion`/`total_chunks` (los produce visualization-service). Por eso la
> respuesta devuelve `instrumentoIdsCrudo` + `grafoId` en vez de
> `coleccion`/`total_chunks`. El `IndexResponse` real de `/rag/index` es
> `{ coleccion, total_chunks, instrumentos, mensaje }` (**sin** `ok`, verificado en
> `schemas/rag.py`); el frontend lee `coleccion`/`total_chunks` de ahí. El `ok` es
> propio de la respuesta de `/grafo/investigacion`. La firma del cliente
> `guardarGrafoInvestigacion` en el frontend se ajusta a esto (§8).

- Errores: fallo al persistir en Postgres → `rollback` + `logger.exception` + 500
  (patrón `registrar_calculo`). La traducción de ids que no mapean a `id_crudo` se
  omite de la lista devuelta con `logger.warning` (no rompe).

---

## 7. Persistencia — tabla `tt_rag.grafo_investigacion`

### 7.1 Schema (aditivo, no destructivo, DENTRO del bloque transaccional)

Se inserta en `infrastructure/postgres/init/01_schema.sql` **dentro del
`BEGIN;…COMMIT;`** existente, justo después de la tabla `kpi_calculo` (último
`CREATE TABLE` del bloque) y antes de la sección «Índices». `CREATE TABLE IF NOT
EXISTS` la hace idempotente; no toca ninguna tabla existente.

```sql
-- ── grafo_investigacion (trazabilidad del grafo de recomendación) ─────────────
CREATE TABLE IF NOT EXISTS grafo_investigacion (
    grafo_id          SERIAL  PRIMARY KEY,
    investigacion_id  TEXT    NOT NULL,
    id_owner          INTEGER REFERENCES usuario(usuario_id) ON DELETE CASCADE,
    instrumento_ids   JSONB   NOT NULL,
    grafo_snapshot    JSONB   NOT NULL,
    parametros        JSONB,
    fecha_creacion    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

(Dentro del bloque el `search_path` ya es `tt_rag, public`, así que la tabla y la
FK `usuario(usuario_id)` resuelven sin cualificar schema, igual que las demás.)

Índice sugerido (en la sección de índices del mismo bloque):
`CREATE INDEX IF NOT EXISTS idx_grafo_inv_owner ON grafo_investigacion(id_owner);`

> **Nota:** `01_schema.sql` solo corre en la **primera** inicialización del volumen
> de Postgres (init scripts de la imagen). Para una BD ya existente hace falta
> ejecutar el `CREATE TABLE IF NOT EXISTS` a mano (o recrear el volumen en el
> entorno de pruebas). Documentar esto en el PLAN; no es un cambio de diseño pero
> es un paso operativo real (§9-B).

### 7.2 ORM — `shared/models/grafo_investigacion.py`

Espeja el estilo de `kpi_calculo.py` (ORM 2.0, `Mapped`/`mapped_column`, `SCHEMA`,
`JSONB` de `sqlalchemy.dialects.postgresql`):

```python
from __future__ import annotations
from datetime import datetime
from sqlalchemy import TIMESTAMP, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shared.db.base import SCHEMA, Base

class GrafoInvestigacion(Base):
    __tablename__ = "grafo_investigacion"
    __table_args__ = {"schema": SCHEMA}
    grafo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investigacion_id: Mapped[str] = mapped_column(Text, nullable=False)
    id_owner: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="CASCADE"))
    instrumento_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    grafo_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parametros: Mapped[dict | None] = mapped_column(JSONB)
    # NIT #6: usar server_default para que el default lo ponga Postgres (como kpi_inferido.fecha_inferencia),
    # evitando mezclar el reloj de Python (datetime.utcnow) con el de la columna.
    fecha_creacion: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
```

Registrar en `shared/models/__init__.py` (import + `__all__`), igual que las demás
tablas, para que quede en `Base.metadata`.

---

## 8. Frontend

### 8.1 `src/api/grafo.ts` (archivo nuevo)

Mismo patrón que `espacio.ts`: usa `pedir()` + `ANALYSIS_URL`. Las tres funciones
del grafo van con `auth: false` en dev (igual que `getEspacioVectorial`), porque
el servicio resuelve el usuario por `DEV_USER_ID`.

```typescript
import { ANALYSIS_URL, pedir } from "./client";

export interface NodoGrafo {
  id: string; idCrudo: string; titulo: string;
  tipo: "Encuesta" | "Entrevista" | "Prueba estandarizada";
  autorId: string; autorNombre: string; kpis: string[]; esPropio: boolean;
}
export interface AristaGrafo {
  origen: string; destino: string; tipo: "kpi_compartido";
  peso: number; kpis: string[];
}
export interface Recomendacion extends NodoGrafo {
  score: number; score_semantico: number; score_kpi: number;
  razon: string; kpis_compartidos: string[];
}
export interface RecomendarRequest {
  instrumentoIds: string[]; autorId?: string;
  w_sem?: number; w_kpi?: number; top_n?: number; min_score?: number;
  excluir_propios?: boolean;   // ← default false en backend; wiring en §3.1
}

export function getAcervoGrafo() {
  return pedir<{ nodos: NodoGrafo[]; aristas: AristaGrafo[] }>(
    `${ANALYSIS_URL}/grafo/acervo`, { auth: false });
}
export function recomendarGrafo(req: RecomendarRequest) {
  return pedir<{ recomendaciones: Recomendacion[]; parametros: Record<string, number>;
    degradado_semantico: boolean }>(
    `${ANALYSIS_URL}/grafo/recomendar`, { method: "POST", body: req, auth: false });
}
export function guardarGrafoInvestigacion(req: {
  investigacionId: string; instrumentoIds: string[]; grafo_snapshot: unknown;
}) {
  return pedir<{ ok: boolean; grafoId: number; instrumentoIdsCrudo: string[] }>(
    `${ANALYSIS_URL}/grafo/investigacion`, { method: "POST", body: req, auth: false });
}
```

> **Nota de patrón (regla del proyecto):** las pantallas nunca importan mocks ni
> hacen fetch directo; todo pasa por `src/api/`. `grafo.ts` cumple esto. El helper
> `pedir()` ya mapea errores a mensajes en español.

### 8.2 Pantalla React Flow

- Dependencia nueva **única**: `@xyflow/react` (v12). Se instala con el gestor del
  proyecto (`bun add @xyflow/react` — el proyecto usa `bun run build`, ver gate).
- Feature nueva: `src/features/grafo/` con `GrafoPage.tsx`, `NodoInstrumento.tsx`
  (nodo custom), `FichaInstrumento.tsx` (panel lateral). Organización por features
  (regla del proyecto). Textos 100% en español.
- Estado: `instrumentosActivos: string[]` (ids = `id_instrumento`). `useEffect`
  sobre `instrumentosActivos` con **debounce ~300 ms** llama `recomendarGrafo`
  (RNF-1 < 1.5 s). Al soltar un nodo en la zona activa (`onDrop` de React Flow) se
  añade su id y se recalcula.
- Colores/tipografía: solo tokens semánticos de `src/styles.css` (regla del
  proyecto); nada de clases de color literales. El estilo de nodo recomendado vs
  propio vs acervo se expresa con tokens existentes o nuevos tokens semánticos.
- Botón «Comenzar investigación»: ejecuta el flujo de §6.3 y navega a `/chat` con
  TanStack Router.

### 8.3 Ruta y navegación

- Ruta nueva `src/routes/_panel.grafo.tsx` → `GrafoPage` (espeja
  `_panel.chat.tsx`: `createFileRoute("/_panel/grafo")` + `head` con meta en
  español).
- Entrada en `src/components/layout/Sidebar.tsx`: añadir a `OPCIONES`
  `{ to: "/grafo", etiqueta: "Grafo de recomendación", icono: Share2 }` donde
  `Share2` es la **referencia del componente** importada de `lucide-react` (NO un
  elemento JSX — resuelve revisión final, NIT #4: `Sidebar.tsx` guarda la referencia
  y renderiza `<Icono .../>` tras desestructurar; pasar JSX rompería el render).
  `Network` ya lo usa «Espacio vectorial», por eso se elige `Share2`.

---

## 9. Discrepancias spec ↔ código y suposiciones (FLAGS)

**[A] — Rutas del backend en el prompt del paso son incorrectas.** El prompt pedía
leer `services/analysis-service/app/main.py` y
`services/analysis-service/app/vectorization/routers/`. El entrypoint real es
`services/analysis-service/main.py` (los routers se importan como
`from app.vectorization.routers import ...`). Resuelto: §4 usa las rutas reales.
*Severidad: baja (ya resuelto).*

**[B] — `01_schema.sql` solo corre en init de volumen limpio.** La tabla nueva es
idempotente, pero una BD ya poblada no la obtiene automáticamente. El PLAN debe
incluir un paso operativo (ejecutar el `CREATE TABLE IF NOT EXISTS` o recrear el
volumen de pruebas). *Severidad: media — operativa, no de diseño.*

**[C] — Fuente del `tipo` de instrumento.** La spec no dice de dónde sale `tipo`.
`sources.py` (RAG) lo infiere de `dc:type` y cae a "Encuesta" por defecto; eso es
poco fiable. El grafo usa `raw_data.tipo_instrumento` (columna canónica real) con
la regla de `map_instrumento.mapear_tipo` replicada localmente (desconocido →
`"Encuesta"` + `logger.warning`; el router emite siempre el literal mapeado). Ver
la nota de normalización en §5. *Severidad: baja — mejora, decisión tomada.*

**[D] — DOS espacios de IDs (crítico).** Detallado en §1. El grafo opera en
`id_instrumento`; `/rag/index` opera en `id_crudo`. La spec §4 trata el `id` del
nodo como si sirviera para ambos. Resuelto exponiendo `idCrudo` en los nodos y
traduciendo en `/grafo/investigacion` (§6.3). **Este es el flag de mayor impacto;
si el revisor discrepa de la traducción, afecta el contrato de los tres
endpoints.** *Severidad: alta — resuelto, pero conviene validación del revisor.*

**[E] — `coleccion`/`total_chunks` en la respuesta de `/grafo/investigacion`.** La
spec los pide; con la decisión «el frontend llama a `/rag/index`» no los puede
producir analysis-service. Resuelto devolviendo `instrumentoIdsCrudo` + `grafoId`;
`coleccion`/`total_chunks` los obtiene el frontend del `IndexResponse` real.
**Precisión (hallazgo NIT #5):** el `IndexResponse` real de `/rag/index`
(verificado en `visualization-service/app/schemas/rag.py`) es
`{ coleccion, total_chunks, instrumentos, mensaje }` — **no** incluye un campo
`ok`. El `ok` pertenece exclusivamente a la respuesta de `/grafo/investigacion`
(`{ ok, grafoId, instrumentoIdsCrudo }`). El frontend lee `coleccion`/
`total_chunks` del `IndexResponse` y **no** espera `ok` de `/rag/index`. La spec
explícitamente dejó esta rama como «decisión de implementación». *Severidad:
media — desviación justificada del literal; equivalencia de campos corregida.*

**[F] — Suposición no verificada: cobertura de `summary_instrument`.** El grafo
asume que los instrumentos del acervo tienen vector en `summary_instrument` y
filas en `kpi_inferido`. No se verificó qué instrumentos sembrados cumplen ambas
cosas (depende del estado de la BD/Chroma de pruebas). El diseño degrada bien
(instrumentos sin vector → `sim_semantica` no los puntúa; sin KPIs →
`solape_kpi=0`), pero el gate §9 de la spec («recomendar devuelve candidatos
reales») exige datos sembrados coherentes. *Severidad: media — a confirmar en
verificación, no bloquea el diseño.*

**[G] — Suposición: `auth: false` en dev para `/grafo/*`.** Espeja
`getEspacioVectorial`. Verificado que `UsuarioActual` resuelve por `DEV_USER_ID`
en `AUTH_DEV_MODE`. En producción (JWT) habría que ajustar igual que el resto del
servicio; fuera del alcance actual. *Severidad: baja.*

---

## 10. Confirmación: no se duplica lógica de vectores

Verificado contra `kpi_search.py`, `chroma_client.py`, `embeddings.py` y
`espacio.py`:

- El motor de score **reutiliza** `chroma_client.get_or_create_collection`,
  `chroma_client.query`, `chroma_client.get_point` y
  `kpi_search._distance_to_score`. No reimplementa coseno, no reinstancia cliente
  Chroma, no recalcula embeddings (lee vectores ya persistidos de
  `summary_instrument`, igual que `espacio.py` y `kpi_search`).
- El seam `client=None` → `get_or_create_collection(name, client=client)` es el
  mismo que ya usan `chroma_client`, `kpi_search` y `espacio`.
- La única pieza nueva de cálculo es el **Jaccard sobre conjuntos de KPIs**
  (función pura, sin vectores), que no existe en el código y es el aporte
  estructural del componente.

---

## 11. Qué se puede testear (y cómo)

- **Unit (puro, sin IO):** `_jaccard`, la combinación de score, el etiquetado de
  `razon`, la validación de pesos (suma 1.0), el clamp de `top_n`.
- **Integration (Chroma efímero):** `sim_semantica` numérico contra vectores
  sembrados conocidos; degradación forzando fallo del cliente inyectado.
- **Integration (BD de pruebas):** `GET /grafo/acervo` devuelve nodos+aristas de
  instrumentos sembrados; `POST /grafo/recomendar` ordena por score; traducción
  `id_instrumento → id_crudo` en `/grafo/investigacion`.
- **Frontend:** `bun run build` verde (gate). Smoke manual del arrastre/soltar y
  del botón «Comenzar investigación».

Un diseño así de inyectable (cliente Chroma y sesión BD como parámetros, funciones
puras separadas del IO) es la señal de que es testeable sin montar toda la
infraestructura.

---

## 12. Orden de implementación (para el PLAN)

1. `core/grafo_recomendador.py` (Jaccard + semántico + degradación + seam de
   cliente) con sus unit/integration tests.
2. `routers/grafo.py` (3 endpoints, schemas Pydantic con validación §3) +
   registro en `main.py`.
3. Schema (`01_schema.sql`, tabla nueva en el bloque transaccional) +
   `shared/models/grafo_investigacion.py` + registro en `__init__.py`.
4. `src/api/grafo.ts`.
5. `@xyflow/react` + `features/grafo/` (GrafoPage, nodo custom, zona drop,
   debounce, botón).
6. Ruta `_panel.grafo.tsx` + entrada en `Sidebar.tsx`.
7. Verificación: backend con datos sembrados + `bun run build` verde.

---

## 13. Respuestas a hallazgos de revisión

Revisión referenciada: `design-review.json` (veredicto `CHANGES_REQUESTED`,
1 HIGH / 2 MEDIUM / 3 NIT) y `design-review.md`. Las seis se **abordan**; ninguna
se backloguea ni se ignora, y los cambios se alinean con la spec (fuente de
verdad). Resumen:

- **#1 [HIGH] — wiring de `excluir_propios`.** ABORDADO. Se declaró el campo
  `excluir_propios: bool = False` en el schema Pydantic del router, se añadió
  `excluir_propios?: boolean` al `RecomendarRequest` TS (§8.1) y el router lo pasa
  al core (que ya lo tenía). Se fijó la regla única en §3.1 (y se enlazó desde
  §6.2): `excluir_propios == true` excluye los instrumentos cuyo `autorId ==
  (request.autorId ?? usuario_actual.usuario_id)`; la mera presencia de `autorId`
  **no** activa la exclusión. Se eliminó la frase ambigua «del flag `autorId` / un
  bool explícito» de §6.2. Esto aterriza la spec §4.2 («excluye… los del propio
  autor, según el flag»).

- **#2 [MEDIUM] — fuente/normalización del `tipo`.** ABORDADO. §5 ahora refiere la
  lógica de `map_instrumento.mapear_tipo` (keyed sobre `raw_data.tipo_instrumento`
  lowercase-snake), **no** la de `sources.py` (que parte de `dc:type` y es poco
  fiable). Como `map_instrumento` vive en instrument-service (no importable), el
  grafo **replica** el mismo diccionario y regla con un helper local, documentando:
  desconocido → `"Encuesta"` + `logger.warning`, y la garantía de que el router
  SIEMPRE emite el literal mapeado ({Encuesta, Entrevista, Prueba estandarizada}),
  nunca el crudo — cumpliendo el union TS de `NodoGrafo.tipo`. Flag §9-C
  actualizado.

- **#3 [MEDIUM] — umbral de la razón `"Alta afinidad"`.** ABORDADO. §2.3 fija la
  regla sobre los **scores crudos** `[0,1]`: `alto_sem = score_semantico >= 0.5`,
  `alto_kpi = score_kpi >= 0.5`; si ambos → `"Alta afinidad (contenido + KPIs)"`;
  elif `score_semantico >= score_kpi` → `"Contenido similar"`; else → `"KPIs
  compartidos: " + join(kpis_compartidos)`. Se documentó que `0.5` es sobre el
  score crudo (no ponderado) y se eliminó la frase incoherente «normalizando por su
  peso».

- **#4 [NIT] — cota superior de `top_n`.** ABORDADO. §3 justifica: `100` es defensa
  propia del grafo contra requests abusivos, independiente del `[1,20]` de
  `_clamp_top_k` del RAG (dominio distinto: chunks).

- **#5 [NIT] — `IndexResponse` no tiene `ok`.** ABORDADO. §9-E y la nota de §6.3
  precisan que el `IndexResponse` real es `{coleccion, total_chunks, instrumentos,
  mensaje}` (sin `ok`, verificado en `schemas/rag.py`); el `ok` es de la respuesta
  de `/grafo/investigacion`. El frontend lee `coleccion`/`total_chunks` del
  `IndexResponse` y no espera `ok` de él.

- **#6 [NIT] — `grafo_snapshot` sin cota.** ABORDADO. §3.2 añade una cota
  pragmática: rechazo 422 si el snapshot serializado supera 1 MB (y límite blando
  opcional de nodos+aristas). §3 y §6.3 reconocen y referencian la validación. Se
  mantiene opaco a nivel estructural por ser trazabilidad de un usuario de confianza
  en dev, pero ya no «sin validar».
