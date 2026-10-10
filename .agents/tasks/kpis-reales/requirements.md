# Requisitos — Integración de KPIs reales (kpis-reales)

## Resumen

Hoy el catálogo de KPIs de Indagata está sembrado con ~30 KPIs de ejemplo (en un seed deshabilitado, `infrastructure/postgres/init/_disabled/04_seed.sql`, cuyas columnas ni siquiera coinciden con el esquema vigente) y la pantalla de KPIs del frontend se alimenta de un endpoint que devuelve solo **nombres** (`GET /instrumentos/kpis/catalogo` → `list[str]`, derivado de `design_reference.kpi_hints` de los instrumentos, no de la tabla `tt_rag.kpi`). El usuario ya cuenta con los 55 KPIs reales en un CSV y pidió: (1) rehacer la tabla `tt_rag.kpi` con esos KPIs, (2) re-apuntar la indexación vectorial de KPIs a una nueva estrategia de embedding, (3) exponer un catálogo real estructurado y (4) cablear la pantalla de KPIs para que muestre los datos reales (nombre + significado).

Esta tarea toca cinco capas: **esquema de BD + re-seed**, **modelo ORM**, **indexación vectorial (Chroma)**, **endpoint de catálogo** y **frontend**. Todo el texto de cara al usuario, las rutas y los identificadores de dominio se mantienen en español. El re-seed destructivo de `tt_rag.kpi` (reemplazar los KPIs viejos por los 55 nuevos) está **explícitamente autorizado** por el usuario.

### Datos de entrada (verificados)

Fuente única de verdad: `infrastructure/postgres/seed/kpis_ampliados.csv`.

Re-lectura con `csv.DictReader` (encoding `utf-8-sig`) confirmada:
- **55 filas de datos** (más la cabecera).
- **8 columnas**, en este orden exacto:
  1. `KPI` (nombre)
  2. `Polaridad_Rendimiento`
  3. `Tipo_Objetivo_Estrategico`
  4. `Formula_Metrica_Calculo`
  5. `Descripcion_Ampliada_Educativa` (el "significado" que se muestra en la UI)
  6. `Comportamiento_Direccional_y_Causalidad`
  7. `Razon_Estrategica_y_Decisiones`
  8. `Texto_Contexto_RAG_Vectorial` (ÚLTIMA columna — el texto que se embebe)
- **55 nombres de KPI únicos** (sin duplicados).
- **0 filas con `Texto_Contexto_RAG_Vectorial` vacío**.

> Nota de ubicación (para la fase de diseño/implementación, no es un requisito funcional en sí): al momento de redactar estos requisitos el CSV existe en el árbol principal del repositorio (`infrastructure/postgres/seed/kpis_ampliados.csv`) y **todavía no está copiado dentro del worktree** `.worktrees/kpis-reales`. La implementación debe garantizar que el CSV quede versionado dentro del worktree bajo esa misma ruta antes de que el pipeline de seed lo consuma. No debe hardcodearse el conteo de 55: cualquier script de carga debe re-contar las filas del CSV al ejecutarse.

### Estrategia de embedding (DECIDIDA)

Para cada KPI se **embebe ÚNICAMENTE** la última columna `Texto_Contexto_RAG_Vectorial`, que es un párrafo autocontenido escrito a propósito para vectorización. **No** se concatenan las demás columnas en el texto embebido. Las **otras columnas son METADATOS**: viven en Postgres (fuente de verdad) y se adjuntan al punto de Chroma como metadata escalar (no se vectorizan). Se conserva distancia **coseno** + embeddings **normalizados** con el **mismo modelo** (`settings.EMBEDDING_MODEL`, 768 dimensiones), para que los vectores de KPI sigan siendo comparables con los de `summary_instrument`.

### Mapeo al frontend (DECIDIDO — Opción B, mapear más campos del CSV)

El objeto `KpiCatalogo` del frontend (`pixel-perfect-pixel/src/types/index.ts`) se puebla así:
- `id` ← `str(kpi_id)`
- `nombre` ← `KPI`
- `descripcionCorta` ← `Descripcion_Ampliada_Educativa`
- `queEs` ← `Descripcion_Ampliada_Educativa`
- `queMide` ← `Comportamiento_Direccional_y_Causalidad`
- `comoSeMide` ← `Formula_Metrica_Calculo`
- `formula` ← `Formula_Metrica_Calculo`
- `infoGeneral` ← `Razon_Estrategica_y_Decisiones`
- `etiquetas` ← derivadas de `Polaridad_Rendimiento` + `Tipo_Objetivo_Estrategico` (pocas etiquetas cortas)
- `icono` ← ícono de Lucide elegido por una heurística pequeña sobre el nombre del KPI, con fallback a un ícono **ya mapeado**.

## Requisitos funcionales

### Capa 1 — Esquema de BD + re-seed (`tt_rag.kpi`)

- FR-1.1 La tabla `tt_rag.kpi` debe conservar `kpi_id SERIAL PRIMARY KEY`. Las claves foráneas que la referencian (`kpi_variable`, `kpi_inferido`, `valor_variable_inferido`, `kpi_inferido_chunk`) deben seguir siendo válidas tras el cambio.
- FR-1.2 El esquema de columnas de `tt_rag.kpi` debe representar los campos del CSV necesarios como fuente de verdad en Postgres. Como mínimo debe almacenar: nombre del KPI, el texto de significado educativo (`Descripcion_Ampliada_Educativa`), la fórmula/método de cálculo (`Formula_Metrica_Calculo`), el comportamiento direccional/causalidad (`Comportamiento_Direccional_y_Causalidad`), la razón estratégica (`Razon_Estrategica_y_Decisiones`), la polaridad (`Polaridad_Rendimiento`), el tipo de objetivo estratégico (`Tipo_Objetivo_Estrategico`) y el texto de contexto RAG a vectorizar (`Texto_Contexto_RAG_Vectorial`). La fase de diseño decide el mapeo exacto columna CSV → columna SQL y si se reutilizan/renombran las columnas actuales (`nombre_kpi, descripcion, categoria, ambito, url_documentacion, formula`); los nombres SQL finales se mantienen en español.
- FR-1.3 El re-seed debe **reemplazar** los KPIs viejos por los 55 nuevos (operación destructiva autorizada). Debe dejar exactamente los 55 KPIs del CSV, sin residuos del catálogo anterior.
- FR-1.4 El re-seed se alimenta del CSV (`kpis_ampliados.csv`) como única fuente de verdad; no debe duplicar los datos de los KPIs embebidos en SQL a mano con texto divergente del CSV.
- FR-1.5 El reseteo del contador de identidad de `kpi_id` debe dejar los IDs en un rango determinista y contiguo (p. ej. 1..55) para que la indexación y el frontend puedan mapear por `str(kpi_id)` de forma estable.

### Capa 2 — Modelo ORM (`shared/models/kpi.py`)

- FR-2.1 El modelo `KPI` debe reflejar exactamente las columnas finales de `tt_rag.kpi` tras FR-1.2 (mismos nombres, nullability y tipos), conservando `kpi_id` como PK autoincremental.
- FR-2.2 Todo consumidor existente del modelo que lea campos que cambien de nombre o desaparezcan (`kpi_indexer.build_kpi_text`, los schemas de propuestas que exponen `categoria`/`ambito`, el chroma-viewer que lee `nombre_kpi`) debe actualizarse para seguir compilando y funcionando. En particular `nombre_kpi` es leído por `kpi_indexer` y por `infrastructure/chroma-viewer/app.py`.

### Capa 3 — Indexación vectorial (`analysis-service`, colección Chroma `kpis`)

- FR-3.1 `build_kpi_text` (o su reemplazo) debe devolver **solo** el valor de `Texto_Contexto_RAG_Vectorial` del KPI. No debe concatenar nombre, significado, polaridad ni ningún otro campo en el texto a embeber.
- FR-3.2 La metadata del punto en Chroma debe incluir, como escalares, al menos: `kpi_id`, `nombre_kpi` (nombre del KPI) y los campos de metadato del CSV que el diseño decida exponer (polaridad, tipo de objetivo, fórmula, etc.). No se adjunta `Texto_Contexto_RAG_Vectorial` como metadato redundante salvo que el diseño lo justifique; sí es el `document`/texto embebido.
- FR-3.3 El `id` de cada punto en Chroma sigue siendo `str(kpi_id)` para poder mapear de vuelta a la BD tras una búsqueda semántica.
- FR-3.4 Se conserva el modelo de embeddings (`settings.EMBEDDING_MODEL`, 768-dim), con `normalize_embeddings=True` y distancia coseno (`hnsw:space: cosine`) en la colección `kpis`.
- FR-3.5 La reindexación debe eliminar los puntos obsoletos del catálogo anterior de la colección `kpis` antes de (o como parte de) reinsertar los 55 nuevos, de modo que no queden vectores huérfanos de KPIs que ya no existen. (El `upsert` actual no borra puntos previos; esto debe resolverse explícitamente en el diseño.)
- FR-3.6 El endpoint `POST /vectorizacion/kpis/reindex` debe devolver `n_kpis = 55` tras un reseed+reindex correcto, y la colección `kpis` debe contener exactamente 55 puntos.

### Capa 4 — Endpoint de catálogo real de KPIs

- FR-4.1 Debe existir un endpoint que devuelva el catálogo **estructurado** de los 55 KPIs leídos de `tt_rag.kpi` (no solo nombres, y no derivado de `kpi_hints` de instrumentos). La respuesta debe traer, por KPI, los campos necesarios para poblar `KpiCatalogo` del frontend según el mapeo de la sección "Mapeo al frontend".
- FR-4.2 El endpoint debe ser alcanzable por el frontend a través de la vía ya establecida (el gateway proxea `/instrumentos/*` al `instrument-service`; `analysis-service` lo consume el frontend de forma directa). El diseño elige en qué servicio vive y bajo qué ruta en español, de forma coherente con los patrones existentes y sin romper el contrato del endpoint actual `GET /instrumentos/kpis/catalogo` si otros consumidores dependen de él.
- FR-4.3 La respuesta debe estar ordenada de forma determinista (p. ej. por `kpi_id`).
- FR-4.4 El endpoint devuelve exactamente 55 KPIs cuando la BD está sembrada con el CSV.

### Capa 5 — Frontend (pantalla de KPIs)

- FR-5.1 `getCatalogoKpis` (`pixel-perfect-pixel/src/api/kpis.ts`) debe consumir el endpoint de catálogo real estructurado y mapear la respuesta a `KpiCatalogo[]` según la sección "Mapeo al frontend", en lugar del mapeo actual `list[str] → KpiCatalogo` con campos vacíos.
- FR-5.2 El valor de `icono` debe ser siempre un nombre válido del mapa `ICONOS` del frontend. El conjunto válido actual (en `features/kpis/TarjetaKpi.tsx` y `features/kpis/DetalleKpi.tsx`) es: `Award, BarChart2, BookOpen, Briefcase, Calculator, ClipboardCheck, Heart, Home, Laptop, MessageCircle, Monitor, Shield, Smile, Users, Zap`. Está **prohibido** emitir nombres fuera de ese conjunto (una iteración previa envió `ChartBar`, que no existe en el mapa). Cuando la heurística no tenga una coincidencia clara, debe caer a `BarChart2`.
- FR-5.3 En la interfaz, el usuario debe ver como mínimo el **nombre** del KPI y su **significado** (`Descripcion_Ampliada_Educativa`), que son los dos datos que el usuario pidió explícitamente mostrar. Los demás campos mapeados pueblan la tarjeta/detalle según el diseño del componente ya existente.
- FR-5.4 El mapa `ICONOS` debe estar sincronizado entre el frontend (consumidor) y la heurística que produce `icono` (backend o frontend, según decida el diseño): si la heurística vive en el backend, no debe emitir un nombre que el frontend no mapee.

## Requisitos no funcionales

- NFR-1 (i18n) Todo el texto de cara al usuario, nombres de ruta e identificadores de dominio permanecen en español.
- NFR-2 (Compatibilidad) El cambio no debe romper la refactorización de microservicios vigente (`refactorizacion-microservicios`): se conservan los límites de servicio, el proxy del gateway y los contratos públicos existentes salvo los que esta tarea modifica a propósito.
- NFR-3 (Reproducibilidad) El seed y la reindexación deben ser re-ejecutables de forma determinista a partir del CSV (idempotentes en resultado final: 55 filas en BD, 55 puntos en Chroma).
- NFR-4 (Consistencia de embeddings) Los vectores de KPI deben seguir siendo comparables con los de `summary_instrument` (mismo modelo, misma normalización, misma métrica), para no degradar la búsqueda semántica de propuestas de KPIs.

## Criterios de aceptación (gate de verificación en runtime)

Numerados, específicos y comprobables:

1. **CSV**: la re-lectura de `infrastructure/postgres/seed/kpis_ampliados.csv` con `csv.DictReader` reporta 55 filas de datos, 8 columnas con los nombres exactos listados arriba, 55 nombres de KPI únicos y 0 valores vacíos en `Texto_Contexto_RAG_Vectorial`.
2. **BD**: `SELECT COUNT(*) FROM tt_rag.kpi` devuelve `55`, los `kpi_id` son contiguos en el rango esperado (p. ej. 1..55) y no queda ningún KPI del catálogo anterior.
3. **FK intactas**: tras el reseed, las tablas que referencian `kpi(kpi_id)` siguen teniendo FKs válidas (no quedan referencias colgantes ni se eliminaron las constraints).
4. **Reindex**: `POST /vectorizacion/kpis/reindex` responde `200` con `n_kpis = 55`, y la colección Chroma `kpis` contiene exactamente 55 puntos, cada uno con `id = str(kpi_id)` y su `document` igual al `Texto_Contexto_RAG_Vectorial` del KPI correspondiente.
5. **Texto embebido**: para una muestra de KPIs, el `document` del punto en Chroma es idéntico a `Texto_Contexto_RAG_Vectorial` (no una concatenación con otros campos).
6. **Catálogo real**: el endpoint de catálogo estructurado devuelve `200` con exactamente 55 KPIs, ordenados de forma determinista, cada uno con los campos del mapeo (`nombre`, `descripcionCorta`/`queEs` = significado, `queMide`, `comoSeMide`/`formula`, `infoGeneral`, `etiquetas`, `icono`).
7. **Íconos válidos**: todos los valores de `icono` del catálogo pertenecen al conjunto `ICONOS` del frontend; ninguno es `ChartBar` ni otro nombre inexistente.
8. **Propuestas con nombres reales**: `POST /vectorizacion/propuestas` devuelve propuestas cuyos `nombre_kpi` corresponden a KPIs reales del nuevo catálogo (no a los 30 nombres viejos).
9. **Frontend build**: el build del frontend (`pixel-perfect-pixel`) pasa sin errores de TypeScript tras cablear `getCatalogoKpis` al endpoint real.
10. **Español**: las rutas, mensajes y campos de dominio nuevos están en español.

## Restricciones explícitas

- `kpi_id` permanece como `SERIAL PRIMARY KEY` para que sobrevivan las FKs que lo referencian.
- Todo en español (texto de usuario, rutas, identificadores de dominio).
- No romper `refactorizacion-microservicios` (límites de servicio, proxy del gateway, contratos públicos existentes).
- El CSV `kpis_ampliados.csv` es la **única fuente de verdad** de los datos de KPI; Postgres es la fuente de verdad en runtime derivada del CSV, y Chroma solo almacena el vector + metadatos.
- Embeber únicamente `Texto_Contexto_RAG_Vectorial`; las demás columnas son metadatos.
- Nombres de ícono restringidos al mapa `ICONOS` del frontend, con fallback a `BarChart2`.

## Fuera de alcance

- Rediseño visual de la pantalla de KPIs o del componente `TarjetaKpi` / `DetalleKpi` más allá de poblarlos con datos reales.
- Endpoints de datos de gráfica por KPI (`getDatosGrafica`), KPIs de tablero (`getKpis`) y noticias (`getNoticias`): siguen como mock (TODOs existentes).
- Cambios en el pipeline de inferencia de KPIs por instrumento (`/vectorizacion/propuestas` / `/confirmar`) más allá de que las propuestas reflejen el nuevo catálogo.
- Cambios en el modelo de embeddings, la métrica de distancia o la dimensión del vector.
- Migración de datos históricos de `kpi_inferido` que apunten a KPIs viejos (el usuario autorizó reemplazo destructivo del catálogo; no se solicita preservar inferencias previas).

## Supuestos

- Los `kpi_id` nuevos no necesitan preservar la correspondencia con los `kpi_id` del catálogo viejo (el usuario autorizó reemplazo completo). Si existieran inferencias previas en `kpi_inferido` apuntando a IDs viejos, se consideran descartables en este contexto de pruebas.
- El endpoint de catálogo estructurado puede ser nuevo (p. ej. un `catalogo-detallado`) sin eliminar el `GET /instrumentos/kpis/catalogo` actual, salvo que el diseño determine que ningún consumidor depende del contrato viejo.
- El reorden/reset de la secuencia de `kpi_id` a 1..55 es aceptable porque el catálogo se reemplaza por completo.
