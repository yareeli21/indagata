# Runbook — Visor de Vectores ChromaDB

Visor web read-only para inspeccionar los embeddings almacenados en ChromaDB.
Servicio **standalone** definido en `docker-compose.yml` (`chroma-viewer`). No
modifica ningún microservicio.

## (a) Cómo abrir el visor

1. Levantar el stack (o solo el visor y sus dependencias):

   ```bash
   docker compose up -d chromadb chroma-viewer
   ```

2. Abrir en el navegador:

   **http://localhost:8085**

   El contenedor expone el puerto interno `8000` mapeado a `8085` en el host.
   Se conecta a ChromaDB vía `CHROMA_HOST=chromadb` / `CHROMA_PORT=8000` dentro
   de la red `indagata_network`.

## (b) Qué vas a ver

El visor muestra una proyección PCA 2D de los embeddings, coloreada por
colección. Hay **2 colecciones**:

- **`kpis`** — ~30 puntos. Vectorización de la técnica de asociación de KPIs
  (instrumento original en `.md` + metadatos destacados del `.json`).
- **`summary_instrument`** — 21 puntos. Un punto por cada instrumento (encuestas)
  cargado desde las rutas locales del usuario.

Cada punto es un vector; el agrupamiento visual da una idea de similitud entre
instrumentos/KPIs. Es solo lectura: no edita ni crea datos.

## (c) Cómo borrar y recargar más adelante

Cuando tengas los datos reales y quieras reemplazar lo que está cargado ahora:

### 1. Vaciar las tablas en Postgres (esquema `tt_rag`)

Truncar los procesados y sus hijos. Respetar el orden/parents con `CASCADE`:

```sql
TRUNCATE TABLE tt_rag.kpi RESTART IDENTITY CASCADE;
TRUNCATE TABLE tt_rag.instrumento_procesado RESTART IDENTITY CASCADE;
```

> Nota: usar `CASCADE` para arrastrar cualquier tabla hija/padre dependiente.
> Ajustar los nombres si tu esquema real difiere; verificar con `\dt tt_rag.*`.

### 2. Borrar las 2 colecciones en Chroma

Eliminar las colecciones `kpis` y `summary_instrument` para que se regeneren
limpias (vía cliente de Chroma o endpoint administrativo del
vectorization-service, según corresponda):

- `kpis`
- `summary_instrument`

### 3. Re-llamar los endpoints de reindexado

En este orden:

1. `/vectorizacion/kpis/reindex` — reconstruye la colección `kpis`.
2. `/vectorizacion/propuestas` — llamar **por cada instrumento** para repoblar
   `summary_instrument`.

Tras esto, refrescar http://localhost:8085 para ver la nueva proyección.

## (d) Alcance de los cambios (confirmación)

- **NO** se modificó código de ningún microservicio bajo `services/*`.
- **NO** se modificó ningún `Dockerfile` bajo `infrastructure/docker/`.
- El único archivo versionado modificado y commiteado fue **`docker-compose.yml`**
  (se agregó el servicio standalone `chroma-viewer`).
- Los artefactos del visor viven en `.agents/tasks/chroma-viz/scratch/viewer`
  y los datos copiados en `storage/raw/` quedan **sin versionar** (untracked).

Commit: `0a42816` — `ajustes: visor ChromaDB (servicio standalone en docker-compose)`
