# ChromaDB poblada (Momento 1: asociación de KPIs) + visor de vectores read-only

Esta tarea era de carga de datos + infraestructura, no de features. El implementador sembró ~30 KPIs demo en `tt_rag.kpi`, creó 21 pares `raw_data`/`instrumento_procesado`, reindexó la colección `kpis` en Chroma, vectorizó los 21 instrumentos (`summary_instrument`), y añadió un servicio nuevo `chroma-viewer` que proyecta los embeddings a 2D con PCA y los pinta en un dispersograma. La restricción dura del gate era que el único archivo versionado tocado fuera `docker-compose.yml` — una iteración previa fue rechazada por tocar `services/analysis-service/requirements.txt` y nueve archivos de `pixel-perfect-pixel/src/*`, y esta iteración los revirtió con `git checkout --`.

Watch for: nada bloqueante. El diff versionado es exclusivamente `docker-compose.yml` (confirmed, verificado con `git status --porcelain --untracked-files=no` → sólo ` M docker-compose.yml`). El pin `chromadb-client==1.0.0` que permitió correr la vectorización ya NO está en la superficie versionada tras el revert; es un riesgo de rebuild futuro, no de este paso (likely).

**Verdict**: APPROVED

## High-level view

La restricción crítica se cumple. `git diff --name-only` sobre `services` e `infrastructure/docker` no devuelve nada, y el único cambio rastreado es `docker-compose.yml`. El revert documentado en verification.md coincide con el estado real del árbol: los archivos de servicio y de `pixel-perfect-pixel` ya no aparecen como modificados.

El cambio en `docker-compose.yml` añade un bloque `chroma-viewer` al final de `services:` sin tocar ningún bloque existente (el diff es un `+` puro de 20 líneas). El servicio construye desde `./.agents/tasks/chroma-viz/scratch/viewer`, se une a `indagata_network`, apunta a `chromadb:8000` por entorno y publica en el puerto host 8085, que el plan verificó libre.

Las dos colecciones de Chroma están pobladas. El spot-check en vivo (`GET .../collections`) confirma `kpis` y `summary_instrument`, ambas dim 768, consistente con los conteos registrados (30 y 21).

Los KPIs se mapearon a las columnas REALES de `tt_rag.kpi`. El `INSERT` usa `(nombre_kpi, descripcion, categoria, ambito, formula)` — todas presentes en `01_schema.sql`. Las columnas antiguas del seed deshabilitado (`nombrekpi`, `direccion_deseada`, `razon`) se plegaron en campos reales en vez de inventarse. Son 30 filas exactas.

Las filas de instrumento se crearon en el orden correcto de FK: `raw_data` padre con `RETURNING id_crudo`, luego `instrumento_procesado` hija referenciando ese `id_crudo`. El mapeo salió 1:1 (`inst_NN` → id N), coherente con `id_map.json`.

El visor es read-only de verdad: sólo llama `list_collections()` y `col.get(...)`, nunca `add`/`upsert`/`delete`.

La limpieza está documentada en verification.md y en la sección 10 del plan: TRUNCATE con CASCADE de las tres tablas, DELETE de ambas colecciones Chroma por la API v2, borrado de los archivos copiados, y la secuencia de endpoints a re-llamar para recargar con datos reales (reindex de KPIs + propuestas por instrumento). Confirma explícitamente que no se tocó código de microservicio.

<details>
<summary>Issues (1)</summary>

1. **Pin chromadb-client fuera de la superficie versionada** — el `chromadb-client==1.0.0` que habilitó la vectorización se revirtió junto con `services/analysis-service/requirements.txt`. El stack vivo corre con la imagen ya construida, así que no afecta ahora, pero un rebuild futuro de analysis-service podría regresar al cliente incompatible con la API v2. Debe reintroducirse en un cambio aparte explícitamente autorizado cuando toque modificar servicios. No bloquea este paso.

</details>

<details>
<summary>Details</summary>

### Cumplimiento de la restricción dura (único archivo versionado = docker-compose.yml)

Es el criterio que tumbó la iteración anterior, así que se verificó directamente y no sólo por la evidencia. `git status --porcelain --untracked-files=no` imprime una sola línea: ` M docker-compose.yml` (confirmed). `git diff --name-only -- services infrastructure/docker` devuelve vacío (confirmed) — no hay cambios rastreados bajo `services/*` ni `infrastructure/docker/`. El revert descrito en verification.md (requirements.txt del analysis-service + nueve archivos de `pixel-perfect-pixel/src/*`) corresponde al estado real del árbol. Los archivos de datos, scratch y los `storage/raw/inst_*` aparecen como *untracked*, no como modificaciones de archivos versionados, así que no cuentan contra la restricción.

### El bloque chroma-viewer en docker-compose.yml

El diff es puramente aditivo (confirmed): 20 líneas insertadas, cero borradas, un bloque nuevo entre el último servicio y la sección `networks:`. No se alteró ningún servicio existente.

```
chroma-viewer:
  build:
    context: ./.agents/tasks/chroma-viz/scratch/viewer
  ports: [ "8085:8000" ]
  environment: { CHROMA_HOST: chromadb, CHROMA_PORT: 8000 }
  depends_on: [ chromadb ]
  networks: [ indagata_network ]
```

El contenedor sirve FastAPI en su puerto interno 8000 y se publica en el host 8085 (el plan lo verificó libre con `Get-NetTCPConnection`, fuera del rango 8000-8008 del stack). Al unirse a `indagata_network` alcanza `chromadb:8000` por nombre de contenedor. El `depends_on` sólo garantiza orden de arranque, no readiness de Chroma, pero el visor tolera un Chroma aún no listo: `/api/points` captura la excepción y responde 502 con el error, en vez de tumbarse. Comportamiento razonable para un visor de diagnóstico.

### Las dos colecciones de Chroma

Spot-check en vivo permitido (no se re-ejecutó la carga): `GET http://localhost:8008/api/v2/.../collections` devuelve exactamente `summary_instrument` (id 7dc5fa53…) y `kpis` (id bc2c609a…), ambas `dimension: 768` (confirmed). Coincide con los conteos de verification.md (`kpis`=30, `summary_instrument`=21) y con el `/api/points` del visor (count=51). Las claves de esquema de cada colección (`nombre_kpi`/`ambito`/`categoria`/`kpi_id` en `kpis`; `id_instrumento`/`tipo_instrumento`/`seccion` en `summary_instrument`) confirman que el indexador escribió los metadatos esperados.

### Mapeo de KPIs a columnas reales

`seed_kpis.sql` inserta en `kpi (nombre_kpi, descripcion, categoria, ambito, formula)`. Contrastado con `01_schema.sql` líneas 178-187, esas son columnas reales (`kpi_id SERIAL PK`, `nombre_kpi TEXT NOT NULL`, `descripcion`, `categoria`, `ambito`, `url_documentacion`, `formula`). No se insertó ninguna columna inventada — las antiguas `nombrekpi`/`direccion_deseada`/`razon` del seed deshabilitado se remapearon: `direccion_deseada` se plegó como texto dentro de `ambito` ("Dirección deseada: Aumentar/Disminuir/Monitorear/Mixto") y `razon` se anexó a `descripcion` (confirmed). Son 30 `VALUES` exactos. El `TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE` al inicio lo hace idempotente. No inserta en `variable` ni `kpi_variable`, lo cual es correcto: el reindexer (`kpi_indexer.py`) sólo necesita `nombre_kpi`/`descripcion`/`categoria`/`ambito` para construir el documento a vectorizar.

### Orden de FK en raw_data / instrumento_procesado

`seed_instrumentos.sql` resuelve la dependencia de FK correctamente: por cada `inst_NN` inserta primero el padre `raw_data` (con los cuatro NOT NULL: `id_owner=1`, `tipo_instrumento='encuesta'`, `nombre_archivo`, `raw_archivo`) y captura su clave con `RETURNING id_crudo INTO v_crudo`, luego inserta la hija `instrumento_procesado` referenciando ese `id_crudo` (confirmed). El `TRUNCATE ... CASCADE` de ambas tablas al inicio la hace idempotente. El `SELECT` final emite el mapeo `inst_NN → id_instrumento`, que resultó 1:1 y quedó persistido en `id_map.json` (inst_01→1 … inst_21→21), consistente con los IDs que luego consumió el POST de propuestas.

### El visor es read-only

`app.py` sólo abre un `chromadb.HttpClient` y llama `list_collections()` y `col.get(include=["embeddings","metadatas","documents"])` (confirmed). No hay ninguna llamada de escritura (`add`/`upsert`/`update`/`delete`/`create_collection`). El PCA se aplica sobre el conjunto unido de embeddings de todas las colecciones, lo que hace que las posiciones 2D sean relativas al conjunto completo — adecuado para "mapa de puntos" coloreado por colección, que es lo que el usuario pidió (mensajes 7-12). El `/api/points` degrada a `n_components=1` si hubiera menos de 2 puntos o dimensiones, un borde que aquí no aplica (hay 51 puntos de 768 dim) pero evita que PCA reviente en datasets diminutos.

### Limpieza documentada y aislamiento de microservicios

La sección 10 del plan y la sección de cierre de verification.md documentan el throwaway completo: `TRUNCATE kpi/instrumento_procesado/raw_data RESTART IDENTITY CASCADE`, `DELETE` de las colecciones `kpis` y `summary_instrument` por la API v2 (por id o nombre), `Remove-Item` de los `storage/raw/inst_*`, y la secuencia de recarga con datos reales: `seed_kpis` + `POST /vectorizacion/kpis/reindex`, luego crear `raw_data`/`instrumento_procesado` y `POST /vectorizacion/propuestas` por instrumento (confirmed). Ambos documentos afirman explícitamente que esto no toca código de microservicio y que el flujo de recarga usa sólo endpoints ya existentes. Responde directamente la pregunta del usuario (mensaje 12) sobre cómo reemplazar los datos demo por los reales sin mover los microservicios.

### Cobertura de verificación

Probado y registrado: conteo de `tt_rag.kpi` (30), `reindex` HTTP 200 con `n_kpis=30`, conteo de `instrumento_procesado` (21), 21× POST propuestas HTTP 200 / 0 fallos, conteos Chroma por la API v2 (30 / 21), y el visor respondiendo 200 en `/` y 51 puntos en `/api/points`.

No probado: que el navegador renderice el scatter de Plotly (sólo se verificó el 200 de `/` y el JSON de `/api/points`, no el render visual); el comportamiento del visor si una colección quedara vacía tras un TRUNCATE sin re-reindex (el código lo tolera devolviendo lista vacía, pero no hay evidencia ejecutada de ese caso). Ninguno es bloqueante para esta tarea de carga de datos.

</details>

<details>
<summary>File map</summary>

Versionado (irá al commit):
- `docker-compose.yml` — añade el servicio nuevo `chroma-viewer` (+20 líneas, aditivo); ningún servicio existente alterado.

Scratch / throwaway bajo `.agents/tasks/chroma-viz/` (no versionado):
- `scratch/seed_kpis.sql` — 30 KPIs demo mapeados a columnas reales de `tt_rag.kpi`.
- `scratch/seed_instrumentos.sql` — 21 pares `raw_data`→`instrumento_procesado` en orden de FK.
- `scratch/post_propuestas.ps1` (+ `post_propuestas_result.txt`) — POST de los 21 instrumentos a `/vectorizacion/propuestas`.
- `scratch/viewer/{Dockerfile,app.py,requirements.txt}` — visor FastAPI read-only con PCA 2D + Plotly.
- `id_map.json` — mapeo `inst_NN → id_instrumento` (1:1).

Datos copiados (no versionado): `storage/raw/inst_01..21.md` y `storage/raw/inst_01..21.v1.json`.

Diff completo: `git -C c:\Users\yarel\Documents\indagata\indagata diff docker-compose.yml`.

</details>
