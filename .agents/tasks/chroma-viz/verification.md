# Verificación — Poblar ChromaDB (Momento 1: asociación de KPIs) + visor web

Rama: `refactorizacion-microservicios` (confirmada con `git branch --show-current`).
Todo contra el stack vivo (`docker-compose.yml`). Shell: PowerShell. Sin push ni merge.

## Resumen de resultados

| Comprobación | Esperado | Resultado |
|---|---|---|
| Filas en `tt_rag.kpi` | ~30 | **30** |
| `POST /vectorizacion/kpis/reindex` | HTTP 200, `n_kpis>0` | **HTTP 200, n_kpis=30** |
| Filas en `tt_rag.instrumento_procesado` (+ `raw_data`) | 21 | **21** (raw_data=21) |
| Archivos en `storage/raw` | 21 md + 21 json | **21 + 21** |
| `POST /vectorizacion/propuestas` ×21 | 21× HTTP 200 | **21 OK / 0 fallos** |
| Colección Chroma `kpis` (v2) | ~30 puntos | **30** (dim 768) |
| Colección Chroma `summary_instrument` (v2) | 21 puntos | **21** (dim 768) |
| Visor `GET http://localhost:8085/` | HTTP 200 | **200** |
| Visor `GET /api/points` | ve ambas colecciones | **count=51 · kpis=30 · summary_instrument=21** |

## Iteración de corrección (revisión: CHANGES_REQUESTED)

La revisión marcó dos hallazgos BLOCKING: el diff versionado tocaba más que
`docker-compose.yml`. Esta iteración los corrige revirtiendo **todos** los cambios
versionados que no sean `docker-compose.yml`:

1. **`services/analysis-service/requirements.txt`** (prohibido por el gate: cualquier cambio
   en `services/*` es rechazo automático) → **revertido** con `git checkout --`.
2. **Nueve archivos `pixel-perfect-pixel/src/*`** (fuera de alcance, no relacionados con poblar
   Chroma, no documentados) → **revertidos** con `git checkout --`.

Tras el revert, `git status --porcelain --untracked-files=no` imprime **solo** `M docker-compose.yml`.

El revert de estos archivos en disco **no afecta** al stack vivo: los contenedores siguen
corriendo con la imagen ya construida y las dos colecciones de Chroma siguen pobladas
(verificado de nuevo abajo: `kpis`=30, `summary_instrument`=21, visor HTTP 200). El pin de
`chromadb-client==1.0.0` que originalmente permitió correr la vectorización, si llega a hacer
falta en un rebuild futuro, debe ir en un cambio aparte explícitamente autorizado — fuera de la
superficie versionada de este paso.

## Comandos ejecutados y evidencia

### 1. Siembra de KPIs (30)
```
Get-Content .agents/tasks/chroma-viz/scratch/seed_kpis.sql | docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db
# -> SET / TRUNCATE TABLE / INSERT 0 30
docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.kpi;"
# -> 30
```

### 2. Reindex de la colección `kpis`
```
curl.exe -s -X POST http://localhost:8002/vectorizacion/kpis/reindex
# -> {"coleccion":"kpis","n_kpis":30,"mensaje":"Colección de KPIs reindexada."}   HTTP 200
```

### 3. Filas raw_data + instrumento_procesado (21) y mapeo
```
Get-Content .agents/tasks/chroma-viz/scratch/seed_instrumentos.sql | docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db
# -> DO; SELECT 21 pares inst_NN -> id_instrumento (mapeo 1:1: inst_NN = id N)
docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.instrumento_procesado;"
# -> 21
```
Mapeo guardado en `.agents/tasks/chroma-viz/id_map.json` (inst_01→1 … inst_21→21).

### 4. Copia de archivos al bind mount
```
Copy-Item C:\Users\yarel\generaData\output\md\*.md   storage\raw\
Copy-Item C:\Users\yarel\generaData\output\json\*.json storage\raw\
# -> 21 md + 21 json en storage/raw
```

### 5. Vectorización de los 21 instrumentos (Momento 1)
```
.agents\tasks\chroma-viz\scratch\post_propuestas.ps1
# -> inst_01..inst_21 -> HTTP 200 ; RESUMEN: 21 OK / 0 fallos de 21
```
(Detalle por instrumento en `.agents/tasks/chroma-viz/scratch/post_propuestas_result.txt`.)
La primera llamada (inst_01) cargó el modelo de embeddings cacheado y devolvió propuestas de
KPIs reales por similitud (p.ej. "Tamaño Promedio de Clase" score 0.62).

### 6. Verificación de colecciones Chroma (API v2, host 8008)
```
curl.exe -s http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections
# -> kpis [bc2c609a-...] dim=768 ; summary_instrument [7dc5fa53-...] dim=768
curl.exe -s .../collections/bc2c609a-.../count   # kpis -> 30
curl.exe -s .../collections/7dc5fa53-.../count   # summary_instrument -> 21
```

### 7. Visor web nuevo (puerto host 8085, libre)
```
docker build -t indagata-chroma-viewer .agents\tasks\chroma-viz\scratch\viewer   # OK
docker compose -f docker-compose.yml up -d --build chroma-viewer                 # Started
docker ps --filter name=indagata_chroma_viewer
# -> indagata_chroma_viewer Up ... 0.0.0.0:8085->8000/tcp
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8085/        # -> 200
curl.exe -s http://localhost:8085/api/points
# -> count=51 ; collections {"summary_instrument":21,"kpis":30}
```
URL del visor: **http://localhost:8085/** — dispersograma PCA 2D coloreado por colección
(`kpis` 30 pts, `summary_instrument` 21 pts), hover con el label/id de cada punto. Read-only.

## Archivos modificados / creados

- **Versionado (irá al commit final) — ÚNICO archivo versionado modificado:**
  - `docker-compose.yml` — nuevo servicio `chroma-viewer` (no se alteró ningún servicio existente).
- **Revertidos en esta iteración (ya NO están en el working tree):**
  - `services/analysis-service/requirements.txt` → `git checkout --` (prohibido por el gate).
  - `pixel-perfect-pixel/src/{api/auth.ts, api/chat.ts, api/client.ts, api/instrumentos.ts,
    features/auth/AuthContext.tsx, features/kpis/GraficasKpi.tsx,
    features/research/ArmarInvestigacionPage.tsx, routeTree.gen.ts, routes/login.tsx}`
    → `git checkout --` (fuera de alcance).
- **Scratch / throwaway (bajo `.agents/tasks/chroma-viz/`):** `scratch/seed_kpis.sql`,
  `scratch/seed_instrumentos.sql`, `scratch/post_propuestas.ps1`, `scratch/post_propuestas_result.txt`,
  `scratch/viewer/{Dockerfile,app.py,requirements.txt}`, `scratch/build.log`, `id_map.json`.
- **Datos copiados:** `storage/raw/inst_01..21.md` y `storage/raw/inst_01..21.v1.json`.

## Restricción respetada

Tras la iteración de corrección, el único archivo versionado modificado es `docker-compose.yml`.
No queda ningún cambio bajo `services/*` ni `infrastructure/docker/Dockerfile.*` en el working
tree (ambos revertidos). El visor vive por completo en el scratch del task. El commit final
(en un paso posterior) incluirá únicamente `docker-compose.yml`.

Verificación del estado final:
```
git status --porcelain --untracked-files=no
# ->  M docker-compose.yml   (único)
curl.exe -s .../collections/<kpis>/count               # -> 30
curl.exe -s .../collections/<summary_instrument>/count # -> 21
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8085/   # -> 200
```
