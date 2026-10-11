# Verificación fail-closed — Grafo de Recomendación (rama `elotro-back`)

Fecha de ejecución: ver historial del step. Repo: `c:\Users\yarel\Documents\indagata\indagata`.
Todas las comprobaciones se corrieron de verdad; abajo va la narrativa y los resultados.
**No se hizo commit ni push.**

## Branch safety

```
git -C c:\Users\yarel\Documents\indagata\indagata rev-parse --abbrev-ref HEAD
→ elotro-back
```

HEAD está en `elotro-back`. Se continúa.

---

## 1. Python — `ast.parse` de los tres fuentes (venv del proyecto)

Intérprete: `c:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe`.

Se parsearon con `ast.parse` (UTF-8):

- `services/analysis-service/app/vectorization/core/grafo_recomendador.py`
- `services/analysis-service/app/vectorization/routers/grafo.py`
- `shared/models/grafo_investigacion.py`

Resultado: **`AST OK`** para los tres. Sin `SyntaxError`.

Adicional: el módulo `grafo_recomendador` **importa limpio** en el venv
(`import app.vectorization.core.grafo_recomendador` → `import OK`), lo que confirma
que las dependencias del motor de score resuelven.

**Estado: PASS.**

---

## 2. Chequeo unitario del score híbrido (sin Docker, seam `client`)

Script: `.agents/tasks/grafo/_unit_score_check.py`, ejecutado con el venv.
Caso en memoria con KPIs y vectores conocidos; cada aserción se compara contra
un valor **calculado a mano**.

Acervo de prueba:

- Activo (id 1): KPIs {10, 20} → unión activa = {10, 20}.
- Candidato C2 (id 2): KPIs {20, 30}.
- Candidato C3 (id 3): KPIs {10, 20}.
- Candidato C4 (id 4): KPIs {40}.

### Jaccard (a mano)

- C2 vs {10,20}: |{20}| / |{10,20,30}| = 1/3 ≈ 0.3333 → **PASS**
- C3 vs {10,20}: 2/2 = 1.0 → **PASS**
- C4 vs {10,20}: 0/3 = 0.0 → **PASS**
- unión vacía → 0.0 → **PASS**

### Score combinado = `w_sem*sim + w_kpi*jaccard` (w_sem=0.6, w_kpi=0.4)

Semánticos inyectados vía fake de `_sim_semantica_por_candidato` (no degradado):

- C2: 0.6·0.8 + 0.4·(1/3) = 0.48 + 0.13333 = **0.6133** → PASS
- C3: 0.6·0.2 + 0.4·1.0 = 0.12 + 0.40 = **0.52** → PASS
- C4: 0.6·0.9 + 0.4·0.0 = **0.54** → PASS
- `parametros.w_sem` = 0.6 (no degradado) → PASS

### Etiqueta `razon` (sobre scores crudos [0,1], `UMBRAL_ALTO = 0.5`)

- (sem 0.8, kpi 0.6, compartidos) → "Alta afinidad (contenido + KPIs)" → PASS
- (sem 0.2, kpi 0.4, ["K20"]) → "KPIs compartidos: K20" → PASS
- (sem 0.45, kpi 0.1, []) → "Contenido similar" → PASS
- (sem 0.3, kpi 0.3, []) → "Contenido similar" (fallback) → PASS
- C2 (sem 0.8 > kpi 0.333) → "Contenido similar" → PASS
- C3 (kpi 1.0 ≥ sem 0.2, compartidos) → "KPIs compartidos: K10, K20" → PASS

### Degradación con gracia (RNF-4) vía el seam `client`

Se inyectó un cliente falso cuyo `get_or_create_collection` lanza, para forzar
la rama de degradación de forma determinista (en vez de depender de que el
servidor Chroma esté caído):

- `degradado_semantico` = True → PASS
- `w_sem_eff` forzado a 0.0 → PASS
- Score = 0.4·jaccard: C3 = 0.4, C2 = 0.1333, C4 = 0.0 → PASS
- `score_semantico` = 0.0 en todos los candidatos → PASS
- Orden desc por score: primero C3 → PASS
- `razon` de C3 = "KPIs compartidos: K10, K20" → PASS

El traceback que imprime el script en esta rama es el `logger.warning(..., exc_info=True)`
esperado de la degradación: se **registra**, no se propaga; `recomendar` devuelve
`degradado=True`.

Resultado del script: **`RESULT: PASS (toda la matemática del score cuadra)`**
(25 aserciones, todas PASS).

**Estado: PASS.**

### Nota sobre el seam `client=None`

Con `client=None` el motor resuelve el cliente Chroma real
(`chroma_client.get_client()`). Como el contenedor `indagata_chromadb` está arriba
pero la colección `summary_instrument` está vacía, esa ruta **no degrada**: devuelve
`sim=0.0` para todos y `degradado=False` (comportamiento correcto). Por eso la
prueba de degradación usa un cliente inyectado que falla, que es el uso previsto
del seam para ejercitar RNF-4 sin depender del estado del servidor.

---

## 3. Registro estático (schema + router)

- `infrastructure/postgres/init/01_schema.sql`: el archivo hace
  `CREATE SCHEMA IF NOT EXISTS tt_rag;` + `SET search_path TO tt_rag, public;`
  y luego `CREATE TABLE IF NOT EXISTS grafo_investigacion (...)` con
  `idx_grafo_inv_owner`. Es decir, `tt_rag.grafo_investigacion` **está presente**. → PASS
- `services/analysis-service/main.py`: `from app.vectorization.routers import (..., grafo, ...)`
  e `app.include_router(grafo.router)`. Import + include **presentes**. → PASS

**Estado: PASS.**

---

## 4. Frontend — `bun add @xyflow/react && bun run build`

Directorio: `pixel-perfect-pixel/`. `bun 1.4.2`.

- `bun add @xyflow/react` → `installed @xyflow/react@12.12.0`.
- `bun run build` (`vite build`) → compiló los tres entornos
  (client, SSR, nitro). `✓ 2768 modules transformed` (client),
  `✓ 159 modules transformed` (SSR), `✓ 2734 modules transformed` (nitro).
  Se emitieron los chunks del grafo (`_panel.grafo-*.js` / `.mjs`).
  **Sin errores de TypeScript**, exit code 0.

**Estado: PASS.**

---

## 5. Endpoints en vivo (Docker)

Docker **está arriba** (`docker ps`): `indagata_analysis_service`, `indagata_postgres`,
`indagata_redis`, `indagata_ollama`, `indagata_chromadb`, `liverpool-talento-frontend-1`.

Se intentó `GET http://localhost:8002/grafo/acervo` → **HTTP 404**.
Al leer `GET /openapi.json` del servicio, las rutas publicadas son solo las de
vectorización/KPIs clásicas (`/health`, `/vectorizacion/*`); **no aparece ningún
`/grafo/*`**. El contenedor `indagata_analysis_service` lleva ~15 h arriba y fue
construido **antes** de que se agregara el router del grafo, por lo que su imagen
no contiene la feature.

Decisión: **no se ejercitó Docker en vivo** para el grafo. Rebuild/restart del
servicio es un efecto secundario fuera del alcance seguro de un step de
verificación. La matemática del score (chequeo unitario, §2) y el build del
frontend (§4) sí se corrieron y pasaron, que es lo que define `passed`.

**Estado: NO EJERCITADO (imagen desplegada obsoleta; no se redeployó).**

---

## Veredicto

| # | Comprobación | Resultado |
|---|---|---|
| 1 | `ast.parse` de los 3 fuentes (venv) | PASS |
| 2 | Score híbrido (Jaccard + combinado + razón + degradación) | PASS |
| 3 | `tt_rag.grafo_investigacion` en schema + router en `main.py` | PASS |
| 4 | `bun add @xyflow/react && bun run build` (sin errores TS) | PASS |
| 5 | Endpoints en vivo (Docker) | No ejercitado (imagen obsoleta) |

El build pasa y la matemática del score cuadra con los valores calculados a mano.
`passed = true`. El único punto no ejercitado (§5) es por imagen desplegada
obsoleta, no por fallo de la feature, y la rúbrica de `passed` no lo exige.
