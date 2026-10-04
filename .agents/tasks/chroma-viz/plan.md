# Implementation Plan — Poblar ChromaDB (Momento 1: asociación de KPIs) + visor web de vectores

Runbook para el agente implementador. Es una tarea de **carga de datos + infraestructura**, NO de features:
no se modifica NINGÚN código de microservicio (`services/*`) ni ningún `infrastructure/docker/Dockerfile.*`.
Solo se edita `docker-compose.yml` (un servicio visor nuevo) y se crean scripts/SQL desechables bajo
`.agents/tasks/chroma-viz/scratch/`.

Todos los comandos corren desde la raíz del repo `c:\Users\yarel\Documents\indagata\indagata`,
en la rama `refactorizacion-microservicios`, contra el stack VIVO. Shell: PowerShell (`;` no `&&`).

---

## 0. Hechos verificados contra el stack vivo (no asumidos)

Verificado leyendo el código y consultando el stack en ejecución:

- **Rama actual:** `refactorizacion-microservicios` (confirmado con `git branch --show-current`). Trabajar aquí, commitear aquí, NO usar `main`, NO hacer push, NO merge.
- **Autenticación NO requiere JWT para vectorizar.** `shared/db/core/config.py` tiene `AUTH_DEV_MODE: bool = True` y `DEV_USER_ID: int = 1`; el `.env` de la raíz confirma `AUTH_DEV_MODE=true` y `DEV_USER_ID=1`. `services/analysis-service/app/vectorization/dependencies.py` → `get_current_user` resuelve el usuario `DEV_USER_ID` SIN token cuando `AUTH_DEV_MODE` es true. **Por tanto, las llamadas a `/vectorizacion/*` NO llevan header Authorization.** (El brief asumía JWT; el código real dice lo contrario. Login documentado abajo por si se desactivara el modo dev.)
- **Usuario dev existe:** `tt_rag.usuario` tiene `usuario_id=1` → `admin@indagata.local` (rol `administrador`) y `usuario_id=2` → `investigador@indagata.local`. `DEV_USER_ID=1` resuelve correctamente.
- **Ruta de login (por si se necesita):** `POST http://localhost:8000/auth/login`, body JSON `{"email": "...", "password": "..."}` (schema `LoginRequest` en `services/api-gateway/app/auth/schemas.py`). Respuesta: `{"access_token": "...", "token_type": "bearer", "usuario": {...}}`. Dev admin: `admin@indagata.local` / `admin123`. **NOTA:** el api-gateway (`services/api-gateway/proxy/proxy.py`) NO proxea `/vectorizacion/*`; esos endpoints solo existen directamente en analysis-service (puerto host 8002). No intentar llamarlos vía gateway.
- **Endpoints de vectorización (confirmados en el openapi vivo de :8002):** `/vectorizacion/propuestas`, `/vectorizacion/confirmar`, `/vectorizacion/kpis/reindex`, `/vectorizacion/summary/{id}`, `/health`. analysis-service responde `{"status":"ok"}`.
- **Esquema `tt_rag.kpi` (real, confirmado con `\d`):** `kpi_id SERIAL PK`, `nombre_kpi TEXT NOT NULL`, `descripcion TEXT`, `categoria TEXT`, `ambito TEXT`, `url_documentacion TEXT`, `formula TEXT`. El reindex (`kpi_indexer.py`) vectoriza `nombre_kpi + descripcion + "Categoría: "+categoria + "Ámbito: "+ambito`, con id de punto = `kpi_id`.
- **Seed deshabilitado `infrastructure/postgres/init/_disabled/04_seed.sql` (confirmado):** ~55 KPIs con columnas ANTIGUAS `(nombrekpi, descripcion, direccion_deseada, razon, formula)` + inserts a `variable`. Esas columnas NO existen en el esquema real → por eso se deshabilitó. Hay que remapear.
- **Esquema `tt_rag.instrumento_procesado` (real, confirmado con `\d`):** única columna NOT NULL sin default es `id_crudo` (FK → `raw_data.id_crudo`). `estado` tiene default `'recibido'`. **Cada instrumento necesita primero una fila padre en `raw_data`.**
- **Esquema `tt_rag.raw_data` (real):** NOT NULL = `id_owner` (FK → usuario), `tipo_instrumento`, `nombre_archivo`, `raw_archivo`. `raw_archivo_original` es opcional.
- **Estado inicial de la BD (limpio):** `kpi`=0, `instrumento_procesado`=0, `raw_data`=0 filas. Pizarra limpia.
- **Datos del host:** 21 archivos en `C:\Users\yarel\generaData\output\md\inst_01.md..inst_21.md` y 21 en `C:\Users\yarel\generaData\output\json\inst_01.v1.json..inst_21.v1.json`. JSON raíz: `instrument_id` (p.ej. `"inst_01"`), `metadata.dublin_core` (dc:title/subject/description/coverage presentes), `metadata.survey_specific` (notas_contextuales/notas_interpretacion vienen VACÍAS — el código tiene `PLACEHOLDERS_NOTAS`, así que está bien esta vez), `respondents` (250 por archivo → carrera se resuelve desde ahí). Codificación UTF-8.
- **ChromaDB:** imagen `chromadb/chroma:latest`, versión API `1.0.0`, API **v2**. Puerto host **8008 → contenedor 8000**. El contenedor interno se llama `chromadb` en la red `indagata_network`. Colecciones actuales: `[]` (vacío). Endpoint de listado verificado: `GET http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections`.
- **analysis-service** apunta a Chroma por entorno `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000` (inyectado por compose), embeddings 768-dim, modelo cacheado en volumen `hf_cache`.
- **Puertos host libres (confirmado con `Get-NetTCPConnection`):** `3001`, `8090`, `8085`, `8010` LIBRES. `8080` OCUPADO (contenedor ajeno `liverpool-talento-frontend`). **El visor usará el puerto host `8085`** (libre, fuera del rango 8000-8008 del stack).
- **Carpeta `storage/` bind-montada** existe con `raw/ json/ clean/ sav/`.

**Asumido (no verificado):** que la primera llamada a `/vectorizacion/propuestas` tarda unos segundos al cargar el modelo de embeddings aunque esté cacheado (comportamiento normal de sentence-transformers). El resto está verificado.

---

## Decisión de arquitectura del visor

El usuario pidió explícitamente ver los vectores como **"un mapa de puntos"** / gráficamente (mensajes 7-12),
no una tabla. Los admins off-the-shelf (`flanker/chromadb-admin`, `fengzhichao/chromadb-admin`,
`BlackyDrum/chromadb-ui`) son navegadores de tablas/colecciones, no dispersogramas 2D, y varios arrastran
incompatibilidades con la API v2 de Chroma 1.0.0. Por eso se construye un **visor propio read-only**
(FastAPI + HTML/JS estático con Plotly) que lee Chroma por la API v2, proyecta los embeddings a 2D con PCA
y pinta un scatter coloreado por colección. Es un contenedor NUEVO con su propio Dockerfile en el scratch dir
(NO toca `infrastructure/docker/Dockerfile.*`). **Fallback documentado** (sección 9) si se prefiere algo instantáneo:
`flanker/chromadb-admin` en el puerto 3001.

---

## Plan ordenado

- [ ] 1. Crear la carpeta de trabajo desechable y la rama de verificación de puerto.
      Crear `.agents/tasks/chroma-viz/scratch/`. Confirmar rama y stack.
      Files: `.agents/tasks/chroma-viz/scratch/` (dir)
      Verify: `git branch --show-current` imprime `refactorizacion-microservicios`; `docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.kpi;"` imprime `0`.

- [ ] 2. Escribir el SQL de siembra de KPIs remapeado a las columnas reales.
      Crear `.agents/tasks/chroma-viz/scratch/seed_kpis.sql`. Empieza con `SET search_path TO tt_rag, public;` y `TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE;` (demo/throwaway, idempotente). Tomar ~30 KPIs del seed deshabilitado `infrastructure/postgres/init/_disabled/04_seed.sql` y mapear a columnas REALES: `nombrekpi → nombre_kpi`, `descripcion → descripcion`, `formula → formula`. Plegar `direccion_deseada` (Aumentar/Disminuir/Monitorear/Mixto) en `ambito` (texto corto, p.ej. `'Dirección deseada: Aumentar'`) y usar una `categoria` temática sensata (p.ej. `'Académico'`, `'Financiero'`, `'Investigación'`, `'Experiencia estudiantil'`). Opcional: anexar `razon` al final de `descripcion`. NO inventar columnas (nada de `direccion_deseada`/`razon`/`nombrekpi` como columnas). NO insertar en `variable` (no hace falta para la vectorización). Añadir un comentario de cabecera "DEMO / THROWAWAY".
      Files: `.agents/tasks/chroma-viz/scratch/seed_kpis.sql`
      Verify: aplicar y contar — `Get-Content .agents/tasks/chroma-viz/scratch/seed_kpis.sql | docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db` termina sin error; luego `docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.kpi;"` imprime ~30 (>0).

- [ ] 3. Reindexar la colección `kpis` en Chroma desde la BD.
      Llamar al endpoint de mantenimiento (sin JWT; AUTH_DEV_MODE). La primera llamada carga el modelo de embeddings (segundos).
      Files: ninguno (llamada HTTP)
      Verify: `curl.exe -s -X POST http://localhost:8002/vectorizacion/kpis/reindex` devuelve JSON `{"coleccion":"kpis","n_kpis":<~30>}` con `n_kpis > 0`. Confirmar en Chroma: `curl.exe -s http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections` lista una colección `kpis`.

- [ ] 4. Crear las 21 filas padre `raw_data` + sus `instrumento_procesado`, capturando cada `id_instrumento`.
      Escribir `.agents/tasks/chroma-viz/scratch/seed_instrumentos.sql`: `SET search_path TO tt_rag, public;` y para cada `inst_NN` (01..21) insertar en `raw_data` (`id_owner=1`, `tipo_instrumento='encuesta'`, `nombre_archivo='inst_NN.v1.json'`, `raw_archivo='/app/storage/raw/inst_NN.v1.json'`, `raw_archivo_original='/app/storage/raw/inst_NN.md'`) y luego su `instrumento_procesado` (`id_crudo` = el recién creado, `estado='recibido'`, `ruta_json='/app/storage/raw/inst_NN.v1.json'`). Usar un bloque `INSERT ... RETURNING` o un `DO`/CTE que inserte el padre y la hija en orden. Al final, `SELECT ip.id_instrumento, rd.nombre_archivo FROM instrumento_procesado ip JOIN raw_data rd ON rd.id_crudo=ip.id_crudo ORDER BY ip.id_instrumento;` para imprimir el mapeo `inst_NN → id_instrumento`. Guardar ese mapeo (lo usa el paso 6). Marcar como DEMO/THROWAWAY.
      Files: `.agents/tasks/chroma-viz/scratch/seed_instrumentos.sql`
      Verify: aplicar con `Get-Content ... | docker compose ... psql` sin error; `docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.instrumento_procesado;"` imprime `21` y el SELECT final imprime 21 pares `inst_NN → id_instrumento`.

- [ ] 5. Copiar los 21 md + 21 json al árbol bind-montado `storage/raw`.
      Copiar `C:\Users\yarel\generaData\output\md\*.md` y `C:\Users\yarel\generaData\output\json\*.json` a `c:\Users\yarel\Documents\indagata\indagata\storage\raw\`. (Mantiene los archivos dentro del árbol del proyecto; también sirven de referencia para `raw_archivo`/`raw_archivo_original`. El POST del paso 6 igualmente envía los bytes por multipart, así que la ruta exacta no es crítica, pero esto deja todo auto-contenido.)
      Files: `storage/raw/inst_01.md..inst_21.md`, `storage/raw/inst_01.v1.json..inst_21.v1.json`
      Verify: `(Get-ChildItem storage\raw -Filter *.md).Count` → `21` y `(Get-ChildItem storage\raw -Filter *.v1.json).Count` → `21`.

- [ ] 6. Vectorizar los 21 instrumentos vía `/vectorizacion/propuestas` (Momento 1), un POST por instrumento con su `id_instrumento` del paso 4.
      Escribir un script PowerShell desechable `.agents/tasks/chroma-viz/scratch/post_propuestas.ps1` que recorra `inst_01..inst_21`, lea el mapeo `inst_NN → id_instrumento` (hardcodearlo desde el SELECT del paso 4, o re-consultarlo a psql), y para cada uno ejecute **`curl.exe`** (no el alias PS) con multipart: `-F "archivo_json=@storage/raw/inst_NN.v1.json;type=application/json" -F "instrumento_original=@storage/raw/inst_NN.md;type=text/markdown" -F "tipo_instrumento=encuesta" -F "id_instrumento=<ID>"` contra `http://localhost:8002/vectorizacion/propuestas`. SIN header Authorization. Comprobar que cada respuesta sea HTTP 200 y contenga `id_instrumento`/`propuestas`. Imprimir un resumen (21 OK / fallos).
      Files: `.agents/tasks/chroma-viz/scratch/post_propuestas.ps1`
      Verify: el script reporta 21 respuestas HTTP 200. Confirmar en BD opcional y en Chroma en el paso 7.

- [ ] 7. Verificar que Chroma tiene ambas colecciones pobladas.
      Listar colecciones y contar puntos por la API v2 (puerto host 8008). Para el conteo, obtener el `id` de cada colección del listado y llamar al endpoint de count: `GET http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections/<collection_id>/count`.
      Files: ninguno (llamadas HTTP; opcional guardar `.agents/tasks/chroma-viz/scratch/verify_chroma.ps1`)
      Verify: el listado incluye `kpis` y `summary_instrument`; `count` de `kpis` ≈ 30 y `count` de `summary_instrument` = `21`.

- [ ] 8. Construir el visor web read-only (FastAPI + Plotly scatter PCA) como scratch, SIN tocar servicios.
      Crear bajo `.agents/tasks/chroma-viz/scratch/viewer/`: `Dockerfile` (base `python:3.11-slim`, instala `fastapi uvicorn chromadb numpy scikit-learn jinja2`), `app.py` (FastAPI read-only: se conecta a Chroma host `chromadb` puerto `8000` por `chromadb.HttpClient`; un endpoint `GET /api/points` que para cada colección hace `collection.get(include=["embeddings","metadatas","documents"])`, apila los embeddings, aplica `sklearn.decomposition.PCA(n_components=2)` sobre el conjunto unido, y devuelve `[{x,y,coleccion,label,id}]`; un endpoint `GET /` que sirve una página con Plotly CDN que pinta el scatter coloreado por colección, con hover mostrando `label`/`id`), y `requirements.txt`. El visor NO escribe en Chroma. Usar la versión del cliente `chromadb` compatible con servidor 1.0.0 (API v2) — fijar `chromadb==1.0.*` en requirements para que hable v2.
      Files: `.agents/tasks/chroma-viz/scratch/viewer/Dockerfile`, `.agents/tasks/chroma-viz/scratch/viewer/app.py`, `.agents/tasks/chroma-viz/scratch/viewer/requirements.txt`, `.agents/tasks/chroma-viz/scratch/viewer/templates/index.html` (o HTML inline)
      Verify: `docker build -t indagata-chroma-viewer .agents/tasks/chroma-viz/scratch/viewer` termina con éxito (imagen creada).

- [ ] 9. Añadir el servicio visor NUEVO a `docker-compose.yml` y levantarlo. (ÚNICA edición de archivo versionado.)
      Añadir al final de `services:` en `docker-compose.yml` (sin tocar ningún servicio existente) un bloque:
      ```yaml
        chroma-viewer:
          build:
            context: ./.agents/tasks/chroma-viz/scratch/viewer
            dockerfile: Dockerfile
          container_name: indagata_chroma_viewer
          environment:
            CHROMA_HOST: chromadb
            CHROMA_PORT: 8000
          ports:
            - "8085:8000"
          depends_on:
            - chromadb
          networks:
            - indagata_network
          restart: unless-stopped
      ```
      (El contenedor sirve FastAPI en su puerto interno 8000; se publica en host 8085 — libre. Se une a `indagata_network` para alcanzar `chromadb:8000`.) Levantar solo ese servicio.
      Files: `docker-compose.yml`
      Verify: `docker compose -f docker-compose.yml up -d --build chroma-viewer` arranca sin error; `docker ps` muestra `indagata_chroma_viewer` Up; `curl.exe -s http://localhost:8085/api/points` devuelve JSON con puntos de `kpis` y `summary_instrument`; abrir `http://localhost:8085/` en el navegador muestra el dispersograma 2D coloreado por colección. (La advertencia `version is obsolete` del compose es inofensiva.)

- [ ] 10. Commit en la rama `refactorizacion-microservicios` (SIN push).
      Commitear SOLO `docker-compose.yml` (el servicio visor). El contenido de `.agents/` queda fuera del árbol versionado por convención del workflow; si git lo rastrea, NO incluirlo en este commit (solo `docker-compose.yml`). Verificar que no se tocó ningún `services/*` ni `infrastructure/docker/Dockerfile.*`.
      Files: `docker-compose.yml`
      Verify: `git status --porcelain` no muestra cambios en `services/` ni en `infrastructure/docker/`; `git add docker-compose.yml; git commit -m "ajustes"` crea el commit; `git log -1 --name-only` muestra solo `docker-compose.yml`. NO ejecutar `git push`.

---

## Secuencia de comandos (resumen pasos 2-7, PowerShell desde la raíz)

```powershell
# 2. Sembrar KPIs
Get-Content .agents/tasks/chroma-viz/scratch/seed_kpis.sql | docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db
docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SELECT count(*) FROM tt_rag.kpi;"

# 3. Reindexar KPIs en Chroma (sin JWT: AUTH_DEV_MODE=true)
curl.exe -s -X POST http://localhost:8002/vectorizacion/kpis/reindex

# 4. Crear raw_data + instrumento_procesado (imprime mapeo inst_NN -> id_instrumento)
Get-Content .agents/tasks/chroma-viz/scratch/seed_instrumentos.sql | docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db

# 5. Copiar archivos al bind mount
Copy-Item C:\Users\yarel\generaData\output\md\*.md   storage\raw\
Copy-Item C:\Users\yarel\generaData\output\json\*.json storage\raw\

# 6. POST de los 21 instrumentos (Momento 1)
.\.agents\tasks\chroma-viz\scratch\post_propuestas.ps1

# 7. Verificar colecciones
curl.exe -s http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections
```

Ejemplo de un POST individual del paso 6 (referencia):
```powershell
curl.exe -s -o NUL -w "%{http_code}`n" -X POST http://localhost:8002/vectorizacion/propuestas `
  -F "archivo_json=@storage/raw/inst_01.v1.json;type=application/json" `
  -F "instrumento_original=@storage/raw/inst_01.md;type=text/markdown" `
  -F "tipo_instrumento=encuesta" `
  -F "id_instrumento=1"
```

---

## 9. Fallback del visor (si se prefiere off-the-shelf en vez del custom)

Si el visor custom diera problemas de build, usar `flanker/chromadb-admin` (navegador de tablas, NO scatter).
Bloque compose alternativo (puerto host 3001, libre):
```yaml
  chroma-viewer:
    image: fengzhichao/chromadb-admin
    container_name: indagata_chroma_viewer
    ports:
      - "3001:3001"
    networks:
      - indagata_network
    restart: unless-stopped
```
En la UI (http://localhost:3001) configurar la conexión a `http://chromadb:8000` (nombre del contenedor en la red).
Limitación conocida: estas UIs listan colecciones/registros pero NO dibujan un mapa de puntos 2D, que es lo que
el usuario pidió — por eso el plan prefiere el visor custom.

---

## 10. Limpieza (todo es DEMO / THROWAWAY)

Cuando el usuario tenga los KPIs/instrumentos reales, borrar lo sembrado y recargar:

```powershell
# Vaciar tablas (CASCADE limpia instrumento_procesado, kpi_inferido, etc.)
docker compose -f docker-compose.yml exec -T postgres psql -U postgres -d indagata_db -c "SET search_path TO tt_rag,public; TRUNCATE kpi RESTART IDENTITY CASCADE; TRUNCATE instrumento_procesado RESTART IDENTITY CASCADE; TRUNCATE raw_data RESTART IDENTITY CASCADE;"

# Borrar las colecciones de Chroma (API v2). Obtener el id de cada colección y DELETE:
#   GET  http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections
#   DELETE .../collections/kpis   y   .../collections/summary_instrument   (por nombre o id)
curl.exe -s -X DELETE "http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections/kpis"
curl.exe -s -X DELETE "http://localhost:8008/api/v2/tenants/default_tenant/databases/default_database/collections/summary_instrument"

# Quitar los archivos copiados
Remove-Item storage\raw\inst_*.md, storage\raw\inst_*.v1.json

# Bajar el visor (si se quiere)
docker compose -f docker-compose.yml stop chroma-viewer; docker compose -f docker-compose.yml rm -f chroma-viewer
```

**Recargar con datos reales:** repetir pasos 2-7 con los nuevos SQL/archivos — primero `seed_kpis.sql` (o el
catálogo real) + `POST /vectorizacion/kpis/reindex`, luego crear filas `raw_data`/`instrumento_procesado` y
hacer `POST /vectorizacion/propuestas` por instrumento. **Esto NO toca el código de los microservicios**: solo
alimenta la BD y Chroma usando los endpoints ya existentes. El visor sigue funcionando sin cambios.

---

## Definición de "hecho"

1. `tt_rag.kpi` tiene ~30 filas demo; `kpis` en Chroma poblada (`reindex` devolvió `n_kpis>0`).
2. 21 filas en `instrumento_procesado` (con sus `raw_data`), mapeadas a `inst_01..inst_21`.
3. Colección `summary_instrument` en Chroma con 21 puntos.
4. Servicio `chroma-viewer` nuevo en `docker-compose.yml`, levantado, mostrando el dispersograma 2D en `http://localhost:8085/`.
5. Ningún archivo bajo `services/*` ni `infrastructure/docker/Dockerfile.*` modificado.
6. Commit "ajustes" en `refactorizacion-microservicios` con SOLO `docker-compose.yml`. Sin push, sin merge a main.
7. Sección de limpieza documentada arriba.
