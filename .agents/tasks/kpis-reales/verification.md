# Verificación de runtime — kpis-reales

Worktree: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales` (rama `kpis-reales`).
Proyecto Docker Compose: `indagata` (contenedores `indagata_*`). Compose del worktree.

Conteo real del CSV (fuente de verdad, recontado en runtime): **55** filas de datos, 8 columnas,
0 nombres vacíos, 0 textos RAG vacíos.

## Correcciones aplicadas durante la verificación (commit local en kpis-reales)

El orden vinculante `docker compose exec analysis-service python scripts/seed_kpis.py` fallaba por
dos defectos de ejecución en contenedor (no cambian lo que ve el usuario ni el comportamiento del
sistema; solo habilitan el flujo de seed ya documentado):

1. `services/analysis-service/scripts/seed_kpis.py` — el guard de `sys.path` y la resolución de la
   ruta del CSV asumían `parents[3]` = raíz del repo (válido solo en ejecución local desde
   `services/analysis-service/`). En el contenedor `/app` es la carpeta del servicio: `parents[3]`
   lanzaba `IndexError` y `/app` no estaba en `sys.path` al invocar `python scripts/seed_kpis.py`
   (en `sys.path[0]` queda la carpeta del script). Se hizo robusto a ambos layouts (busca `shared/`
   y el CSV en `parents[1]` = /app y `parents[3]` = raíz, sin lanzar si falta un nivel).
2. `docker-compose.yml` — `infrastructure/postgres/seed/` no estaba montado en el contenedor de
   analysis-service, así que el CSV no era alcanzable. Se añadió el bind mount de solo lectura
   `./infrastructure/postgres/seed:/app/infrastructure/postgres/seed:ro`.

## Orden vinculante ejecutado

### (0) down -v + up (recreación de volúmenes Postgres + Chroma)

```
docker compose -p indagata -f <main>/docker-compose.yml down -v      # baja proyecto previo + volúmenes
docker compose -p indagata up -d postgres chromadb redis ollama analysis-service   # desde el worktree
```
- Volúmenes recreados: `indagata_postgres_data`, `indagata_chromadb_data`, etc. `01_schema.sql`
  aplicó la forma nueva desde cero.
- `frontend` (servicio del dir legacy `./frontend`) NO se levanta: su `npm ci` falla por falta de
  package-lock. Es un fallo preexistente ajeno a esta tarea (el frontend de la tarea es
  `pixel-perfect-pixel`, verificado por build aparte). No afecta runtime de KPIs.

Forma de `tt_rag.kpi` tras recrear volumen (`\d tt_rag.kpi`): 9 columnas
(`kpi_id SERIAL PK`, `nombre NOT NULL`, 6 metadatos nullable, `texto_contexto_rag_vectorial NOT NULL`).
Referenciada por FKs `kpi_variable_kpi_id_fkey` y `kpi_inferido_kpi_id_fkey`.

### (1-2) Seed

```
docker compose -p indagata exec -T analysis-service python scripts/seed_kpis.py
```
Salida: `INFO Seed de KPIs completo: 55 insertados.` → **n_insertados = 55**.

### (3) Conteo real en BD + IDs contiguos + FKs (CA-2, CA-3)

```
SELECT COUNT(*), MIN(kpi_id), MAX(kpi_id), (MAX-MIN+1)=COUNT AS contiguo FROM tt_rag.kpi;
-> 55 | 1 | 55 | t
SELECT conname FROM pg_constraint WHERE contype='f' AND confrelid='tt_rag.kpi'::regclass;
-> kpi_inferido_kpi_id_fkey, kpi_variable_kpi_id_fkey
```
CA-2 ✔ (55, IDs contiguos 1..55). CA-3 ✔ (FKs hacia kpi(kpi_id) intactas tras el reseed).

### (4) Reindex (CA-4, CA-5)

```
POST http://localhost:8002/vectorizacion/kpis/reindex
-> 200  {"coleccion":"kpis","n_kpis":55,"mensaje":"Colección de KPIs reindexada."}
```
Inspección de la colección Chroma `kpis`:
- `col.count()` = **55**.
- Todos los ids = `str(kpi_id)`, rango 1..55 (min=1, max=55, n=55).
- Metadatos con clave nueva `nombre` (sin `nombre_kpi` viejo); claves:
  `descripcion_ampliada_educativa, formula_metrica_calculo, kpi_id, nombre, polaridad_rendimiento, tipo_objetivo_estrategico`.
- `document == texto_contexto_rag_vectorial` para muestra ids 1, 28, 55 → ALL_MATCH=True.

CA-4 ✔ (exactamente 55 puntos, id=str(kpi_id)). CA-5 ✔ (document = texto RAG, no concatenación).

### (5) Catálogo (CA-6, CA-7)

```
GET http://localhost:8002/vectorizacion/kpis/catalogo
-> 200, N=55, ORDERED=True (id 1..55)
```
- 8 campos presentes: `id, nombre, descripcion_ampliada_educativa, polaridad_rendimiento,
  tipo_objetivo_estrategico, formula_metrica_calculo, comportamiento_direccional_causalidad,
  razon_estrategica_decisiones`.
- EMPTY_NOMBRE=0, EMPTY_SIGNIF=0 (significado = `descripcion_ampliada_educativa` poblado).

CA-6 ✔. CA-7 ✔: el ícono se calcula en el frontend (`elegirIcono` en `src/api/kpis.ts`) y está
acotado por `ICONOS_VALIDOS.has(candidato) ? candidato : "BarChart2"`, por lo que nunca emite un
nombre fuera del mapa ni `ChartBar`. Verificado por lectura del código + build verde (CA-9).

### (6) Propuestas con nombres reales (CA-8)

```
POST http://localhost:8002/vectorizacion/propuestas  (encuesta, id_instrumento=1)
-> 200, 5 propuestas:
   52 | Tasa de Participación en Programas de Intercambio / Estudio en el Extranjero | 0.4938
   37 | Tasa de Continuidad en Estudios de Posgrado | 0.4924
   49 | Puntaje de Satisfacción Estudiantil (NPS / Encuestas) | 0.4767
   24 | Tasa de Inserción Laboral de Egresados | 0.4722
   47 | Uso de Servicios de Salud Mental y Apoyo Psicológico | 0.4659
```
CA-8 ✔: nombres reales del catálogo nuevo (ids dentro de 1..55; campo `nombre` nuevo), no los viejos.

### (7) Build de frontend (CA-9)

```
cd pixel-perfect-pixel && npm run build
-> ✓ built in 2.12s  (sin errores de TypeScript)
```
CA-9 ✔.

## Resultado

Todos los criterios de aceptación de runtime (CA-2..CA-9) pasan. `passed = true`.
