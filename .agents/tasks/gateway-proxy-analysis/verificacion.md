# Verificación — Proxear analysis-service por el api-gateway

Primera iteración (no existía `review.json`). Implementación completa según `plan.md`.

## Cambios aplicados

- `services/api-gateway/proxy/proxy.py`: añadidos handlers de proxy hacia el
  service `analysis` para los tres prefijos, replicando el patrón de `/instrumentos`
  y `/api/metadata` (ruta base + `{path:path}`, un handler por método, passthrough
  con `_ruta_upstream`):
  - `/vectorizacion` y `/vectorizacion/{path:path}` → GET, POST
  - `/kpis` y `/kpis/{path:path}` → GET, POST
  - `/grafo` y `/grafo/{path:path}` → GET, POST
  Docstring de cabecera actualizado (los tres prefijos añadidos a "Prefijos
  passthrough" y corregida la frase que decía que analysis-service se consumía
  directo). NO se tocó `proxy_request`: el multipart funcionó a la primera (el
  boundary se preserva porque `_HEADERS_A_QUITAR` solo quita `host`/`content-length`).
- Frontend `pixel-perfect-pixel/src/api/`:
  - `carga.ts`: `ANALYSIS_URL` → `API_URL` en `proponerKpis` (fetch multipart crudo,
    sin Authorization), `confirmarKpis`, `prepararCalculo`, `registrarCalculo`,
    `getCalculosInstrumento`. Import limpiado a `{ API_URL, leerToken, pedir }`.
    Comentarios actualizados. `auth: false` conservado.
  - `espacio.ts`, `grafo.ts`, `kpis.ts`: `ANALYSIS_URL` → `API_URL` en todas las
    llamadas; imports y comentarios actualizados; `auth: false` conservado.
  - `client.ts`: `ANALYSIS_URL` se conserva marcado `@deprecated` (0 referencias
    vivas fuera de su definición).

## Comandos y resultados

1. Sintaxis Python del proxy:
   `python -c "import ast; ast.parse(open('services/api-gateway/proxy/proxy.py',encoding='utf-8').read())"`
   → OK (exit 0).

2. Build de la imagen del gateway:
   `docker compose -f docker-compose.yml build api-gateway`
   → `Image indagata-api-gateway Built`, exit 0.

3. Recreación del contenedor:
   `docker compose -f docker-compose.yml up -d api-gateway`
   → `indagata_api_gateway Started`, estado `Up (healthy)`, `0.0.0.0:8000->8000/tcp`.
   `/health` → 200 (log del healthcheck del contenedor).

4. Multipart crítico por el GATEWAY (prueba del paso 7 del wizard):
   `curl.exe -s -w "...HTTP_STATUS:%{http_code}..." -X POST "http://localhost:8000/vectorizacion/propuestas" -F "archivo_json=@storage/raw/inst_01.v1.json;type=application/json" -F "instrumento_original=@storage/raw/inst_01.md;type=text/markdown" -F "tipo_instrumento=encuesta" -F "id_instrumento=1" --max-time 120`
   → **HTTP_STATUS:200**, JSON con `"propuestas":[...]` de **5 KPIs** (kpi_id 19, 1, 51,
   37, 8; cada uno con `kpi_id`, `nombre`, `score`). Boundary multipart preservado.

5. GETs por el gateway:
   - `curl.exe ... "http://localhost:8000/vectorizacion/kpis/catalogo"` → **HTTP 200**,
     57456 bytes (lista del catálogo).
   - `curl.exe ... "http://localhost:8000/grafo/acervo"` → **HTTP 200**, 357 bytes
     (`{nodos, aristas}`).

6. Typecheck del frontend: `bunx tsc --noEmit` reporta 13 errores PREEXISTENTES
   (index-signature strictness en chat.ts/client.ts/UploadWizard.tsx/StepTiposPregunta.tsx
   y acceso a `import.meta.env.VITE_*`), NO relacionados con este cambio. Verificado
   con `git stash` + `tsc` sobre el baseline: produce exactamente los mismos 13 errores.
   Mis ediciones (`ANALYSIS_URL` → `API_URL`) no añaden ningún error nuevo.
   El build real del proyecto es `vite build` (no `tsc`); no hay script `typecheck`.
   `grep ANALYSIS_URL` en `src/`: 0 referencias vivas fuera de la definición en `client.ts`.

## Notas

- NO se hizo git add/commit/push: los cambios quedan solo en el working tree.
- No se tocó la UI ni los componentes del wizard, ni el `.env` del frontend, ni otros
  servicios/contenedores.
