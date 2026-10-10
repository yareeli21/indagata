# Especificación técnica — Grafo de Recomendación de Instrumentos

> **Estado:** Diseño aprobado, pendiente de implementación.
> **Rama de trabajo:** `elotro-back`.
> **Tipo de componente:** Capa de Inteligencia Colaborativa (Business Intelligence) sobre el acervo de instrumentos de investigación educativa.

---

## 1. Visión general

El **Grafo de Recomendación** es una pantalla interactiva donde un investigador
visualiza el acervo de instrumentos como un grafo, selecciona los instrumentos
con los que quiere trabajar, y el sistema le **recomienda en tiempo real** con
qué otros instrumentos (de otros investigadores) puede complementar su
investigación. Las recomendaciones combinan dos señales:

1. **Estructural** — instrumentos que comparten KPIs (datos en `kpi_inferido`).
2. **Semántica** — instrumentos con contenido similar (vectores en la colección
   `summary_instrument` de ChromaDB).

Esto convierte el acervo en un **sistema de descubrimiento**: el investigador no
solo busca, sino que el sistema le sugiere activamente conexiones que no sabía
que existían, al estilo de un *recommendation engine* de BI enterprise
(comparable a Neo4j Bloom o el grafo de citaciones de Google Scholar, pero
aplicado a instrumentos educativos).

### 1.1 Por qué es valioso (justificación BI para la tesis)

| Capacidad BI | Cómo la implementa Indagata |
|---|---|
| **Discovery** | El grafo revela patrones de KPIs y similitud no evidentes |
| **Recommendation** | Score híbrido estructural (KPIs) + semántico (vectores) |
| **Collaboration** | Instrumentos de otros investigadores reutilizables |
| **Lineage / trazabilidad** | Cada investigación guarda su grafo como mapa |
| **Augmentation** | El set resultante alimenta directamente el chat RAG |

La diferencia frente a un filtro simple es el **score híbrido**: no es "comparten
un KPI" ni "texto parecido" por separado, sino una combinación ponderada y
ajustable de ambas señales. Esa fusión grafo + vector store es lo que hace al
componente difícil de replicar con herramientas genéricas.

---

## 2. Requisitos

### 2.1 Funcionales

- **RF-1.** El investigador ve sus instrumentos propios como nodos de un grafo.
- **RF-2.** Los nodos tienen color por tipo (encuesta / entrevista / prueba),
  tamaño proporcional al número de KPIs asociados, y aristas entre instrumentos
  que comparten al menos un KPI.
- **RF-3.** Al hacer clic en un nodo, se muestra su ficha (título, tipo, KPIs,
  autor, fragmento).
- **RF-4.** El investigador arrastra instrumentos a una **zona de investigación
  activa**. Al soltar un nodo ahí, el sistema recalcula recomendaciones **en
  tiempo real**.
- **RF-5.** Las recomendaciones aparecen como nodos nuevos (de otros
  investigadores) con un estilo visual distinto, agrupados por razón de
  recomendación (KPI compartido / similitud semántica).
- **RF-6.** El investigador puede arrastrar un nodo recomendado a su
  investigación activa; el grafo lo reincorpora y vuelve a recalcular.
- **RF-7.** Un botón **"Comenzar investigación"** toma el set activo
  (propios + complementarios), lo indexa en el RAG (`POST /rag/index`) y abre el
  chat.
- **RF-8.** El grafo de cada investigación se persiste (nodos activos +
  recomendados mostrados) para trazabilidad.

### 2.2 No funcionales

- **RNF-1.** La recomendación en tiempo real debe responder en < 1.5 s para no
  romper la fluidez de arrastrar/soltar.
- **RNF-2.** La interfaz permanece 100% en español.
- **RNF-3.** Reutiliza la infraestructura existente (ChromaDB `summary_instrument`,
  `kpi_inferido`, el patrón de `/rag/index`). No introduce bases de datos nuevas.
- **RNF-4.** El grafo debe degradar con gracia: si ChromaDB no responde, aún
  muestra recomendaciones estructurales (por KPI) desde Postgres.

---

## 3. El score híbrido (corazón del componente)

Dado un conjunto de instrumentos activos `A = {a1, a2, ...}` seleccionados por el
investigador, para cada instrumento candidato `c` del acervo (de otros
investigadores, no ya en `A`) se calcula:

```
score(c) = w_sem * sim_semantica(c, A) + w_kpi * solape_kpi(c, A)
```

Donde:

- **`sim_semantica(c, A)`** = máxima similitud coseno entre el vector de `c` y los
  vectores de los instrumentos en `A`, tomada de la colección
  `summary_instrument`. Rango [0, 1]. Se reutiliza `_distance_to_score` de
  `kpi_search.py` (`score = 1 - distancia_coseno`).

- **`solape_kpi(c, A)`** = coeficiente de Jaccard entre el conjunto de KPIs de `c`
  y la unión de KPIs de `A`:
  ```
  solape_kpi(c, A) = |KPIs(c) ∩ KPIs(A)| / |KPIs(c) ∪ KPIs(A)|
  ```
  Rango [0, 1]. Los KPIs salen de `kpi_inferido` (join por `id_procesado`).

- **Pesos por defecto:** `w_sem = 0.6`, `w_kpi = 0.4`. Configurables en el request
  (si el investigador quiere priorizar coincidencia de KPIs sobre similitud de
  contenido, o viceversa). Deben sumar 1.0.

**Razón de recomendación:** cada candidato se etiqueta según qué señal dominó:
- `sim_semantica` dominante → *"Contenido similar"*
- `solape_kpi` dominante → *"KPIs compartidos: X, Y"* (se listan los compartidos)
- ambas altas → *"Alta afinidad (contenido + KPIs)"*

**Umbral mínimo:** solo se devuelven candidatos con `score(c) >= 0.15` (evita
ruido). Configurable.

### 3.1 Por qué Jaccard y no conteo simple

El conteo simple de KPIs compartidos favorece a instrumentos con muchos KPIs
(más probabilidad de coincidir por azar). Jaccard normaliza por el tamaño de la
unión, premiando afinidad real, no volumen. Es la métrica estándar para
similitud de conjuntos en sistemas de recomendación.

---

## 4. Contrato del backend

Nuevo router en **analysis-service** (dueño del dominio KPI + vectores), prefijo
`/grafo`. Se llama directo vía `ANALYSIS_URL` desde el frontend (igual que
`espacio.ts` y el score de KPIs), porque el gateway no proxea `/vectorizacion/*`
ni `/grafo/*`.

### 4.1 `GET /grafo/acervo`

Devuelve el grafo base: todos los instrumentos del acervo como nodos, con sus
KPIs y las aristas de KPI compartido.

**Respuesta:**
```json
{
  "nodos": [
    {
      "id": "12",
      "titulo": "Encuesta de compromiso estudiantil",
      "tipo": "Encuesta",
      "autorId": "3",
      "autorNombre": "Investigador Demo",
      "kpis": ["Learner Engagement Metrics", "Student Retention Rate"],
      "esPropio": true
    }
  ],
  "aristas": [
    { "origen": "12", "destino": "7", "tipo": "kpi_compartido", "peso": 2,
      "kpis": ["Student Retention Rate", "Dropout Rate"] }
  ]
}
```

- `esPropio` = true si el instrumento pertenece al usuario autenticado.
- `peso` de la arista = nº de KPIs compartidos entre los dos nodos.

### 4.2 `POST /grafo/recomendar`

El endpoint de tiempo real. Recibe el set activo y devuelve recomendaciones.

**Request:**
```json
{
  "instrumentoIds": ["12", "7"],
  "autorId": "3",
  "w_sem": 0.6,
  "w_kpi": 0.4,
  "top_n": 10,
  "min_score": 0.15
}
```

**Respuesta:**
```json
{
  "recomendaciones": [
    {
      "id": "21",
      "titulo": "Entrevista sobre permanencia universitaria",
      "tipo": "Entrevista",
      "autorId": "5",
      "autorNombre": "Otra investigadora",
      "kpis": ["Student Retention Rate", "Student Support Services"],
      "score": 0.73,
      "score_semantico": 0.68,
      "score_kpi": 0.80,
      "razon": "Alta afinidad (contenido + KPIs)",
      "kpis_compartidos": ["Student Retention Rate"]
    }
  ],
  "parametros": { "w_sem": 0.6, "w_kpi": 0.4 }
}
```

Excluye los instrumentos ya en `instrumentoIds` y (opcionalmente) los del propio
autor, según el flag. Ordena por `score` descendente.

**Lógica interna:**
1. Carga los vectores de `instrumentoIds` desde `summary_instrument`.
2. Carga los KPIs de `instrumentoIds` desde `kpi_inferido` (join a `kpi.nombre`).
3. Para cada candidato del acervo no en el set: calcula `sim_semantica` (query a
   Chroma) y `solape_kpi` (Jaccard sobre KPIs), combina con los pesos.
4. Filtra por `min_score`, ordena, corta a `top_n`, etiqueta la razón.

**Degradación:** si Chroma falla, `w_sem` se fuerza a 0 y solo se usa el componente
de KPI (se avisa en la respuesta con un flag `degradado_semantico: true`).

### 4.3 `POST /grafo/investigacion`

Persiste el grafo de una investigación (RF-8) y dispara el indexado RAG (RF-7).

**Request:**
```json
{
  "investigacionId": "res-123",
  "instrumentoIds": ["12", "7", "21"],
  "grafo_snapshot": { "nodos": [...], "aristas": [...], "recomendados": [...] }
}
```

**Acción:** guarda el snapshot en la tabla nueva `grafo_investigacion` y llama
internamente a la misma lógica de `/rag/index` (o devuelve los ids para que el
frontend llame a `/rag/index`, decisión de implementación). Devuelve
`{ ok, coleccion, total_chunks }`.

---

## 5. Persistencia — tabla nueva `grafo_investigacion`

No destructiva, aditiva al schema:

```sql
CREATE TABLE IF NOT EXISTS tt_rag.grafo_investigacion (
    grafo_id          SERIAL PRIMARY KEY,
    investigacion_id  TEXT    NOT NULL,          -- id opaco del frontend (res-<ts>)
    id_owner          INTEGER REFERENCES usuario(usuario_id) ON DELETE CASCADE,
    instrumento_ids   JSONB   NOT NULL,          -- ["12","7","21"] set activo final
    grafo_snapshot    JSONB   NOT NULL,          -- nodos + aristas + recomendados mostrados
    parametros        JSONB,                     -- {w_sem, w_kpi, min_score}
    fecha_creacion    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Esto da la **trazabilidad** (RF-8): se puede reconstruir qué grafo vio el
investigador y qué recomendaciones aceptó, útil para auditoría y para la tesis.

---

## 6. Frontend — React Flow

### 6.1 Por qué React Flow

- Pensado para grafos interactivos con nodos arrastrables (RF-4, RF-6).
- Soporta nodos custom (componentes React), zonas de drop, agrupación.
- Se integra con el estado de React/TanStack sin fricción.
- Alternativas descartadas: D3.js (demasiado bajo nivel para arrastrar/soltar),
  Cytoscape (más orientado a grafos estáticos de análisis).

Dependencia nueva: `@xyflow/react` (React Flow v12). Es la única dependencia
nueva que introduce esta feature.

### 6.2 Estructura de pantalla

Nueva ruta `_panel.grafo.tsx` → `features/grafo/GrafoPage.tsx`.

Tres zonas visuales dentro del canvas de React Flow:

```
┌─────────────────────────────────────────────────────────────┐
│  ACERVO (nodos grises)        │   INVESTIGACIÓN ACTIVA        │
│  todos los instrumentos       │   (zona resaltada, drop here) │
│  ○ ○ ○ ○ ○                    │        ◉ ◉                    │
│    ○ ○ ○                       │                               │
│                                │   RECOMENDADOS (aparecen al   │
│                                │   soltar, color distinto)     │
│                                │        ◆ ◆ ◆                  │
└─────────────────────────────────────────────────────────────┘
            [ Comenzar investigación → ]
```

- **Nodo custom** (`NodoInstrumento.tsx`): badge de tipo, nombre, chip con nº de
  KPIs, indicador de "recomendado" / "propio".
- **Zona activa**: un área de drop (React Flow `onDrop`); al soltar un nodo ahí
  se añade a `instrumentosActivos` y se dispara `recomendar`.
- **Panel lateral** (`FichaInstrumento.tsx`): al hacer clic en un nodo, su ficha.

### 6.3 Flujo de datos (tiempo real)

```
Montaje → getAcervoGrafo()  → pinta nodos + aristas base
   │
Arrastrar nodo a zona activa → setInstrumentosActivos([...prev, id])
   │                              ↓ (useEffect sobre instrumentosActivos)
   │                          recomendarGrafo({instrumentoIds, pesos})
   │                              ↓
   │                          añade/actualiza nodos recomendados (animados)
   │
"Comenzar investigación" → guardarGrafoInvestigacion() → /rag/index → navega al chat
```

El `useEffect` sobre `instrumentosActivos` con un **debounce de ~300 ms** evita
llamadas excesivas al arrastrar varios nodos seguidos (cumple RNF-1).

### 6.4 Nuevas funciones en `src/api/grafo.ts` (archivo nuevo)

```typescript
export interface NodoGrafo { id, titulo, tipo, autorId, autorNombre, kpis, esPropio }
export interface AristaGrafo { origen, destino, tipo, peso, kpis }
export interface Recomendacion extends NodoGrafo { score, score_semantico, score_kpi, razon, kpis_compartidos }

export function getAcervoGrafo(): Promise<{nodos: NodoGrafo[], aristas: AristaGrafo[]}>
export function recomendarGrafo(req): Promise<{recomendaciones: Recomendacion[], parametros}>
export function guardarGrafoInvestigacion(req): Promise<{ok, coleccion, total_chunks}>
```

Todas llaman a `ANALYSIS_URL/grafo/*` con el patrón de `espacio.ts`.

---

## 7. Dependencias con el estado actual

| Ya existe (reutilizable) | Falta construir |
|---|---|
| `summary_instrument` en Chroma (vectores de instrumentos) | Router `/grafo/*` en analysis-service |
| `kpi_inferido` (relación instrumento↔KPI) | Score híbrido (Jaccard + coseno) |
| `_distance_to_score`, `chroma_client.query` | Tabla `grafo_investigacion` |
| `/rag/index` (indexado de investigación) | Pantalla React Flow + ruta |
| Patrón `espacio.ts` (llamada directa a ANALYSIS_URL) | `src/api/grafo.ts` |
| `buscarRelacionados` (lógica mock, referencia conceptual) | Dependencia `@xyflow/react` |

---

## 8. Plan de implementación (orden)

1. **Backend — score híbrido:** `core/grafo_recomendador.py` (Jaccard + semántico)
   con el seam de inyección de cliente Chroma para tests.
2. **Backend — router:** `routers/grafo.py` con los 3 endpoints; registrar en
   `main.py`.
3. **Schema + ORM:** tabla `grafo_investigacion` + `shared/models/grafo_investigacion.py`.
4. **Frontend — API:** `src/api/grafo.ts`.
5. **Frontend — grafo:** instalar `@xyflow/react`, crear `GrafoPage`, nodos custom,
   zona de drop, debounce de recomendación, botón "Comenzar investigación".
6. **Ruta y navegación:** `_panel.grafo.tsx` + entrada en el menú lateral.
7. **Verificación:** backend con instrumentos sembrados (recomendar devuelve
   candidatos reales con score), build del frontend verde.

---

## 9. Verificación de aceptación (gate)

- `GET /grafo/acervo` devuelve nodos + aristas con los instrumentos sembrados.
- `POST /grafo/recomendar` con 2-3 instrumentos activos devuelve recomendaciones
  ordenadas por score, con razón y KPIs compartidos correctos.
- Jaccard y similitud coseno verificables numéricamente contra un caso conocido.
- Degradación: con Chroma caído, recomendar aún responde (solo KPI,
  `degradado_semantico: true`).
- Frontend: arrastrar un nodo a la zona activa dispara recomendaciones nuevas en
  < 1.5 s; "Comenzar investigación" indexa y abre el chat.
- `bun run build` verde.

---

## 10. Consideraciones para la tesis

- El score híbrido es un aporte metodológico documentable: fusión de recuperación
  estructural (teoría de grafos / Jaccard) y semántica (embeddings densos +
  similitud coseno), con pesos ajustables.
- La trazabilidad del grafo (`grafo_investigacion`) permite estudiar *cómo* los
  investigadores arman sus investigaciones — datos para análisis de uso.
- Limitación honesta: la calidad de las recomendaciones depende del volumen y
  diversidad del acervo. Con pocos instrumentos las conexiones son escasas; por
  eso los datos sintéticos (30 instrumentos con KPIs variados) son el sustento de
  la demostración.
