# Implementation Plan — Proxear analysis-service por el api-gateway

## Objetivo

Eliminar el error `Failed to fetch` del navegador en el paso 7 del wizard de carga
("KPIs sugeridos"). Causa raíz verificada: el navegador no alcanza directamente
`http://localhost:8002` (analysis-service), aunque el backend responde HTTP 200 desde
la misma máquina. Solución acordada: el api-gateway (`:8000`, mismo origen que el login
que SÍ funciona) proxea TODAS las rutas del analysis-service que el frontend usa, y el
frontend deja de llamar directo a `:8002`.

Rama de trabajo: `elotro-back` (checkout principal). **NO hacer git commit ni git push**;
dejar los cambios solo en el working tree.

## Hallazgos de exploración (base del plan, ya verificados)

- El proxy del gateway vive en `services/api-gateway/proxy/proxy.py` y se monta SIN
  prefijo: `main.py` hace `app.include_router(proxy_router)`. Por eso un decorador
  `@router.post("/vectorizacion/...")` queda accesible en `http://localhost:8000/vectorizacion/...`.
- Patrón de proxy existente (a replicar EXACTO): diccionario `SERVICES` ya tiene
  `"analysis": os.getenv("ANALYSIS_SERVICE_URL", "http://analysis-service:8002")`.
  `proxy_request(service, path, request, method)` reenvía status+body transparente.
  `_ruta_upstream(prefijo, path)` reconstruye el path sin barra final extra. Cada prefijo
  declara DOS rutas por método: la base (`/instrumentos`) y la de sub-path
  (`/instrumentos/{path:path}`), para evitar el redirect 307 de FastAPI.
- `_HEADERS_A_QUITAR = {"host", "content-length"}`. `proxy_request` lee
  `body = await request.body()` (bytes crudos) y reenvía con `content=body` y los headers
  originales (conserva `Content-Type`, por lo que el `boundary` del multipart se preserva;
  conserva `Authorization`). Esto cubre tanto multipart como JSON sin cambios.
- `docker-compose.yml`: servicio del gateway = `api-gateway` (container `indagata_api_gateway`),
  publica `8000:8000`, y ya inyecta `ANALYSIS_SERVICE_URL: http://analysis-service:8002`.
  El volumen `./services/api-gateway:/app` monta el código: con `--build`/recreate el cambio
  en `proxy.py` queda dentro del contenedor.
- Frontend (`pixel-perfect-pixel/src/api/`): `client.ts` define `API_URL` (`:8000`) y
  `ANALYSIS_URL` (`:8002`). Llamadas a reemplazar `ANALYSIS_URL` → `API_URL`:
  - `carga.ts`: `fetch(.../vectorizacion/propuestas)` (fetch crudo multipart, NO el helper
    `pedir`); `pedir(.../vectorizacion/confirmar)`; `pedir(.../kpis/calculo/preparar)`;
    `pedir(.../kpis/calculo/registrar)`; `pedir(.../kpis/calculo/${id_instrumento})`.
  - `espacio.ts`: `pedir(.../vectorizacion/espacio)`.
  - `grafo.ts`: `pedir(.../grafo/acervo)`, `pedir(.../grafo/recomendar)`, `pedir(.../grafo/investigacion)`.
  - `kpis.ts`: `pedir(.../vectorizacion/kpis/catalogo)`.
  - Las llamadas con `auth: false` SIGUEN con `auth: false` (dev mode no requiere token;
    el POST por curl funcionó sin Authorization).
- Typecheck del frontend: `tsconfig.json` tiene `noEmit: true`; no hay script `typecheck`
  en `package.json`, así que se usa `npx tsc --noEmit` directo. No modificar la UI (regla
  de `pixel-perfect-pixel/AGENTS.md`): los cambios son solo en `src/api/` y en el gateway.

## Plan

- [ ] 1. Añadir en el proxy del gateway las rutas de proxy hacia el service `analysis`
      para los TRES prefijos, replicando EXACTO el patrón de `/instrumentos` (ruta base +
      `{path:path}` por método, un handler por verbo HTTP usando el `_ruta_upstream`
      correcto, passthrough transparente sin reescribir el path). Añadir, tras el bloque
      de `/api/enrichment`:
        * `/vectorizacion` y `/vectorizacion/{path:path}` → GET y POST, con
          `_ruta_upstream("/vectorizacion", path)`. (Cubre POST `/vectorizacion/propuestas`
          [multipart], POST `/vectorizacion/confirmar` [json], GET `/vectorizacion/espacio`,
          GET `/vectorizacion/kpis/catalogo`, POST `/vectorizacion/kpis/reindex`,
          GET `/vectorizacion/summary/{id}`.)
        * `/kpis` y `/kpis/{path:path}` → GET y POST, con `_ruta_upstream("/kpis", path)`.
          (Cubre POST `/kpis/calculo/preparar`, POST `/kpis/calculo/registrar`,
          GET `/kpis/calculo/{id_instrumento}`.)
        * `/grafo` y `/grafo/{path:path}` → GET y POST, con `_ruta_upstream("/grafo", path)`.
          (Cubre GET `/grafo/acervo`, POST `/grafo/recomendar`, POST `/grafo/investigacion`.)
      Cada handler debe llamar `proxy_request("analysis", _ruta_upstream("/<prefijo>", path), request, "<METODO>")`.
      Multipart: NO añadir manejo especial; `proxy_request` ya reenvía bytes crudos
      conservando el `Content-Type` (y por tanto el `boundary`), porque `_HEADERS_A_QUITAR`
      solo quita `host` y `content-length`. Dejar el passthrough tal cual también sirve
      para los endpoints JSON. (El ajuste al `Content-Type` del paso 5 es solo contingente.)
      Actualizar el docstring de cabecera del módulo: añadir los tres nuevos prefijos a la
      lista "Prefijos passthrough" y corregir la frase que dice que `analysis-service` lo
      consume el frontend de forma directa / no se proxea aquí (ya no es cierto).
      Files: `services/api-gateway/proxy/proxy.py`
      Verify: `python -c "import ast,sys; ast.parse(open(r'services/api-gateway/proxy/proxy.py',encoding='utf-8').read())"` sin error (sintaxis válida). La verificación funcional real se hace en el paso 6.

- [ ] 2. Repuntar `kpis.ts`: cambiar la llamada del catálogo de KPIs de `ANALYSIS_URL` a
      `API_URL`. Reemplazar `pedir<KpiCatalogoDTO[]>(\`${ANALYSIS_URL}/vectorizacion/kpis/catalogo\`, { auth: false })`
      por la misma llamada con `API_URL`. Ajustar el import `{ ANALYSIS_URL, pedir, simularRed }`
      → `{ API_URL, pedir, simularRed }`. Actualizar el comentario del JSDoc de
      `getCatalogoKpis` que afirma "el gateway NO proxea /vectorizacion/*" (ya no es cierto;
      indicar que va por el gateway). Mantener `auth: false` y el fallback a mock.
      Files: `pixel-perfect-pixel/src/api/kpis.ts`
      Verify: paso 7 (typecheck conjunto).

- [ ] 3. Repuntar `espacio.ts`: cambiar `pedir<EspacioVectorial>(\`${ANALYSIS_URL}/vectorizacion/espacio\`, { auth: false })`
      a `API_URL`. Cambiar el import `{ ANALYSIS_URL, pedir }` → `{ API_URL, pedir }`.
      Actualizar el JSDoc que dice "El api-gateway NO proxea /vectorizacion/*" (ahora va por
      el gateway). Mantener `auth: false`.
      Files: `pixel-perfect-pixel/src/api/espacio.ts`
      Verify: paso 7 (typecheck conjunto).

- [ ] 4. Repuntar `grafo.ts`: cambiar las tres llamadas (`/grafo/acervo`, `/grafo/recomendar`,
      `/grafo/investigacion`) de `ANALYSIS_URL` a `API_URL`. Cambiar el import
      `{ ANALYSIS_URL, pedir }` → `{ API_URL, pedir }`. Actualizar el comentario de cabecera
      que afirma "El api-gateway NO proxea /grafo/*" (ahora sí lo proxea). Mantener los tres
      `auth: false`.
      Files: `pixel-perfect-pixel/src/api/grafo.ts`
      Verify: paso 7 (typecheck conjunto).

- [ ] 5. Repuntar `carga.ts`: cambiar a `API_URL` las cinco llamadas que hoy usan
      `ANALYSIS_URL`:
        * `fetch(\`${ANALYSIS_URL}/vectorizacion/propuestas\`...)` (fetch crudo multipart en
          `proponerKpis`; NO convertir a `pedir`; mantener sin Authorization).
        * `pedir(\`${ANALYSIS_URL}/vectorizacion/confirmar\`...)` en `confirmarKpis` (`auth: false`).
        * `pedir(\`${ANALYSIS_URL}/kpis/calculo/preparar\`...)` en `prepararCalculo` (`auth: false`).
        * `pedir(\`${ANALYSIS_URL}/kpis/calculo/registrar\`...)` en `registrarCalculo` (`auth: false`).
        * `pedir(\`${ANALYSIS_URL}/kpis/calculo/${id_instrumento}\`...)` en `getCalculosInstrumento` (`auth: false`).
      El import ya trae `API_URL`; quitar `ANALYSIS_URL` del import `{ ANALYSIS_URL, API_URL, leerToken, pedir }`
      → `{ API_URL, leerToken, pedir }` (las llamadas a `/instrumentos/*` ya usan `API_URL`).
      Actualizar los JSDoc/comentarios que digan que el gateway no proxea `/vectorizacion/*`
      o `/kpis/*` (en `proponerKpis`, `confirmarKpis`, `getKpisSugeridos`, y el bloque del
      paso 5 "Note: calls go through API_URL ... If not proxied yet, call ANALYSIS_URL") para
      reflejar que ahora todo va por el gateway. Mantener los `auth: false` y el multipart.
      Files: `pixel-perfect-pixel/src/api/carga.ts`
      Verify: paso 7 (typecheck conjunto).

- [ ] 6. Marcar `ANALYSIS_URL` como deprecado en `client.ts`. Tras los pasos 2–5 ya no
      queda ninguna referencia a `ANALYSIS_URL` en `src/api/`. Mantener la constante exportada
      para no romper imports externos (si los hubiera) y marcarla con comentario de deprecada:
      cambiar el JSDoc `/** URL base del analysis-service (el api-gateway NO proxea /vectorizacion/*). */`
      por uno que indique "@deprecated: el api-gateway ya proxea analysis-service; usar API_URL".
      Antes de editar, confirmar que no queda ningún uso vivo:
      `grep` de `ANALYSIS_URL` en `pixel-perfect-pixel/src` (excluyendo `client.ts`) debe dar 0
      resultados; si aparece alguno, repuntarlo a `API_URL` como en los pasos 2–5.
      Files: `pixel-perfect-pixel/src/api/client.ts`
      Verify: paso 7 (typecheck conjunto).

- [ ] 7. Typecheck del frontend. Ejecutar desde `pixel-perfect-pixel`:
      `npx tsc --noEmit`
      Resultado esperado: sin errores (exit 0). Si falla por algún `ANALYSIS_URL` huérfano o
      import mal ajustado, corregirlo y re-ejecutar. (El proyecto no tiene script `typecheck`;
      `tsconfig.json` ya tiene `noEmit: true`.)
      Files: ninguno (verificación).
      Verify: `cd pixel-perfect-pixel; npx tsc --noEmit` termina sin errores.

- [ ] 8. Reconstruir/recrear el api-gateway y verificar que arranca. Ejecutar desde la raíz
      del repo:
      `docker compose up -d --build api-gateway`
      Luego comprobar salud: `docker compose ps api-gateway` (estado healthy/running) y
      `curl.exe http://localhost:8000/health` → HTTP 200.
      Files: ninguno (verificación).
      Verify: el contenedor `indagata_api_gateway` queda running y `/health` responde 200.

- [ ] 9. Verificar el proxy multipart de KPIs sugeridos de punta a punta por el gateway.
      Con el analysis-service arriba, replicar la prueba que YA funciona contra `:8002` pero
      ahora contra `:8000`. Desde PowerShell (usar `curl.exe`, no el alias `curl`):
      `curl.exe -i -X POST http://localhost:8000/vectorizacion/propuestas -F "archivo_json=@<ruta>/instrumento.json;type=application/json" -F "instrumento_original=@<ruta>/instrumento.md;type=text/markdown" -F "tipo_instrumento=encuesta" -F "id_instrumento=<id>"`
      Resultado esperado: HTTP 200 con JSON que incluye `propuestas` (los ~5 KPIs), idéntico
      a lo que devolvía el `:8002` directo. Esto confirma que el `boundary` del multipart se
      preserva a través de `proxy_request`.
      Si falla el parseo del boundary (p. ej. 422 "boundary" o cuerpo vacío), aplicar el ajuste
      contingente del paso 1: en `proxy_request`, preservar explícitamente el `Content-Type`
      original en los headers reenviados SIN romper los endpoints JSON, y repetir este curl.
      Files: posiblemente `services/api-gateway/proxy/proxy.py` (solo si el boundary falla).
      Verify: `curl.exe` al gateway devuelve HTTP 200 con `propuestas`.

- [ ] 10. Verificar un endpoint JSON y uno GET por el gateway para confirmar que el passthrough
      no rompió los no-multipart. Desde PowerShell:
      `curl.exe -i http://localhost:8000/vectorizacion/kpis/catalogo` → HTTP 200 con el array del catálogo.
      `curl.exe -i http://localhost:8000/grafo/acervo` → HTTP 200 con `{nodos, aristas}`.
      Resultado esperado: ambos 200 con el JSON de dominio esperado (status y cuerpo del
      upstream transparentes).
      Files: ninguno (verificación).
      Verify: ambos `curl.exe` devuelven HTTP 200 con el JSON correcto.

## Notas y supuestos

- El fetch multipart de `proponerKpis` NO manda Authorization hoy y al pasar por el gateway
  sigue sin necesitarlo (dev mode; el POST por curl funcionó sin token). Las llamadas con
  `auth: false` SIGUEN con `auth: false` — no se añade auth en ningún paso.
- No se toca la UI ni los tipos de dominio; solo `src/api/*` y el proxy del gateway, conforme
  a `pixel-perfect-pixel/AGENTS.md` (acceso a datos solo por `src/api/`).
- Supuesto para los pasos 9–10: el analysis-service está levantado y hay al menos un
  `id_instrumento` válido con su `instrumento.json` / `instrumento.md` para la prueba
  multipart (los mismos insumos con los que ya se validó el `:8002`). Si no se dispone de
  esos archivos de muestra, el paso 10 (GET catálogo/acervo) basta para confirmar el proxy;
  el 9 se valida en cuanto haya un instrumento cargado desde el wizard.
- `ANALYSIS_URL` se deja definido (deprecado) en `client.ts` por seguridad de imports; si una
  verificación posterior confirma 0 referencias en todo el repo, puede eliminarse, pero no es
  requisito para cerrar la tarea.
