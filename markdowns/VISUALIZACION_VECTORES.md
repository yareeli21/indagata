# Visualización de la base de datos vectorial (ChromaDB)

> Documento explicativo: qué estamos montando, para qué sirve, qué cambios se
> hicieron en el proyecto y por qué cada uno fue necesario. Pensado para
> entender el "para qué" sin ser experta en el tema.

---

## 1. El objetivo

Poder **ver gráficamente, en el navegador, los vectores** de la base de datos
vectorial del proyecto: un "mapa de puntos" donde cada punto es una encuesta o
un KPI vectorizado. Textos parecidos quedan cerca; textos distintos, lejos.

Esto sirve para:

- Comprobar que la vectorización realmente funciona (que hay puntos).
- Explorar visualmente cómo se agrupan los instrumentos y los KPIs.
- Tener una ventana a ChromaDB parecida a lo que DBeaver es para PostgreSQL.

---

## 2. Conceptos clave (rápido)

### ¿Qué es un vector / embedding?
Un modelo de IA (en este proyecto, `paraphrase-multilingual-mpnet-base-v2`)
convierte un texto en una lista de **768 números**. Esa lista es el "vector" o
"embedding". Dos textos con significado parecido producen vectores parecidos.

### ¿Qué es ChromaDB?
La **base de datos vectorial**. Guarda esos vectores y permite buscar los más
parecidos. Corre como un contenedor (`indagata_chromadb`) y persiste sus datos
en el volumen `chromadb_data`. Está encendida todo el tiempo.

### ¿Qué es el "visor"?
Solo una **ventana para mirar** ChromaDB. No guarda ni procesa nada; se conecta
a ChromaDB y dibuja los puntos. Igual que DBeaver no es PostgreSQL, el visor no
es ChromaDB: solo lo muestra.

### Las colecciones (como "tablas" dentro de ChromaDB)
El proyecto define tres, con propósitos distintos:

| Colección            | Qué guarda                                                        | Momento / uso                 |
|----------------------|-------------------------------------------------------------------|-------------------------------|
| `kpis`               | Cada KPI del catálogo vectorizado                                 | Base de referencia            |
| `summary_instrument` | El *summary* del instrumento (preguntas .md + metadatos, SIN respuestas) | **Asociación de KPIs** (hoy)  |
| `instrumentos`       | El instrumento COMPLETO (preguntas + respuestas + metadatos + KPIs) | **RAG final** (más adelante)  |

**Lo que se hizo hoy cubre solo la asociación de KPIs** (`kpis` +
`summary_instrument`). La colección `instrumentos` (RAG completo) queda para
después.

---

## 3. Las dos técnicas de vectorización (por qué están separadas)

Son dos representaciones del mismo instrumento, para dos propósitos:

1. **Asociación de KPIs (Momento 1 — lo de hoy)**
   Se vectoriza el *summary*: el instrumento original en `.md` (solo las
   preguntas) + los metadatos clave del JSON. **No incluye las respuestas**
   (meterían ruido). Ese vector se compara contra la colección `kpis` para
   proponer qué KPIs asociar. Vive en `summary_instrument`.

2. **RAG final (Momento 2 — más adelante)**
   Se vectoriza el JSON completo consolidado: preguntas + todas las respuestas
   + metadatos + KPIs ya asociados. Sirve para que el investigador elija ciertos
   instrumentos y haga investigación sobre ellos. Vive en `instrumentos`.

No se separan en bases distintas, sino en **colecciones distintas dentro de la
misma ChromaDB** (como varias tablas en una misma base).

### ¿Hubo "chunks"? (NO, no en esta fase)
Importante para entender qué se guardó: **cada instrumento se vectorizó como UN
solo punto**, sin trocear. Por eso 21 encuestas = 21 puntos (no más).

- Lo que entra al embedding es el **summary** (un texto condensado): metadatos
  clave + preguntas del `.md`, **sin las respuestas**. Todo ese texto junto
  produce **un único vector de 768 dimensiones** por instrumento. Confirmado en
  el código: `kpi_search.index_summary()` hace un `upsert` con un solo `id`, un
  solo `embedding` y un solo `document` por instrumento.
- **Por qué sin chunks aquí:** el summary es corto y cabe de sobra en una sola
  vectorización. El chunking (partir en trozos) se usa para documentos largos o
  cuando se quieren recuperar fragmentos puntuales. Para comparar "la esencia de
  un instrumento" contra los KPIs, un solo vector representativo es lo correcto.
- **Contraste con el RAG (Momento 2, más adelante):** ahí probablemente SÍ habrá
  chunking, porque el instrumento completo (preguntas + respuestas + metadatos +
  KPIs) es mucho más texto y el RAG necesita recuperar fragmentos específicos. El
  esquema de la BD ya contempla esto con tablas como `documento_vectorizado` y
  `kpi_inferido_chunk`. Pero eso NO se hizo hoy.

Resumen: **asociación de KPIs (hoy) = 1 vector por instrumento, sin chunks.**
**RAG (después) = instrumento completo, probablemente troceado en chunks.**

---

## 4. Por qué hicieron falta tantos cambios

Punto honesto: **la mayoría de los cambios NO fueron por el visor.** El visor es
lo más simple. Al intentar meter datos reales a la base vectorial, se
**destaparon bugs que el proyecto ya tenía** y que impedían que la vectorización
funcionara. Para *ver* los vectores, primero había que lograr *crearlos*.

Analogía: querías ver el agua del grifo, pero la tubería estaba tapada y la
llave no encajaba con el grifo nuevo. Hubo que destapar y cambiar la llave antes
de que cayera el agua. El visor es solo el vaso.

### Cambio A — Fijar `numpy==1.26.4` (bug real del proyecto)
- **Archivo:** `services/analysis-service/requirements.txt`
- **Síntoma:** `import chromadb` reventaba con
  `AttributeError: np.float_ was removed in the NumPy 2.0 release`.
- **Causa:** el `requirements.txt` fijaba `chromadb` pero dejaba `numpy` libre,
  así que pip instaló numpy 2.x. ChromaDB 0.5.0 usa `np.float_`, que numpy 2.0
  eliminó.
- **Por qué era necesario:** sin esto, el analysis-service no podía ni importar
  ChromaDB. La vectorización estaba rota para cualquier uso, no solo la demo.

### Cambio B — Subir el cliente de ChromaDB a `chromadb-client==1.0.0` (bug real del proyecto)
- **Archivo:** `services/analysis-service/requirements.txt`
- **Síntoma:** al conectar, error `Could not connect to tenant default_tenant`;
  el servidor responde `The v1 API is deprecated. Please use /v2 apis`.
- **Causa:** el **cliente** dentro del servicio era `chromadb==0.5.0` (habla la
  API v1), pero el **servidor** ChromaDB es 1.0.0 y eliminó la API v1. Cliente y
  servidor no se entendían (desajuste de versión mayor).
- **La solución exacta:** se usó el paquete **`chromadb-client==1.0.0`** (el
  *thin client* HTTP-only), NO el paquete completo `chromadb==1.0.0`. Motivo: el
  paquete completo 1.0.0 choca con `fastapi==0.115.6` (exige fastapi 0.115.9),
  mientras que el client-only no arrastra esa dependencia y expone el mismo
  `chromadb.HttpClient`, así que **no requirió ningún cambio de código** en
  `chroma_client.py`.
- **Por qué era necesario:** sin alinear el cliente con el servidor, no hay
  conexión posible. Bajar el servidor a una versión vieja habría sido deuda
  técnica; lo correcto es que el cliente también sea 1.0.x.
- **Nota de proceso:** durante el flujo automatizado, este pin se revirtió por
  error y quedó un estado inconsistente en `requirements.txt`
  (`numpy==1.26.4` pero `chromadb==0.5.0`). Se corrigió a mano después, dejando
  el archivo coherente con lo que realmente corre en el contenedor
  (`numpy==1.26.4` + `chromadb-client==1.0.0`), para que una reconstrucción
  futura del servicio NO vuelva a romperse.

> Ambos cambios (A y B) arreglan la vectorización **de verdad**, no son parches
> para la demo. Se habrían topado igual al construir el RAG.

### Cambio C — Agregar el visor de ChromaDB (esto SÍ es por la visualización)
- **Archivo:** `docker-compose.yml` (se añade UN servicio nuevo, no se tocan los
  existentes).
- **Qué hace:** un contenedor que lee ChromaDB y muestra las colecciones como un
  mapa de puntos en el navegador.

### Datos demo cargados (contenido, no estructura)
- ~30 KPIs demo en la tabla `tt_rag.kpi` (el seed original estaba desalineado;
  se adaptó a las columnas reales).
- Las 21 encuestas vectorizadas en `summary_instrument` vía el flujo real
  (`POST /vectorizacion/propuestas`).
- Filas de apoyo en `tt_rag.raw_data` e `tt_rag.instrumento_procesado` (el
  endpoint las requiere).

Todo esto es **demo / desechable**: se puede borrar y recargar con datos reales.

---

## 5. Qué NO se tocó (importante)

- **Ningún código de lógica** de los microservicios (ni `main.py`, ni routers,
  ni servicios, ni `chroma_client.py`).
- **Ningún Dockerfile.**
- El **esquema** de la base de datos (solo se insertaron filas de datos).
- Los **otros microservicios** siguen igual.

El único archivo de servicio modificado es
`services/analysis-service/requirements.txt`, y solo para fijar versiones
(numpy + chromadb). El único otro archivo cambiado es `docker-compose.yml`
(para añadir el visor).

---

## 6. Resumen de archivos modificados

| Archivo                                          | Cambio                                        | Motivo                                  |
|--------------------------------------------------|-----------------------------------------------|-----------------------------------------|
| `services/analysis-service/requirements.txt`     | `numpy==1.26.4` (pin nuevo)                   | el cliente ChromaDB no soporta numpy 2.x |
| `services/analysis-service/requirements.txt`     | `chromadb==0.5.0` → `chromadb-client==1.0.0`  | Alinear cliente con servidor Chroma 1.0 (API v2) |
| `docker-compose.yml`                             | + servicio visor (contenedor nuevo)           | Ver los vectores en el navegador        |

Commits en la rama `refactorizacion-microservicios` (sin push):
- `0a42816` — `docker-compose.yml`: servicio visor standalone.
- `f54a085` — `requirements.txt`: pins numpy + chromadb-client (corrección del
  estado inconsistente que dejó el proceso automatizado).

---

## 7. Cómo borrar los datos demo y recargar con datos reales (a futuro)

Cuando tengas los instrumentos/KPIs reales, puedes vaciar lo demo y recargar.
(Comandos de referencia; ajustar nombres según corresponda.)

### Vaciar las tablas de Postgres
```sql
-- dentro de psql del contenedor postgres, base indagata_db
TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE;
TRUNCATE tt_rag.instrumento_procesado RESTART IDENTITY CASCADE;
TRUNCATE tt_rag.raw_data RESTART IDENTITY CASCADE;
```

### Borrar las colecciones de ChromaDB
Eliminar las colecciones `kpis` y `summary_instrument` por la API v2 de Chroma
(host `localhost:8008`) o reiniciando desde el visor/cliente. Al volver a
vectorizar, se recrean solas.

### Recargar
1. Sembrar los KPIs reales en `tt_rag.kpi`.
2. Llamar `POST /vectorizacion/kpis/reindex` → repuebla `kpis`.
3. Por cada instrumento real: crear su fila en `instrumento_procesado` y llamar
   `POST /vectorizacion/propuestas` → repuebla `summary_instrument`.

---

## 8. Estado del RAG (las tres piezas)

| Pieza                     | Dónde vive                        | Estado |
|---------------------------|-----------------------------------|--------|
| LLM (`llama3.2:3b`)       | contenedor `ollama`, volumen `ollama_data` | listo (GPU) |
| Modelo de embeddings      | analysis-service, volumen `hf_cache` | descargado y persistente |
| Base vectorial (ChromaDB) | contenedor `chromadb`, volumen `chromadb_data` | funcionando |

---

## 9. Pendientes conocidos (no son parte de esto)

- **Frontend**: su build (`npm ci`) falla; no se necesita para la visualización.
- **storage-service** y **visualization-service**: son *stubs* (solo responden
  `/health`), pendientes de lógica real.
- **RAG completo (colección `instrumentos`)**: Momento 2, para más adelante.

---

*Generado como apoyo para entender la visualización de la base vectorial del
proyecto Indagata. Los datos cargados son demostrativos y reemplazables.*
