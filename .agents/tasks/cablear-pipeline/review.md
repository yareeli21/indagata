# Cablear pasos 1-4 del asistente de carga al backend real (iteración 2)

El commit `885cb4c` conecta los pasos 1-4 del `UploadWizard` (subir → limpieza → metadatos Dublin Core → asociación de KPIs) a los microservicios reales: `subirInstrumento` contra `/instrumentos/upload`, metadatos vía el proxy del gateway `/api/metadata/*`, y propuestas/confirmación directo a `ANALYSIS_URL/vectorizacion/*`. En backend añade el proxy passthrough de `metadata-service` en el api-gateway y reconcilia `dc_manager.py` con los modelos reales (bug bloqueante de la línea base). Las firmas exportadas de `src/api/*` se conservan; los flujos sin fuente real quedan mock con TODO explícito; no se inventan endpoints. Todo vive en el worktree `cablear-pipeline`; el checkout principal (`pruebas`) queda intacto.

Watch for: nada bloqueante. Un detalle cosmético menor (nombre de ícono Lucide inexistente en el fallback del catálogo) y el recorte honesto del paso de KPIs en el flujo de upload puro, ambos documentados y sin romper tipos ni UI (confirmed).

**Verdict**: APPROVED

## High-level view

El cableado respeta exactamente los contratos pactados. El upload va por `fetch`+`FormData`+Bearer porque `pedir()` fuerza `Content-Type: application/json` y no sirve para multipart; los campos (`archivo`, `tipo_instrumento`, `archivo_original`) y la respuesta (`UploadResponse` con ambos ids + `archivo_respondido.parseo`) coinciden con el router y el schema del instrument-service. Los dos ids se propagan por separado como manda el diseño: `id_crudo` para listados y `id_instrumento` para metadatos/KPIs.

El proxy nuevo del gateway (`/api/metadata/*`, `/api/enrichment/*`) es una copia fiel del patrón `/instrumentos/*`: ruta base + `{path:path}` para evitar el 307, `proxy_request` que devuelve status+body del upstream sin envoltorio, y `_headers_reenvio` que conserva `Authorization`. El path se reenvía tal cual, así que el doble segmento real (`/api/metadata/metadata/{id}/init`) se preserva de punta a punta, y el frontend lo construye con ese doble segmento a propósito.

Las propuestas/confirmación de KPIs van directo a `ANALYSIS_URL` (el gateway no proxea `/vectorizacion/*`), sin Authorization (modo dev del analysis-service), con los nombres de campo del router (`archivo_json`, `instrumento_original`, `tipo_instrumento`, `id_instrumento`) y el payload JSON de `ConfirmarRequest`. Los mapeos `parseo→ReporteLimpieza` y `propuesta→KpiSugerido` producen exactamente las formas que consume la UI.

La reconciliación de `dc_manager.py` corrige un bug que, según el plan verificado, hacía fallar init/register/get/delete con 500 contra el esquema real: filtra `InstrumentoProcesado` por `id_instrumento`, resuelve tipo/nombre vía join a `RawData` por `id_crudo`, identifica `MetadatosDC` por su PK real `id_crudo`, usa `ruta_json`/`ruta_de_archivo_limpio` y corrige el valor de estado al `'metadatos_registrados'` que exige el CHECK. Todos los atributos usados existen en los modelos `shared`; los viejos (`instrumento_id`, `.nombre`, `.ruta_archivo`, `.tipo_instrumento` en `InstrumentoProcesado`) no existían.

Las funciones sin fuente real quedan mock con TODO que nombra el endpoint faltante: `getKpis`/`getNoticias`/`getDatosGrafica` (tablero), `limpiarArchivo`/`getKpisSugeridos` (reemplazadas por `subirInstrumento`/`proponerKpis`), y `getCatalogoKpis` degrada a mock si la unión viene vacía. Ningún endpoint inventado.

<details>
<summary>Issues (2)</summary>

1. **Ícono de catálogo inexistente** — `getCatalogoKpis` usa `icono: "ChartBar"` para los KPIs reales; Lucide no exporta `ChartBar` (es `BarChart`/`BarChart3`). Cosmético, no rompe tipos; conviene corregir el nombre del ícono. No bloqueante.
2. **KPIs end-to-end solo con artefactos sembrados** — en el flujo de upload puro no hay JSON enriquecido, así que `proponerKpis` queda sin fuente y el paso cae a `sugeridos = []`. Es un recorte honesto documentado con TODO (no hay endpoint que devuelva el JSON tras el upload); no bloqueante, pero limita la demo end-to-end a la ruta sembrada.

</details>

<details>
<summary>Details</summary>

### Upload: multipart por `fetch`, ambos ids propagados

`subirInstrumento` usa `fetch`+`FormData` con `Authorization: Bearer` manual, correcto porque `pedir()` del `client.ts` fija `Content-Type: application/json` y rompería el multipart. Los campos del `FormData` (`archivo`, `tipo_instrumento` mapeado por `TIPO_UI_A_BACKEND`, `archivo_original` opcional) coinciden con `upload_instrumento` del instrument-service, que es role-gated (requiere Bearer). La respuesta se tipa como `UploadResponse` y devuelve `idCrudo`/`idInstrumento` por separado más el reporte derivado del `parseo`, exactamente como pide la regla de IDs del plan. El mapeo de errores a español por status (401/403/4xx) sigue §2.5. El `UploadResponse` TS y `ParseoArchivo` reflejan el schema Pydantic real.

### Proxy de metadata/enrichment: réplica del patrón transparente

Las seis rutas nuevas (`get/post/delete` × metadata/enrichment) replican el patrón de `/instrumentos/*` sin desviarse: ruta base explícita + `{path:path}` para no disparar el redirect 307, `_ruta_upstream` para reconstruir el path sin barra final forzada, y `proxy_request`, que reenvía con `_headers_reenvio` (conserva `Authorization`, quita `host`/`content-length`) y devuelve `Response(content, status_code, media_type)` del upstream sin envoltorio. El path viaja tal cual, por lo que el doble segmento (`/api/metadata/metadata/{id}/init`) se preserva; el cliente lo construye con el doble `metadata` adrede y lo comenta para que no se "corrija". El docstring del módulo y de `main.py` se actualizaron para reflejar que metadata ya se proxea.

### KPIs: directo a analysis-service, mapeos de forma preservada

`proponerKpis` va a `ANALYSIS_URL/vectorizacion/propuestas` por `fetch`+`FormData` sin Authorization (el analysis-service resuelve `UsuarioActual` en modo dev; mismo patrón que `espacio.ts`); los campos (`archivo_json`, `instrumento_original`, `tipo_instrumento`, `id_instrumento`) y los Blobs con `type` explícito coinciden con `proponer_kpis`. El mapeo `PropuestaKPI → KpiSugerido` produce `{id: String(kpi_id), nombre: nombre_kpi, coincidencia: Math.round(score*100)}`, que es la forma de 3 campos que consume `StepKpis`. `confirmarKpis` manda el JSON de `ConfirmarRequest` (`id_instrumento`, `decisiones[{kpi_id,aceptado,score}]`, `json_instrumento`) y mapea la salida (`kpi_id→kpiId`, `nombre_kpi→nombreKpi`, `json_enriquecido→jsonEnriquecido`). La construcción de `decisiones` en el wizard (`kpiId: Number(k.id)`, `score: k.coincidencia/100`) revierte correctamente el mapeo de ida.

### Reconciliación de `dc_manager.py` con el esquema real

El plan documenta que la versión base del `dc_manager` usaba atributos inexistentes y filtraba por claves equivocadas, haciendo fallar init/register/get/delete con 500. La corrección, verificada contra los modelos `shared`: `InstrumentoProcesado` se filtra por `id_instrumento` (PK real), tipo/nombre se obtienen por join a `RawData` por `id_crudo` (`tipo_instrumento`, `nombre_archivo`), `MetadatosDC` se identifica por su PK `id_crudo`, el formato se deriva de `ruta_json`/`ruta_de_archivo_limpio`, y el estado se fija en `'metadatos_registrados'` (plural), único valor del CHECK `ck_instrumento_estado`. Se eliminó la asignación a `instrumento.nombre` (atributo inexistente). La inmutabilidad (2.º POST → 409) y el contrato HTTP se conservan. El listado cambia la clave `instrumento_id` por `id_crudo` en su salida, pero esa respuesta no la consume ninguno de los mapeos de UI de esta tarea, así que no rompe forma.

### Recortes honestos y firmas estables

`limpiarArchivo` y `getKpisSugeridos` conservan su firma pero devuelven valores honestos (reporte en ceros / `[]`) porque sus reemplazos reales son `subirInstrumento` y `proponerKpis`; el wizard ya no los invoca. `guardarInstrumento` conserva firma y ahora devuelve el id real si el documento lo trae. `getKpis`/`getNoticias`/`getDatosGrafica` quedan mock con TODO nombrando el endpoint faltante. `getCatalogoKpis` consume `/instrumentos/kpis/catalogo` (list[str]) y degrada a mock ante respuesta vacía o fallo de red; su único defecto es cosmético (`icono: "ChartBar"`, inexistente en Lucide). Las siete firmas exportadas listadas en el plan se mantienen sin cambios.

### Alcance y confinamiento

El commit toca solo los seis archivos de código esperados (`carga.ts`, `kpis.ts`, `UploadWizard.tsx`, `api-gateway/main.py`, `proxy.py`, `dc_manager.py`) más los docs de tarea. No hay rediseño de UI, estilos ni estructura de pasos; `puedeContinuar` queda intacto (incluido que `dc_subject` no es obligatorio). Toda la interfaz, rutas y comentarios siguen en español. El checkout principal está en `pruebas` (`d56c840`), sin tocar; el trabajo vive solo en la rama `cablear-pipeline` del worktree.

### Nota sobre verificación

No se re-ejecutaron build ni suites; se tomó la evidencia registrada en `plan.md` (build de 3 fases `✓ built`, `tsc` solo con 6 errores preexistentes en `client.ts`/`chat.ts` no tocados, smokes TestClient en memoria OK para `dc_manager` y las rutas del gateway). Los contratos backend se verificaron por lectura directa de los schemas/routers/modelos reales, que concuerdan con el cableado. La verificación de integración end-to-end con Docker queda, por diseño, para el step de runtime.

</details>

<details>
<summary>Mapa de archivos</summary>

- `pixel-perfect-pixel/src/api/carga.ts` — upload multipart, `mapearParseoALimpieza`, metadatos init/registro vía gateway, propuestas/confirmación de KPIs; stubs de compatibilidad.
- `pixel-perfect-pixel/src/api/kpis.ts` — `getCatalogoKpis` real con fallback a mock; TODOs en las funciones de tablero.
- `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx` — encadena ids/archivos y llamadas reales por los pasos; carga en 0→1, registro de metadatos en 2→3, confirmación al guardar.
- `services/api-gateway/proxy/proxy.py` — proxy passthrough `/api/metadata/*` y `/api/enrichment/*`.
- `services/api-gateway/main.py` — docstring del módulo actualizado.
- `services/metadata-service/services/dc_manager.py` — reconciliación con los modelos reales (id_instrumento/id_crudo, join a RawData, estado del CHECK).

Diff completo: `git show 885cb4c` en el worktree `cablear-pipeline`.

</details>
