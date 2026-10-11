# Proxy del analysis-service por el api-gateway (/vectorizacion, /kpis, /grafo)

El gateway (`:8000`, mismo origen que el login) ahora proxea los tres prefijos del analysis-service que el frontend consumía directo contra `:8002`, eliminando el `Failed to fetch` del paso de KPIs sugeridos del wizard. Se añaden seis handlers (GET/POST por prefijo, cada uno con ruta base + `{path:path}`) replicando el patrón de `/instrumentos` y `/api/metadata`, y el frontend (`carga.ts`, `espacio.ts`, `grafo.ts`, `kpis.ts`) reemplaza `ANALYSIS_URL` por `API_URL` en todas las llamadas afectadas. El multipart de `/vectorizacion/propuestas` pasa por el mismo `proxy_request` sin tratamiento especial. Watch for: el diff incluye un cambio no relacionado en `Dockerfile.analysis-service` (fix torch CPU-only) **(confirmed)** que no forma parte del alcance de esta tarea pero no es bloqueante.

**Verdict**: APPROVED

## High-level view

El proxy añade los tres prefijos reusando literalmente la mecánica existente: `_ruta_upstream(prefijo, path)` reconstruye el path sin barra final extra, y las dos rutas por método (base y `{path:path}`) evitan el redirect 307 de FastAPI. No se tocó `proxy_request`, así que el passthrough de status/body y la conservación de headers son idénticos al resto del gateway.

El multipart de `/vectorizacion/propuestas` funciona porque `_HEADERS_A_QUITAR` solo elimina `host` y `content-length`: el `Content-Type` con su `boundary` llega intacto al upstream junto con los bytes crudos del cuerpo. La evidencia de verificación muestra el POST multipart por `:8000` devolviendo HTTP 200 con cinco propuestas, idéntico al `:8002` directo, y dos GET JSON (catálogo y grafo/acervo) también en 200.

En el frontend los reemplazos `ANALYSIS_URL`→`API_URL` son exactos y completos: no queda ninguna referencia viva fuera de la definición en `client.ts`, que se conserva marcada `@deprecated`. Se preservaron los `auth: false` y el fetch multipart sigue sin Authorization. Los comentarios que afirmaban que el gateway no proxeaba estos prefijos quedaron actualizados.

El único punto fuera de alcance es un cambio en `Dockerfile.analysis-service` (instalación de torch desde el índice CPU de PyTorch) empaquetado en el mismo working tree. No afecta al proxy ni al frontend y no rompe nada, pero no pertenece a esta tarea.

<details>
<summary>Issues (1)</summary>

1. **Cambio no relacionado empaquetado** *(confirmed, no bloqueante)* — `infrastructure/docker/Dockerfile.analysis-service` trae el fix de torch CPU-only, ajeno al proxy del gateway. Conviene separarlo en su propio commit cuando se versione, pero no bloquea esta revisión.

</details>

<details>
<summary>Details</summary>

### Los tres prefijos replican el patrón de /instrumentos

Cada prefijo declara dos rutas por verbo —la base (`/vectorizacion`) y la de sub-path (`/vectorizacion/{path:path}`)— apuntando al mismo handler, exactamente como `/instrumentos` y `/api/metadata`. Los handlers llaman `proxy_request("analysis", _ruta_upstream("/<prefijo>", path), request, "<METODO>")` con el prefijo correcto en cada caso: `/vectorizacion`, `/kpis` y `/grafo` con GET y POST. El montaje sin prefijo en `main.py` deja estas rutas accesibles en `http://localhost:8000/<prefijo>/...`, cubriendo las llamadas del frontend (`/vectorizacion/propuestas`, `/vectorizacion/confirmar`, `/vectorizacion/espacio`, `/vectorizacion/kpis/catalogo`, `/kpis/calculo/*`, `/grafo/acervo`, `/grafo/recomendar`, `/grafo/investigacion`).

`_ruta_upstream` devuelve `prefijo` cuando `path` está vacío y `prefijo/path` en otro caso, por lo que el upstream recibe el path exacto sin `/` final espurio y sin reescritura.

### Multipart preservado sin tocar proxy_request

`/vectorizacion/propuestas` recibe `multipart/form-data` y pasa por el mismo `proxy_request` que el resto. Como `_HEADERS_A_QUITAR` solo descarta `host` y `content-length`, el `Content-Type: multipart/form-data; boundary=...` del request original se reenvía intacto, y el cuerpo va como bytes crudos (`content=body`), de modo que el `boundary` sigue casando con el cuerpo. La misma ruta cubre los endpoints JSON (`/vectorizacion/confirmar`, `/kpis/calculo/*`) sin ramas condicionales: el mismo mecanismo sirve para multipart y JSON porque ninguno de los dos recomputa ni reescribe el `Content-Type`.

La evidencia en `verificacion.md` registra el curl multipart por `http://localhost:8000/vectorizacion/propuestas` devolviendo **HTTP 200** con `propuestas` de cinco KPIs (kpi_id 19, 1, 51, 37, 8), más dos GET por el gateway (`/vectorizacion/kpis/catalogo` 200, 57456 bytes; `/grafo/acervo` 200, 357 bytes). Esto confirma que el boundary sobrevive al proxy y que el passthrough no rompió los endpoints no-multipart.

### Reemplazos ANALYSIS_URL→API_URL completos

Los cinco puntos de `carga.ts` (`proponerKpis` fetch multipart, `confirmarKpis`, `prepararCalculo`, `registrarCalculo`, `getCalculosInstrumento`), el de `espacio.ts`, los tres de `grafo.ts` y el de `kpis.ts` apuntan ahora a `API_URL`. Los imports se limpiaron en consecuencia (`carga.ts` a `{ API_URL, leerToken, pedir }`, los demás eliminando `ANALYSIS_URL`). Un `git grep ANALYSIS_URL` sobre `pixel-perfect-pixel/src` devuelve una sola línea: la definición en `client.ts`, ya marcada `@deprecated` apuntando a usar `API_URL`. No queda ninguna llamada residual.

Los `auth: false` se conservan en todas las llamadas que ya los tenían, y el fetch multipart de `proponerKpis` sigue sin cabecera `Authorization` (solo cambió el host). Los comentarios/JSDoc que afirmaban "el gateway NO proxea /vectorizacion/* (o /grafo/*)" quedaron corregidos en los cuatro archivos y en el bloque "Note: calls go through API_URL..." de `carga.ts`, y el docstring de cabecera de `proxy.py` suma los tres prefijos a la lista de passthrough y rectifica la frase que decía que el analysis-service se consumía directo.

### Cambio no relacionado: Dockerfile.analysis-service

El working tree incluye una modificación en `infrastructure/docker/Dockerfile.analysis-service` que instala `torch==2.2.2` desde el índice CPU de PyTorch antes del resto de requirements, para evitar arrastrar los wheels CUDA. Es el fix de CUDA de la conversación previa, ajeno al alcance de proxear el analysis-service. No afecta al código del proxy ni del frontend y no introduce riesgo para esta tarea; solo conviene aislarlo en su propio commit cuando se versione.

### Cobertura de pruebas

Verificado por evidencia en `verificacion.md`: sintaxis Python del proxy (ast.parse OK), build y recreación del contenedor (`Up (healthy)`, `/health` 200), el curl multipart crítico por el gateway (200 con cinco propuestas) y dos GET JSON por el gateway (200). El typecheck del frontend (`bunx tsc --noEmit`) reporta 13 errores preexistentes confirmados contra el baseline con `git stash`; los cambios de este diff no añaden errores nuevos. No tratado: no hay prueba de los POST JSON `/vectorizacion/confirmar` ni `/kpis/calculo/*` ni de `/grafo/recomendar`/`/grafo/investigacion` por el gateway, pero comparten el mismo handler y mecanismo que las rutas ya verificadas, por lo que el riesgo residual es bajo.

</details>

<details>
<summary>File map</summary>

- `services/api-gateway/proxy/proxy.py` — seis handlers nuevos (GET/POST × 3 prefijos) hacia `analysis`; docstring de cabecera actualizado.
- `pixel-perfect-pixel/src/api/carga.ts` — cinco llamadas de KPIs/vectorización a `API_URL`; import y comentarios actualizados.
- `pixel-perfect-pixel/src/api/espacio.ts` — `/vectorizacion/espacio` a `API_URL`; import y JSDoc.
- `pixel-perfect-pixel/src/api/grafo.ts` — tres llamadas de grafo a `API_URL`; import y comentario de cabecera.
- `pixel-perfect-pixel/src/api/kpis.ts` — catálogo a `API_URL`; import y JSDoc.
- `pixel-perfect-pixel/src/api/client.ts` — `ANALYSIS_URL` marcado `@deprecated` (conservado).
- `infrastructure/docker/Dockerfile.analysis-service` — **no relacionado**: torch CPU-only.

Diff completo: `git diff` en la raíz del repo.

</details>
