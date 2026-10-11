# Capítulo: Desarrollo

> Reporte técnico del capítulo de Desarrollo de la plataforma Indagata. A
> diferencia del capítulo de Diseño —donde se justificaron las decisiones de
> arquitectura—, aquí se documenta **cómo se construyó efectivamente el
> sistema**, describiendo los artefactos reales que lo componen (archivos de
> configuración, imágenes de contenedor, servicios y sus endpoints). El capítulo
> se redacta de forma incremental; cada subtema corresponde a una pieza concreta
> de la implementación.

---

## 1. Dockerización y orquestación de contenedores

Toda la plataforma Indagata se ejecuta como un conjunto de contenedores Docker
orquestados mediante Docker Compose. Esta decisión responde a la naturaleza del
sistema: una arquitectura de microservicios en la que coexisten servicios
escritos en Python, un frontend en Node.js, una base de datos relacional, una
base de datos vectorial, un almacén en memoria y un motor de modelos de lenguaje.
La contenerización permite que cada componente se construya, aísle y despliegue
de forma reproducible, con sus propias dependencias, y que todo el entorno se
levante con un único comando.

En esta sección se documenta, en orden, la estrategia de contenerización de los
servicios (los *Dockerfiles*), la orquestación del conjunto (el
`docker-compose.yml`), la gestión de la configuración mediante variables de
entorno y los mecanismos de persistencia y conectividad entre contenedores.

### 1.1 Estrategia general de contenerización

La definición de la infraestructura se concentró en el directorio
`infrastructure/`, que agrupa los *Dockerfiles* de cada servicio (en
`infrastructure/docker/`) y los scripts de la base de datos (en
`infrastructure/postgres/`). En la raíz del repositorio se ubican el archivo de
orquestación `docker-compose.yml`, la plantilla de variables de entorno
`.env.example` y el archivo `.dockerignore` que controla el contexto de
construcción.

Cada microservicio del backend cuenta con su propio *Dockerfile*, nombrado según
el servicio que construye (por ejemplo, `Dockerfile.api-gateway`,
`Dockerfile.analysis-service`), lo que permite personalizar las dependencias de
cada imagen sin acoplarlas entre sí. Todos los servicios de backend comparten
una misma base tecnológica —Python 3.12 sobre la imagen oficial
`python:3.12-slim`— y siguen un patrón de construcción común, descrito en el
siguiente apartado.

En total, el sistema se compone de **doce contenedores**: seis microservicios de
backend, el frontend, cuatro servicios de infraestructura (PostgreSQL, Ollama,
ChromaDB y Redis) y un visor auxiliar de vectores.

### 1.2 Construcción de imágenes mediante *multi-stage builds*

Todos los *Dockerfiles* de los microservicios de Python se construyeron con el
patrón de **compilación en múltiples etapas** (*multi-stage build*). Este patrón
separa el proceso en dos fases: una etapa de *construcción* (`base`), en la que
se instalan las herramientas de compilación del sistema (como `gcc`, `g++` y
`libpq-dev`) y se instalan las dependencias de Python declaradas en el archivo
`requirements.txt`; y una etapa *final*, que parte de una imagen limpia de
`python:3.12-slim` y copia únicamente las librerías ya instaladas desde la etapa
anterior, descartando las herramientas de compilación.

El beneficio de este enfoque es que la imagen final no arrastra los compiladores
ni los archivos intermedios necesarios solo durante la instalación, lo que
reduce de manera significativa su tamaño y su superficie de ataque. En la etapa
final únicamente se instalan las librerías de ejecución estrictamente necesarias
—por ejemplo, `libpq5` para la conexión a PostgreSQL mediante *psycopg*—.

El patrón común de estos *Dockerfiles* se ilustra con el del servicio de
instrumentos:

```dockerfile
# Etapa de construcción: instala dependencias con herramientas de compilación
FROM python:3.12-slim as base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY services/instrument-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Etapa final: imagen limpia sin herramientas de compilación
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin
COPY services/instrument-service/ ./
COPY shared/ ./shared/
RUN mkdir -p /app/storage/raw /app/storage/json /app/storage/sav /app/storage/clean /app/storage/temp
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

En todos los casos, el contexto de construcción es la raíz del proyecto, de modo
que cada imagen copia tanto el código del servicio (desde `services/<nombre>/`)
como el módulo común `shared/`, garantizando que la lógica compartida —modelos,
esquemas, autenticación y acceso a datos— quede disponible dentro del
contenedor. Como punto de arranque, cada servicio ejecuta el servidor **Uvicorn**
sobre su aplicación FastAPI, escuchando en todas las interfaces (`0.0.0.0`) y en
el puerto propio del servicio, declarado explícitamente con la instrucción
`EXPOSE`.

Aunque los siete *Dockerfiles* comparten esta estructura, cada uno incorpora las
particularidades que exige el servicio que construye. La siguiente tabla resume
las diferencias relevantes:

| Imagen | Base | Dependencias de sistema (etapa final) | Particularidad |
|--------|------|----------------------------------------|----------------|
| `api-gateway` | python:3.12-slim | `libpq5`, `curl` | Define un `HEALTHCHECK` que consulta `/health` con `curl` |
| `instrument-service` | python:3.12-slim | `libpq5` | Crea los directorios de almacenamiento de archivos |
| `analysis-service` | python:3.12-slim | `libpq5`, `libgomp1` | Añade `g++` en la construcción y `libgomp1` para *torch/sentence-transformers* |
| `metadata-service` | python:3.12-slim | `libpq5` | Imagen mínima, sin almacenamiento local |
| `storage-service` | python:3.12-slim | — | Solo `gcc` en construcción; prepara directorios de artefactos |
| `visualization-service` | python:3.12-slim | `libpq5` | Instala *torch* desde el índice CPU de PyTorch |
| `frontend` | node:20-alpine | — | Construcción Node.js; instala dependencias con `npm ci` |

Dos de estas particularidades merecen comentario por su impacto técnico.

**Servicio de análisis.** Al ser el servicio que ejecuta la vectorización, su
imagen requiere compilar y ejecutar las librerías de aprendizaje automático
(*sentence-transformers*, que depende de *torch*). Por ello, su etapa de
construcción añade el compilador `g++`, y la etapa final instala la librería de
sistema `libgomp1` (soporte de OpenMP), necesaria en tiempo de ejecución para
esas librerías.

**Servicio de visualización.** Este servicio también usa *torch* para generar
*embeddings*, pero únicamente para textos cortos que se procesan con eficiencia
en CPU. Para evitar que la instalación arrastre los *wheels* de CUDA de NVIDIA
—que añaden alrededor de 2.5 GB a la imagen—, el *Dockerfile* instala
deliberadamente la versión de *torch* para CPU desde el índice oficial de
PyTorch antes del resto de dependencias:

```dockerfile
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.2
RUN pip install --no-cache-dir -r requirements.txt
```

Según la nota documentada en el propio *Dockerfile*, esta optimización reduce la
imagen de aproximadamente 3 GB a cerca de 800 MB y el tiempo de construcción de
unos 15 minutos a unos 3. La aceleración por GPU queda reservada al contenedor de
Ollama, que es quien ejecuta el modelo de lenguaje.

**Frontend.** A diferencia de los servicios de Python, el frontend se construye
sobre la imagen `node:20-alpine`. Su etapa de construcción instala las
dependencias de Node.js de forma determinista con `npm ci` (que respeta el
*lockfile*), y la etapa final copia esas dependencias junto con el código fuente.
La imagen expone el puerto 3000 y arranca el servidor de desarrollo de Vite.

### 1.3 Control del contexto de construcción (`.dockerignore`)

Para evitar que archivos innecesarios o sensibles se incluyan en el contexto que
Docker envía al construir las imágenes, se definió un archivo `.dockerignore` en
la raíz del proyecto. Este archivo excluye, entre otros, los metadatos de Git,
los artefactos de Python (`__pycache__`, entornos virtuales), las dependencias de
Node (`node_modules`), la configuración de los editores, la documentación, los
propios *Dockerfiles* y archivos de Compose, y —de manera relevante para la
seguridad— los archivos de variables de entorno (`.env` y sus variantes).

Dos exclusiones tienen un impacto directo en el rendimiento de la construcción:
los directorios de persistencia `storage/` y `chromadb/`, que pueden contener
archivos de gran tamaño, se excluyen del contexto para no ralentizar el proceso.
Esos datos se montan en tiempo de ejecución mediante volúmenes, como se describe
más adelante, en lugar de hornearse dentro de la imagen.

### 1.4 Orquestación con Docker Compose

El archivo `docker-compose.yml`, ubicado en la raíz del repositorio, orquesta la
ejecución conjunta de todos los contenedores. Define los servicios, el orden en
que deben arrancar, la red que los comunica, los volúmenes de persistencia y la
configuración que recibe cada uno. Los servicios se agrupan conceptualmente en
tres bloques: infraestructura, microservicios y componentes auxiliares.

**Servicios de infraestructura.** Se despliegan a partir de imágenes oficiales
publicadas en registros públicos, sin necesidad de construcción propia:

- **PostgreSQL** (`postgres:16-alpine`): base de datos relacional del sistema.
  Monta el directorio de scripts de inicialización en
  `/docker-entrypoint-initdb.d`, de modo que el esquema y los datos semilla se
  crean automáticamente en el primer arranque, y expone el directorio de
  migraciones. Define una comprobación de salud (`pg_isready`) de la que dependen
  los microservicios.
- **Ollama** (`ollama/ollama:latest`): motor que sirve el modelo de lenguaje de
  forma local. Se configura con acceso a la GPU mediante el *driver* de NVIDIA y
  con la variable `OLLAMA_KEEP_ALIVE=-1`, que mantiene el modelo cargado en
  memoria de la GPU indefinidamente para evitar el costo de recarga en cada
  consulta.
- **ChromaDB** (`chromadb/chroma:latest`): base de datos vectorial. Internamente
  escucha en el puerto 8000, que se publica en el puerto 8008 del host para no
  colisionar con los puertos de los microservicios.
- **Redis** (`redis:7-alpine`): almacén en memoria para caché y datos de sesión,
  con su propia comprobación de salud (`redis-cli ping`).

**Microservicios y frontend.** Se construyen a partir de los *Dockerfiles*
descritos, indicando en cada caso el contexto de construcción (la raíz del
proyecto) y la ruta del *Dockerfile* correspondiente. Cada servicio declara sus
dependencias de arranque mediante la cláusula `depends_on`; por ejemplo, los
servicios que acceden a la base de datos esperan a que PostgreSQL supere su
comprobación de salud (`condition: service_healthy`) antes de iniciarse, y el
servicio de análisis espera además a que Ollama y ChromaDB estén en marcha. Este
encadenamiento garantiza que ningún servicio intente conectarse a una dependencia
que todavía no está lista.

Cada contenedor publica su puerto interno en el mismo puerto del host, siguiendo
el mapa de puertos del sistema:

| Contenedor | Imagen / construcción | Puerto host → interno |
|------------|-----------------------|-----------------------|
| `indagata_postgres` | postgres:16-alpine | 5432 → 5432 |
| `indagata_ollama` | ollama/ollama:latest | 11434 → 11434 |
| `indagata_chromadb` | chromadb/chroma:latest | 8008 → 8000 |
| `indagata_redis` | redis:7-alpine | 6379 → 6379 |
| `indagata_api_gateway` | Dockerfile.api-gateway | 8000 → 8000 |
| `indagata_instrument_service` | Dockerfile.instrument-service | 8001 → 8001 |
| `indagata_analysis_service` | Dockerfile.analysis-service | 8002 → 8002 |
| `indagata_metadata_service` | Dockerfile.metadata-service | 8003 → 8003 |
| `indagata_storage_service` | Dockerfile.storage-service | 8004 → 8004 |
| `indagata_visualization_service` | Dockerfile.visualization-service | 8005 → 8005 |
| `indagata_frontend` | Dockerfile.frontend | 3000 → 3000 |
| `indagata_chroma_viewer` | infrastructure/chroma-viewer | 8085 → 8000 |

Todos los servicios se declaran con la política de reinicio
`restart: unless-stopped`, de modo que Docker los vuelva a levantar
automáticamente si fallan, salvo que se detengan de forma explícita.

**Componente auxiliar.** Además de los servicios funcionales, la orquestación
incluye un **visor de vectores** (`chroma-viewer`), una herramienta web de solo
lectura que proyecta en dos dimensiones los *embeddings* almacenados en ChromaDB,
coloreándolos por colección. Es un componente autónomo, de apoyo al desarrollo y
la verificación, cuyo código se versiona en `infrastructure/chroma-viewer/`.

### 1.5 Configuración mediante variables de entorno

La configuración del sistema se externalizó por completo mediante variables de
entorno, siguiendo el principio de separar la configuración del código. El
archivo `.env.example`, versionado en el repositorio, sirve como plantilla
documentada de todas las variables disponibles; cada despliegue crea a partir de
él su propio archivo `.env` con los valores concretos, el cual se excluye del
control de versiones y del contexto de construcción por razones de seguridad.

Dentro del `docker-compose.yml`, estas variables se inyectan en cada contenedor
con la sintaxis `${VARIABLE:-valor_por_defecto}`, que toma el valor del entorno
si está definido o recurre a un valor por defecto en caso contrario. Las
variables se agrupan por propósito: credenciales y parámetros de la base de datos,
clave secreta de la aplicación, configuración del modelo de lenguaje (dirección
de Ollama y nombre del modelo), rutas de almacenamiento, direcciones internas de
los servicios y parámetros del frontend y de Redis.

Un aspecto importante de seguridad es que la clave secreta (`SECRET_KEY`),
empleada para firmar y validar los tokens JWT, se comparte entre el API Gateway
y los demás microservicios que deben validar esos tokens. La orquestación lo hace
explícito, inyectando la misma variable en todos los servicios implicados, de
modo que un token emitido por el *gateway* pueda ser verificado por cualquier
servicio del backend.

### 1.6 Red interna y comunicación entre contenedores

Todos los contenedores se conectan a una red de tipo *bridge* definida en la
orquestación, denominada `indagata_network`. Al compartir esta red, los
servicios se descubren entre sí por el **nombre del servicio** en lugar de
direcciones IP fijas: por ejemplo, el API Gateway alcanza al servicio de análisis
mediante la dirección `http://analysis-service:8002`, y todos los servicios
acceden a la base de datos usando `postgres` como nombre de host. Esta resolución
por nombre, que proporciona el DNS interno de Docker, desacopla la configuración
de la topología de red concreta y es lo que hace que las direcciones internas
declaradas en las variables de entorno funcionen de forma transparente.

Conviene distinguir entre los puertos internos y los publicados. Dentro de la red,
los servicios se comunican por sus puertos internos (por ejemplo, ChromaDB en el
8000); los mapeos de puertos hacia el host solo son necesarios para el acceso
externo —desde el navegador o desde herramientas de desarrollo— y es ahí donde se
resuelven las colisiones, como la de ChromaDB, que se publica en el 8008 para no
chocar con el servicio de instrumentos.

### 1.7 Persistencia mediante volúmenes

Dado que los contenedores son efímeros por naturaleza, los datos que deben
sobrevivir a su reinicio o recreación se gestionan mediante **volúmenes**. La
orquestación emplea dos modalidades complementarias:

- **Volúmenes nombrados**, gestionados por Docker, para los datos de las bases y
  cachés: `postgres_data` (datos de PostgreSQL), `ollama_data` (modelos
  descargados por Ollama), `chromadb_data` (índices vectoriales), `redis_data`
  (datos de Redis) y `hf_cache` (caché del modelo de *embeddings* de
  *sentence-transformers*). Este último se comparte entre los servicios de
  análisis y de visualización para evitar descargar el modelo —de varios cientos
  de megabytes— en cada reconstrucción o recreación del contenedor.
- **Montajes de enlace** (*bind mounts*) hacia directorios del proyecto, para el
  código fuente y los artefactos de trabajo. Cada microservicio monta su propio
  directorio de código (`./services/<nombre>:/app`) y el módulo compartido
  (`./shared:/app/shared`), lo que permite que los cambios en el código se
  reflejen dentro del contenedor sin reconstruir la imagen durante el desarrollo.
  Asimismo, los servicios que manejan archivos montan el directorio `./storage`,
  y la inicialización de PostgreSQL monta los directorios de scripts de
  `infrastructure/postgres/`.

Esta separación garantiza que la información crítica —datos de usuarios,
instrumentos cargados, vectores e índices— persista de forma independiente del
ciclo de vida de los contenedores, mientras que el montaje del código fuente
agiliza el ciclo de desarrollo.

---

## 2. Microservicios implementados

El backend de Indagata se construyó como un conjunto de **seis microservicios**
independientes, cada uno responsable de una parte acotada del dominio. Todos
comparten la misma base tecnológica —Python 3.12 y el framework FastAPI, servidos
con Uvicorn— y una estructura homogénea: un punto de entrada (`main.py`) que crea
la aplicación, configura el registro de eventos (*logging*) y el *middleware* de
CORS, define un gestor de ciclo de vida (*lifespan*) para las tareas de arranque
y agrupa los *endpoints* en enrutadores (*routers*) por función. Cada servicio
escucha en su propio puerto y expone, como mínimo, un *endpoint* `GET /health`
para verificar su disponibilidad.

Un detalle de implementación común a todos los servicios es la resolución del
paquete compartido `shared`. Dentro de los contenedores, `shared/` se copia junto
al código del servicio, de modo que `import shared` resuelve de forma directa.
Para permitir además la ejecución local fuera de Docker, cada `main.py` detecta si
el paquete no está disponible y, en ese caso, añade la raíz del repositorio a la
ruta de búsqueda de módulos. Así, un mismo servicio puede levantarse tanto con
`docker compose up` como con `uvicorn main:app` desde su directorio, sin cambios
en el código.

Esta sección documenta cada microservicio como **componente del sistema**: su
responsabilidad, su estructura interna y las operaciones que ofrece. El detalle
exhaustivo de los *endpoints* (rutas, parámetros y respuestas) se aborda en la
sección 3.

### 2.1 Visión general y comunicación entre servicios

La comunicación entre servicios se realiza mediante peticiones HTTP sobre una API
de tipo REST, con JSON como formato de intercambio. Cada servicio corre en su
propio contenedor y alcanza a los demás por el nombre de servicio dentro de la red
interna de Docker (por ejemplo, `http://analysis-service:8002`), nunca por
direcciones fijas. La siguiente tabla resume los servicios, su puerto y su
responsabilidad principal:

| Servicio | Puerto | Responsabilidad principal |
|----------|--------|---------------------------|
| API Gateway | 8000 | Autenticación JWT y proxy transparente al resto de servicios |
| Instrument Service | 8001 | Carga, consulta, borrado y estandarización de instrumentos |
| Analysis Service | 8002 | Vectorización, inferencia y cálculo de KPIs, espacio vectorial y grafo de recomendación |
| Metadata Service | 8003 | Metadatos Dublin Core, metadatos específicos y enriquecimiento |
| Storage Service | 8004 | Autoridad de artefactos: persistencia versionada de JSON y binarios |
| Visualization Service | 8005 | Núcleo RAG: indexado por investigación y chat fundamentado con Ollama |

Respecto a etapas previas del desarrollo, dos cambios estructurales son
relevantes y se reflejan en todo el capítulo. Primero, el **API Gateway dejó de
ser un simple punto de autenticación** para convertirse en un *proxy transparente*
real: hoy reenvía las peticiones del frontend a los servicios internos. Segundo,
los servicios de **almacenamiento y visualización dejaron de ser componentes
preliminares** (*stubs*): el de almacenamiento es ya la autoridad de artefactos
del sistema, y el de visualización implementa el flujo RAG completo. Esto se
documenta en los apartados correspondientes.

### 2.2 Patrón de enrutamiento: el API Gateway como proxy transparente

El API Gateway (puerto 8000) es la única puerta HTTP del frontend. Cumple dos
funciones: concentrar la **autenticación** mediante JWT y actuar como **proxy
transparente** hacia los microservicios internos. En el estado actual, el
*gateway* organiza su lógica en dos módulos: `app/auth/`, con los *endpoints* de
autenticación (`/auth/login`, `/auth/me`, `/auth/register`), y `proxy/`, con el
reenvío de peticiones.

El proxy reenvía el *path* **tal cual**, sin traducir segmentos ni idiomas, al
servicio que corresponde según el prefijo de la ruta, y devuelve el *status* y el
cuerpo del *upstream* de forma transparente —sin envolverlos en una estructura
adicional—, de modo que el frontend recibe el JSON de dominio y el código HTTP
reales (incluidos 401, 404, 409 o 422). Al reenviar, el proxy conserva la cabecera
`Authorization` para que el JWT viaje al servicio interno, y descarta las cabeceras
`host` y `content-length`, que el cliente HTTP recalcula. Los prefijos que se
enrutan por el *gateway* son:

| Prefijo | Servicio destino | Métodos |
|---------|------------------|---------|
| `/instrumentos/*` | instrument-service :8001 | GET, POST, DELETE |
| `/almacenamiento/*` | storage-service :8004 | GET, POST |
| `/rag/*` | visualization-service :8005 | POST (`/rag/chat` por *streaming*) |
| `/api/metadata/*` | metadata-service :8003 | GET, POST, DELETE |
| `/api/enrichment/*` | metadata-service :8003 | GET, POST, DELETE |

El corazón del *proxy* es una única función de reenvío, común a todos los
prefijos, que preserva el cuerpo, los parámetros de consulta y la cabecera de
autorización, y devuelve la respuesta del *upstream* sin envolверla:

```python
async def proxy_request(service, path, request, method) -> Response:
    url = f"{SERVICES[service]}{path}"
    headers = _headers_reenvio(request)      # conserva Authorization; quita host/content-length
    body = await request.body()
    async with httpx.AsyncClient() as client:
        upstream = await client.request(method, url, content=body, headers=headers,
                                        params=request.query_params,
                                        timeout=httpx.Timeout(connect=5.0, read=120.0, ...))
    return Response(content=upstream.content,
                    status_code=upstream.status_code,            # status real del upstream
                    media_type=upstream.headers.get("content-type"))
```

Dos aspectos de la implementación merecen mención. El *endpoint* de chat RAG
(`/rag/chat`) se trata de forma especial: en lugar de bufferizar la respuesta, el
proxy la **transmite como flujo** (*streaming*) preservando el tipo
`text/event-stream`, lo que permite al frontend recibir la respuesta del modelo
token a token conforme se genera. Por otra parte, algunos servicios —el
*analysis-service* en particular— **no se enrutan por el gateway**: el frontend los
consume directamente, lo que se detalla en el apartado 2.4.

### 2.3 Instrument Service: carga, consulta y estandarización

El servicio de instrumentos (puerto 8001) gestiona el ciclo de vida de los
instrumentos desde su carga hasta su estandarización. Su lógica se organiza en
cinco enrutadores (`health`, `upload`, `delete`, `list` y `standardize`) y una
capa interna de servicios, *parsers* por familia de instrumento y lógica de
estandarización. Al arrancar, prepara el directorio de almacenamiento de archivos
crudos. Las operaciones que ofrece son:

- **Carga** (`POST /instrumentos/upload`): recibe el archivo respondido y,
  opcionalmente, el instrumento original sin respuestas; identifica el tipo de
  cada archivo, lo enruta a su familia de *parser* (tabular para encuestas,
  documental para entrevistas y pruebas), lo parsea para conocer su estructura,
  delega su almacenamiento y registra el instrumento en las tablas `raw_data` e
  `instrumento_procesado` con estado inicial `recibido`.
- **Consulta** (`GET /instrumentos`, `GET /instrumentos/{id}`): lista todos los
  instrumentos o recupera uno por su identificador, resolviendo el JSON de dominio
  de forma defensiva.
- **Catálogo de KPIs** (`GET /instrumentos/kpis/catalogo`): devuelve la unión
  ordenada de las pistas de KPI de todos los instrumentos.
- **Estandarización** (`POST /instrumentos/{id}/estandarizar/preview` y
  `POST /instrumentos/{id}/estandarizar`): previsualiza los tipos de pregunta
  detectados sin persistir y, tras la confirmación del usuario, estandariza el
  instrumento generando el JSON de dominio.
- **Borrado** (`DELETE /instrumentos/{id}`): elimina un instrumento y sus archivos,
  aplicando la regla de propiedad descrita más adelante.

El control de acceso de este servicio es representativo del modelo del sistema:
todas las operaciones exigen rol de **investigador** o **administrador**, y la
regla fina de propiedad en el borrado la aplica la capa de servicio —un
investigador solo puede borrar lo que él mismo subió; un administrador, cualquier
instrumento—.

### 2.4 Analysis Service: vectorización, KPIs y grafo de recomendación

El servicio de análisis (puerto 8002) es el componente de inteligencia del
sistema y, con diferencia, el más rico en funcionalidad. Se apoya en la base
vectorial ChromaDB, en el modelo de *embeddings* de *sentence-transformers* y en
el modelo de lenguaje servido por Ollama. Organiza su lógica en seis enrutadores,
que agrupan cuatro grandes capacidades:

- **Vectorización e inferencia de KPIs** (`vectorizacion`): materializa el flujo
  de dos pasos —proponer y confirmar— que asocia KPIs a un instrumento por
  similitud semántica. Incluye además la reindexación del catálogo de KPIs en
  Chroma y la inspección del *embedding* de un instrumento. Este flujo se
  documenta en detalle en la sección sobre indexación y consulta.
- **Catálogo de KPIs** (`kpis`): expone, de solo lectura, el catálogo completo de
  KPIs de la base de datos para la pantalla correspondiente del frontend.
- **Cálculo de KPIs** (`kpi_calculo`): una vez confirmados los KPIs de un
  instrumento, permite calcular su **valor numérico real**. Un primer *endpoint*
  envía la fórmula del KPI a Ollama para que extraiga las variables de entrada
  como JSON; un segundo recibe los valores capturados por el investigador, calcula
  el nivel de un **semáforo** (favorable, aceptable o desfavorable) según la
  polaridad del indicador y persiste el resultado con una interpretación en
  español. Si Ollama no está disponible o la fórmula es narrativa, el KPI se marca
  como *descriptivo* y se omite del cálculo automático, de forma controlada.
- **Espacio vectorial** (`espacio`): devuelve, de solo lectura, una proyección en
  dos dimensiones (mediante PCA) de las colecciones de *embeddings* para
  visualizar el espacio vectorial en el frontend.
- **Grafo de recomendación** (`grafo`): construye un grafo del acervo en el que
  los instrumentos son nodos y las aristas representan KPIs compartidos, y ofrece
  recomendaciones en tiempo real combinando similitud semántica y solape de KPIs
  (índice de Jaccard). Si Chroma no responde, degrada de forma elegante a
  recomendación basada solo en KPIs.

A diferencia de los demás servicios, el *analysis-service* **no se enruta a través
del API Gateway**: el frontend lo consume directamente mediante su URL. Las rutas
de catálogo de KPIs, espacio vectorial, cálculo y grafo siguen este patrón de
acceso directo.

### 2.5 Metadata Service: Dublin Core y metadatos específicos

El servicio de metadatos (puerto 8003) gestiona toda la información descriptiva de
los instrumentos. Al iniciarse, verifica e inicializa la conexión con la base de
datos. Cubre dos responsabilidades:

- **Metadatos Dublin Core** (`metadata`): registra y consulta los trece campos del
  estándar Dublin Core. Seis se **autocompletan a partir de datos ya conocidos del
  instrumento** —el creador (el usuario), el editor (el nombre de la aplicación),
  el tipo (el del instrumento), el formato (la extensión del archivo), la fecha (la
  del registro) y el idioma (español)— y los otros siete los **provee el usuario**
  (título, materia, descripción, cobertura, derechos, fuente y relación). Conviene
  aclarar que el autocompletado es un simple relleno con valores derivados, **no una
  inferencia ni una recomendación**: el sistema no sugiere contenidos de metadatos.
  Un *endpoint* de inicialización precarga esos campos automáticos para el
  formulario del frontend. El registro es **inmutable**: un segundo intento
  devuelve un conflicto (409).
- **Metadatos específicos por tipo** (`specific`): registra, mediante *upsert*, los
  metadatos propios de cada tipo de instrumento (encuesta, entrevista o prueba
  estandarizada), validando el tipo recibido contra el real del instrumento y
  coaccionando cada campo a su formato (entero, JSON o texto). A diferencia de
  Dublin Core, estos sí son editables: una segunda llamada actualiza la fila.

Las rutas de este servicio se exponen al frontend a través del API Gateway bajo el
prefijo `/api/metadata/*`, que se reenvía sin alteración.

### 2.6 Storage Service: autoridad de artefactos

El servicio de almacenamiento (puerto 8004) es la **autoridad de artefactos** del
sistema: centraliza la persistencia de los archivos que produce el *pipeline*. En
el estado actual ya no es un componente preliminar, sino un servicio funcional que
recibe un artefacto, decide dónde guardarlo según su tipo (ruteo por tipo:
`metadata`, `analysis`, `raw`, `sav`, `temp`), lo escribe de forma atómica con una
**clave versionada estable** y devuelve dónde quedó guardado. Al arrancar, prepara
los directorios de almacenamiento y un índice de artefactos.

Sus operaciones (bajo el prefijo `/almacenamiento`) permiten guardar un JSON de
metadatos o de análisis, guardar un binario (con un límite de 50 MB por archivo),
recuperar un artefacto por su clave —opcionalmente por versión— y listar o filtrar
los artefactos registrados. Cada escritura incrementa la versión del artefacto y
queda registrada en un índice con su ruta, tamaño y marca de tiempo, de modo que
el historial de versiones de cada instrumento sea trazable.

### 2.7 Visualization Service: núcleo RAG

El servicio de visualización (puerto 8005) alberga el **núcleo RAG** del sistema y
constituye el centro de la demostración funcional. También dejó de ser un
componente preliminar: hoy implementa el flujo completo de recuperación aumentada
por generación, apoyándose en ChromaDB para la recuperación, en
*sentence-transformers* para los *embeddings* y en Ollama para la generación. Al
arrancar, prepara sus directorios de trabajo. Ofrece dos operaciones principales
bajo el prefijo `/rag`:

- **Indexado por investigación** (`POST /rag/index`): recupera los artefactos JSON
  de los instrumentos de una investigación, extrae su texto, lo fragmenta en
  *chunks*, genera sus *embeddings* y los almacena —junto con metadatos de
  procedencia (título, tipo, investigador, KPIs)— en una colección de Chroma
  propia de esa investigación. Admite reindexar desde cero.
- **Chat fundamentado** (`POST /rag/chat`): ante una pregunta en lenguaje natural,
  vectoriza la consulta, recupera de Chroma los fragmentos más relevantes de la
  investigación, construye un *prompt* con ese contexto y genera la respuesta con
  Ollama, citando como fuentes los instrumentos de los que proviene la evidencia.
  La respuesta puede entregarse como flujo de eventos (*SSE*), emitiendo la
  respuesta token a token seguida de las fuentes, o como un único JSON.

Una decisión de diseño relevante es que el modelo de lenguaje a usar es
**configurable por petición**: el chat acepta un parámetro de modelo, y si no se
indica recurre al modelo por defecto definido en la configuración. Esto habilita
la experimentación con distintos modelos de Ollama, que se aborda en el subtema de
consulta con el modelo.

---

## 3. Endpoints de cada microservicio

Esta sección documenta la interfaz HTTP de cada microservicio: las rutas que
expone, el método que admiten y su propósito. Las convenciones comunes a todos
los servicios son las siguientes:

- Todos exponen `GET /health`, que devuelve `{"status": "ok", "service": "..."}`
  y es el que consulta Docker para verificar la disponibilidad del contenedor.
- El intercambio de datos usa JSON, salvo las cargas de archivos, que se envían
  como formulario multiparte (*multipart/form-data*).
- Las rutas que exigen autenticación esperan el token JWT en la cabecera
  `Authorization: Bearer <token>`. El rol requerido se indica en cada caso.
- Las rutas marcadas como de **acceso directo** las consume el frontend llamando
  al servicio por su URL, sin pasar por el API Gateway; el resto se alcanzan a
  través del *gateway*, que reenvía la petición de forma transparente.

Para cada ruta de servicio interno se indica, además de su ruta propia, el prefijo
público por el que el *gateway* la expone al frontend cuando aplica.

### 3.1 API Gateway (puerto 8000)

El *gateway* expone sus propios *endpoints* de autenticación y, además, reenvía
por *proxy* los prefijos de los demás servicios (documentados en el apartado 2.2).
Sus *endpoints* propios son:

| Método | Ruta | Propósito | Acceso |
|--------|------|-----------|--------|
| GET | `/health` | Estado del servicio | Público |
| POST | `/auth/login` | Valida correo y contraseña; devuelve un JWT y los datos del usuario | Público |
| GET | `/auth/me` | Devuelve los datos del usuario asociado al token | Autenticado |
| POST | `/auth/register` | Da de alta un usuario (investigador o administrador) | Solo administrador |

El cuerpo del *login* es `{email, password}`; la respuesta incluye
`access_token`, el tipo de token (`bearer`) y el objeto del usuario. El alta de
usuario recibe `{nombre, email, password, rol}`, con la contraseña de al menos
seis caracteres y el rol por defecto `investigador`; la contraseña se almacena
cifrada con *bcrypt*.

### 3.2 Instrument Service (puerto 8001)

Todas las operaciones de dominio exigen rol de **investigador** o
**administrador**. Se exponen al frontend a través del *gateway* bajo el prefijo
`/instrumentos/*`.

| Método | Ruta | Propósito | Acceso |
|--------|------|-----------|--------|
| GET | `/health` | Estado del servicio | Público |
| POST | `/instrumentos/upload` | Sube el archivo respondido y, opcionalmente, el original; identifica el tipo, parsea y registra el instrumento (estado `recibido`) | Investigador / Admin |
| GET | `/instrumentos` | Lista todos los instrumentos | Investigador / Admin |
| GET | `/instrumentos/{id}` | Devuelve un instrumento por su `id_crudo` (404 si no existe) | Investigador / Admin |
| GET | `/instrumentos/kpis/catalogo` | Unión ordenada de las pistas de KPI de todos los instrumentos | Investigador / Admin |
| POST | `/instrumentos/{id}/estandarizar/preview` | Previsualiza los tipos de pregunta detectados, sin persistir | Investigador / Admin |
| POST | `/instrumentos/{id}/estandarizar` | Estandariza con los tipos confirmados y persiste el JSON de dominio | Investigador / Admin |
| DELETE | `/instrumentos/{id}` | Elimina el instrumento y sus archivos (regla de propiedad) | Investigador (propio) / Admin (cualquiera) |

La carga (`/upload`) se envía como formulario multiparte con el archivo
respondido, el campo `tipo_instrumento` (`encuesta`, `entrevista` o
`prueba_estandarizada`) y, de forma opcional, el archivo original. El borrado
aplica la regla de propiedad en la capa de servicio: un investigador que intenta
borrar un instrumento ajeno recibe un 403.

### 3.3 Analysis Service (puerto 8002)

Las operaciones exigen un usuario autenticado. A diferencia del resto, el
*analysis-service* es de **acceso directo**: el frontend lo consume por su URL, no
a través del *gateway*. Sus *endpoints* se agrupan por capacidad.

**Vectorización e inferencia de KPIs** (prefijo `/vectorizacion`):

| Método | Ruta | Propósito |
|--------|------|-----------|
| POST | `/vectorizacion/propuestas` | Paso 1: vectoriza el *summary* del instrumento y propone KPIs por similitud, con su *score* |
| POST | `/vectorizacion/confirmar` | Paso 2: persiste los KPIs aceptados (con evidencia) y devuelve el JSON enriquecido |
| POST | `/vectorizacion/kpis/reindex` | Mantenimiento: revectoriza el catálogo de KPIs en la colección `kpis` |
| GET | `/vectorizacion/summary/{id_instrumento}` | Inspección del *embedding* del *summary*: modelo, dimensión y muestra |

**Catálogo y espacio vectorial** (prefijo `/vectorizacion`):

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/vectorizacion/kpis/catalogo` | Catálogo completo de KPIs de la base de datos (solo lectura) |
| GET | `/vectorizacion/espacio` | Proyección 2D (PCA) de las colecciones `kpis` y `summary_instrument` para visualización |

**Cálculo de KPIs** (prefijo `/kpis/calculo`):

| Método | Ruta | Propósito |
|--------|------|-----------|
| POST | `/kpis/calculo/preparar` | Envía la fórmula del KPI a Ollama para extraer sus variables de entrada como JSON |
| POST | `/kpis/calculo/registrar` | Calcula el nivel del semáforo según la polaridad del KPI y persiste el cálculo |
| GET | `/kpis/calculo/{id_instrumento}` | Lista los cálculos de KPI registrados para el instrumento |

**Grafo de recomendación** (prefijo `/grafo`):

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/grafo/acervo` | Grafo base: instrumentos como nodos y aristas de KPI compartido |
| POST | `/grafo/recomendar` | Recomendaciones para un set activo (semántica + Jaccard de KPIs) |
| POST | `/grafo/investigacion` | Persiste el *snapshot* del grafo y traduce `id_instrumento` → `id_crudo` |

Los dos pasos de la vectorización (`propuestas` y `confirmar`) y la preparación
del cálculo (`preparar`) reciben archivos o cuerpos JSON; su funcionamiento
detallado se documenta en los subtemas de indexación y de consulta con el modelo.

### 3.4 Metadata Service (puerto 8003)

Gestiona los metadatos Dublin Core y los metadatos específicos por tipo. Los
enrutadores se montan bajo el prefijo `/api`, y las rutas se exponen al frontend
a través del *gateway* bajo `/api/metadata/*`. Por razones históricas de montaje,
las rutas de Dublin Core presentan un doble segmento `metadata/metadata`, que el
*gateway* preserva sin alteración.

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/health` | Estado del servicio (incluye además `/health/ready` y `/health/live`) |
| GET | `/api/metadata/metadata/{id}/init` | Campos Dublin Core autocompletados para inicializar el formulario |
| POST | `/api/metadata/metadata/{id}` | Registra los 13 campos Dublin Core (inmutable: 409 si ya existen) |
| GET | `/api/metadata/metadata/{id}` | Recupera los metadatos Dublin Core del instrumento |
| GET | `/api/metadata/metadata` | Lista los registros Dublin Core con paginación |
| DELETE | `/api/metadata/metadata/{id}` | Elimina los metadatos Dublin Core (para rehacer el registro) |
| POST | `/api/metadata/{id}/especificos` | *Upsert* de los metadatos específicos del tipo de instrumento (editable) |

El registro específico recibe un cuerpo `{tipo, campos}`: el `tipo` se valida
contra el tipo real del instrumento (409 si no coincide) y solo se persisten los
campos presentes y no vacíos de la tabla del tipo correspondiente.

### 3.5 Storage Service (puerto 8004)

Autoridad de artefactos del sistema. Se expone al frontend a través del *gateway*
bajo el prefijo `/almacenamiento/*`.

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/health` | Estado del servicio |
| POST | `/almacenamiento/json` | Guarda un JSON (`metadata` o `analysis`) con clave versionada |
| POST | `/almacenamiento/archivo` | Guarda un binario (`raw`, `sav`, `temp`); límite de 50 MB |
| GET | `/almacenamiento/artefacto/{tipo}/{instrumentoId}` | Recupera un artefacto por clave (opcionalmente por `version`) |
| GET | `/almacenamiento/artefactos` | Lista o filtra artefactos por `instrumentoId` y/o `tipo` |

Cada escritura resuelve la siguiente versión del artefacto, construye una clave
estable (`tipo/instrumentoId/version__slug`), escribe de forma atómica y registra
la entrada —ruta absoluta y relativa, tamaño, nombre original y marca de tiempo—
en un índice, de modo que el historial de versiones quede trazable.

### 3.6 Visualization Service (puerto 8005)

Núcleo RAG del sistema. Se expone al frontend a través del *gateway* bajo el
prefijo `/rag/*`.

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/health` | Estado del servicio |
| POST | `/rag/index` | Indexa los instrumentos de una investigación en su colección de Chroma (admite reindexar) |
| POST | `/rag/chat` | Responde una pregunta fundamentada en los instrumentos, citando fuentes (SSE o JSON) |

El indexado recibe `{investigacionId, instrumentoIds, reindexar}` y devuelve el
resumen por instrumento (indexado u omitido, con el número de *chunks*). El chat
recibe `{investigacionId, pregunta, modelo, instrumentoIds, top_k, stream}`; si no
se indica `modelo`, usa el modelo por defecto de la configuración, y si `stream`
es verdadero, la respuesta se transmite como eventos *SSE* (*tokens*, luego las
fuentes y, finalmente, el evento de fin).

---

## 4. Generación de datos sintéticos

Para desarrollar y demostrar la plataforma sin depender de datos reales de
estudiantes —sujetos a marcos de protección de información personal y de obtención
lenta—, se construyó un **motor de generación de datos sintéticos**. Este motor
produce, de forma reproducible, el conjunto de instrumentos de investigación
educativa con los que se ejercita todo el flujo del sistema: carga, metadatos,
estandarización, vectorización, inferencia de KPIs y recuperación RAG.

Esta sección documenta el motor como un **componente de ingeniería**: su
estructura, su interfaz de línea de comandos, los artefactos que produce y las
técnicas que implementa. El fundamento metodológico y psicométrico de la
generación —la justificación del enfoque sintético, la calibración de los perfiles
con base en literatura, el detalle de las distribuciones estadísticas y las
referencias académicas— se documenta de forma extensa en el documento
`storage/instrumentos_sinteticos/METODOLOGIA_DATOS_SINTETICOS.md`, al que se
remite para no duplicar aquí ese contenido.

### 4.1 Ubicación y estructura del motor

El motor es una herramienta autónoma, independiente de los microservicios, que
reside en `tools/data_synthesis/`. Está escrito en Python y se apoya en la pila
científica habitual (NumPy, pandas, SciPy para la generación, y matplotlib y
seaborn para las gráficas). Su organización separa la configuración, los
generadores por tipo de instrumento, la validación de calidad y la
visualización:

```text
tools/data_synthesis/
├── generate.py                      # CLI principal (orquesta la generación)
├── config/
│   ├── perfiles_estudiantes.json    # 8 perfiles con sus parámetros estadísticos
│   └── kpi_mapping.json             # Definición de los 30 instrumentos y sus KPIs
├── generators/
│   ├── base_generator.py            # Utilidades compartidas (muestreo, beta, correlación...)
│   ├── encuesta_generator.py        # Generador de las 10 encuestas
│   ├── entrevista_generator.py      # Generador de las 10 entrevistas
│   └── prueba_generator.py          # Generador de las 10 pruebas estandarizadas
├── quality/
│   └── checker.py                   # Validación: alpha de Cronbach, outliers, correlación
└── visualization/
    └── chart_generator.py           # Gráficas por instrumento y de resumen
```

Toda la configuración que gobierna la generación está **externalizada en archivos
JSON**: `perfiles_estudiantes.json` define los perfiles de estudiante y los
parámetros de correlación y de sesgo, mientras que `kpi_mapping.json` define el
catálogo de instrumentos —título, fuente, dimensiones, número de ítems, tipos de
pregunta y KPIs asociados—. Esta separación permite ajustar o ampliar el conjunto
de datos editando configuración, sin tocar la lógica de generación.

### 4.2 Interfaz de línea de comandos

El punto de entrada es `generate.py`, una CLI que orquesta las tres fases del
proceso —generación, visualización y validación de calidad— según los argumentos
recibidos. Las invocaciones principales son:

| Comando | Efecto |
|---------|--------|
| `python generate.py --all` | Genera los 30 instrumentos (encuestas, entrevistas y pruebas) |
| `python generate.py --tipo encuesta` | Genera solo los instrumentos de un tipo |
| `python generate.py --tipo encuesta --n 3` | Genera *n* instrumentos adicionales, continuando la numeración |
| `python generate.py --all --seed 42` | Generación reproducible con una semilla concreta |
| `python generate.py --charts-only` | Regenera solo las gráficas (sobre datos ya generados) |
| `python generate.py --quality-only` | Corre solo la validación de calidad |
| `python generate.py --all --no-charts --no-quality` | Genera sin gráficas ni validación (más rápido) |
| `python generate.py --all --output <ruta>` | Dirige la salida a un directorio personalizado |

Tras una generación completa, la CLI encadena de forma automática la generación de
gráficas y la validación de calidad, salvo que se desactiven con `--no-charts` y
`--no-quality`. La salida por defecto es el directorio
`storage/instrumentos_sinteticos/`.

### 4.3 Reproducibilidad e idempotencia

Dos propiedades hacen que el motor sea apto para un trabajo de investigación
verificable. La primera es la **reproducibilidad**: toda la aleatoriedad se deriva
de un generador de números aleatorios de NumPy inicializado con una semilla
(`--seed`, 42 por defecto), de modo que la misma semilla produce exactamente el
mismo conjunto de datos. Para que los tres tipos de instrumento no compartan la
misma secuencia aleatoria, cada generador parte de una semilla desplazada:
encuestas usan la semilla base, entrevistas la semilla más 100 y pruebas la
semilla más 200.

La segunda es la **continuidad de la numeración**: antes de generar, cada
generador lee los archivos de metadatos ya existentes en el directorio de salida y
reanuda la numeración a partir del último instrumento producido. Así, la opción
`--n` añade instrumentos nuevos sin sobrescribir los previos, mientras que `--all`
regenera el conjunto completo.

### 4.4 Técnicas de generación implementadas

La lógica común a todos los generadores reside en la clase `BaseGenerator`
(`base_generator.py`), que implementa las técnicas estadísticas que dan realismo a
los datos. En términos de ingeniería, las piezas clave son:

- **Muestreo de perfiles por peso.** Cada respondente se asocia a uno de los ocho
  perfiles de estudiante, muestreado según la distribución de pesos definida en la
  configuración (por ejemplo, el perfil "promedio comprometido" pesa un 20 %). Los
  instrumentos pueden restringir qué perfiles participan (las entrevistas, por
  ejemplo, se dirigen a subconjuntos de perfiles).
- **Respuestas Likert por distribución beta reescalada.** Las respuestas de escala
  se generan a partir de una distribución beta parametrizada por perfil y
  reescalada al rango de la escala (1 a 5). La forma de la beta modela la asimetría
  esperada de cada perfil —positiva para perfiles de alto rendimiento, negativa
  para perfiles en riesgo—, e incorpora comportamientos especiales como el efecto
  techo de los perfiles de posgrado o la respuesta mixta del perfil con *burnout*.
- **Correlación realista entre ítems.** Para que los ítems de una misma dimensión
  covaríen de forma plausible, se construye una matriz de correlación y se aplica
  una **descomposición de Cholesky** sobre ruido normal, con correlación
  intra-dimensión más alta que la inter-dimensión (valores tomados de la
  configuración). Si la matriz no es definida positiva, el código la perturba
  ligeramente y reintenta.
- **Inyección de sesgos de respuesta.** Sobre una fracción pequeña de respondentes
  se inyectan patrones de sesgo típicos de la literatura —aquiescencia (marcar todo
  alto), rechazo (marcar todo bajo) y zigzag (alternar extremos)—, con las
  probabilidades definidas en la configuración.
- **Generación demográfica coherente.** Para cada respondente se derivan variables
  demográficas consistentes con su perfil (edad, género, semestre, promedio, horas
  de trabajo, tipo de universidad, nivel socioeconómico y marcadores como primera
  generación o beca).
- **Métricas de calidad en línea.** El propio generador estima el coeficiente
  **alpha de Cronbach** y detecta respondentes atípicos (por *z-score* de la media
  por fila), y guarda esos valores en los metadatos de cada instrumento.

### 4.5 Perfiles de estudiante y estrategia de realismo

El problema central de cualquier conjunto de datos sintéticos es evitar que
resulte *demasiado artificial*: si todos los respondentes se comportaran igual,
las respuestas serían uniformes, las correlaciones perfectas y los indicadores
triviales de calcular, con lo que el conjunto no ejercitaría de forma realista al
sistema. La estrategia del motor para contrarrestar esto se apoya en una idea
central: en lugar de muestrear respuestas de una única distribución global, cada
respondente se genera a partir de uno de **ocho perfiles de estudiante**, cada uno
con su propia "personalidad estadística". La heterogeneidad entre perfiles, sumada
a varias fuentes de ruido deliberado, es lo que aporta variabilidad creíble al
conjunto.

**Los ocho perfiles.** Cada perfil representa un arquetipo de estudiante
universitario, con un peso poblacional (cuántos respondentes le corresponden) y un
conjunto de parámetros estadísticos y demográficos coherentes entre sí. Están
definidos en `config/perfiles_estudiantes.json`:

| Perfil | Arquetipo | Peso | Forma Likert (α,β) | Media Likert | Rasgo distintivo |
|--------|-----------|------|--------------------|--------------|------------------|
| P1 | Alto rendimiento, autorregulado | 12 % | β(6,2) | ~4.2 | Asimetría positiva marcada |
| P2 | Promedio comprometido | 20 % | β(4,3) | ~3.4 | Distribución central, es el perfil más común |
| P3 | En riesgo académico | 15 % | β(2,5) | ~2.1 | Asimetría negativa, mayor tasa de atípicos |
| P4 | Trabajador adulto (tiempo parcial) | 13 % | β(3,3) | ~3.0 | Patrón irregular, alta dispersión |
| P5 | Avanzado desmotivado (*burnout*) | 10 % | β(3,4) | ~3.0 | Respuesta mixta: motivación baja, rendimiento alto |
| P6 | Internacional / contexto diverso | 8 % | β(3,3) | ~3.1 | Distribución plana, posible sesgo cultural |
| P7 | Posgrado alta competencia | 12 % | β(7,2) | ~4.5 | Efecto techo en las respuestas |
| P8 | Dificultades socioeconómicas | 10 % | β(2.5,4) | ~2.8 | Ítems de bienestar deprimidos |

Los pesos no son uniformes: suman 1.0 y reproducen una población plausible, en la
que predomina el estudiante promedio (P2, 20 %) y los perfiles extremos son
minoritarios. Esto evita el primer gran artificio —una población demasiado
balanceada— y hace que las muestras tengan la mezcla desigual de una población
real.

**Cómo cada perfil "ensucia" los datos de forma controlada.** La clave para que el
conjunto no sea artificial es que cada perfil introduce su propia desviación
respecto de un comportamiento ideal. Varias de estas desviaciones se implementan
de manera explícita en el código:

- **Forma de la distribución por perfil.** La asimetría de las respuestas Likert la
  fija la distribución beta de cada perfil: P1 y P7 se inclinan a valores altos
  (α > β), P3 y P8 a valores bajos (α < β), y P2, P4 y P6 quedan más centrados o
  planos. Así, dos respondentes de distinto perfil ante el mismo ítem producen
  distribuciones distintas, no ruido alrededor de una misma media.
- **Comportamientos especiales por perfil.** Algunos perfiles activan un
  tratamiento adicional: el perfil de posgrado (P7) aplica un **efecto techo** que
  comprime sus respuestas hacia la parte alta de la escala, imitando a quien marca
  casi todo en el máximo; y el perfil con *burnout* (P5) usa **dos distribuciones
  separadas** —una baja para los ítems de motivación y una alta para los de
  rendimiento—, reproduciendo la disonancia real de un estudiante competente pero
  desmotivado.
- **Tasa de atípicos diferenciada.** Cada perfil declara su propia `tasa_atipicos`,
  de modo que los perfiles más vulnerables (P3, P8) generan proporcionalmente más
  respondentes atípicos que los perfiles estables (P1, P7), tal como ocurre en
  muestras reales.
- **Demografía coherente con el arquetipo.** Las variables demográficas no se
  sortean al azar, sino dentro de los rangos propios del perfil: el trabajador
  adulto (P4) tiene edades de 25 a 35 años y de 30 a 50 horas de trabajo semanal;
  el estudiante en riesgo (P3) es de primera generación y de nivel socioeconómico
  bajo; el de dificultades económicas (P8) tiene beca. Esta coherencia interna es
  la que hace que un respondente "cuelgue junto" como una persona plausible y no
  como una colección de atributos inconexos.

**Fuentes de ruido deliberado sobre la base de perfiles.** Encima de la
heterogeneidad entre perfiles, el motor añade tres mecanismos que rompen cualquier
regularidad excesiva, descritos ya en el apartado 4.4 y que aquí se leen como
estrategia anti-artificialidad: la **correlación imperfecta** entre ítems (vía
Cholesky, con un coeficiente que no es ni 0 ni 1, sino un valor intermedio
muestreado por bloque), los **sesgos de respuesta** inyectados en una fracción de
respondentes (aquiescencia, rechazo y zigzag) y la **correlación cruzada** más
débil entre dimensiones distintas que dentro de una misma dimensión. En conjunto,
estos mecanismos consiguen que los instrumentos presenten una consistencia interna
realista —reflejada en los valores de alpha de Cronbach— en lugar de una
correlación perfecta y, por tanto, sospechosa.

**Realismo en las respuestas cualitativas.** La estrategia se extiende al texto de
las entrevistas, donde el riesgo de artificialidad es aún mayor. En lugar de
repetir una misma respuesta, el generador mantiene **plantillas de respuesta por
perfil** y las expande con frases propias del arquetipo: el estudiante de alto
rendimiento (P1) habla de disciplina y planificación, el de riesgo (P3) expresa
frustración con la institución, el internacional (P6) responde incluso en inglés
para reflejar su contexto, y el de *burnout* (P5) verbaliza el desgaste. Además,
la longitud de cada respuesta varía de forma aleatoria —a veces se añade una
segunda frase—, de modo que las transcripciones no quedan uniformes. El resultado
es un corpus cualitativo heterogéneo, apto para alimentar la vectorización y la
recuperación RAG con textos distinguibles entre sí.

En síntesis, el conjunto no es "menos sintético", pero sí **deliberadamente
heterogéneo**: la combinación de perfiles con pesos desiguales, formas de
distribución distintas, demografía coherente, comportamientos especiales, ruido de
correlación y sesgos de respuesta produce datos que, sin dejar de ser plausibles,
no son uniformes ni perfectamente predecibles —que es justo lo que se necesita para
ejercitar el sistema en condiciones próximas a las reales—.

### 4.6 Artefactos de salida

Por cada instrumento generado, el motor produce tres artefactos en el directorio
de su tipo (`encuestas/`, `entrevistas/` o `pruebas/`), con un nombre derivado del
identificador del instrumento (`enc_01`, `ent_01`, `pru_01`, ...):

| Artefacto | Contenido |
|-----------|-----------|
| `<id>_respondido.csv` | Matriz de respuestas: una fila por respondente, con sus variables demográficas y sus respuestas a cada ítem |
| `<id>_original.txt` | Instrumento original (solo las preguntas, sin respuestas), que alimenta la vectorización semántica del sistema |
| `<id>_metadata.json` | Metadatos del instrumento: título, tipo, fuente, dimensiones, KPIs asociados y los parámetros estadísticos estimados (alpha, porcentaje de atípicos, perfiles usados) |

La correspondencia entre estos artefactos y el flujo del sistema es directa: el
archivo `_respondido.csv` es el que se carga como instrumento respondido, y el
`_original.txt` es el instrumento sin respuestas que se usa para construir el
*summary* y vectorizarlo (descrito en los subtemas de indexación). Esta
estructura de dos archivos —respondido y original— refleja exactamente lo que el
*endpoint* de carga del *instrument-service* espera recibir.

### 4.7 Validación de calidad

Tras la generación, el módulo `quality/checker.py` recorre los CSV producidos y
calcula, para cada instrumento, el alpha de Cronbach sobre sus ítems de escala, el
porcentaje de respondentes atípicos y un resumen de la correlación entre ítems. El
umbral de referencia es un alpha mayor o igual a 0.70 para los instrumentos de
tipo Likert; las entrevistas y las pruebas se evalúan con un criterio distinto, al
no estar compuestas principalmente por escalas. El resultado se imprime como un
reporte por tipo y se persiste en `quality_report.json`, dejando constancia
verificable de la consistencia interna del conjunto generado.

### 4.8 Conjunto generado

Con la configuración actual, el motor produce **30 instrumentos**: 10 encuestas,
10 entrevistas y 10 pruebas estandarizadas. Cinco de las encuestas se basan en
instrumentos reales de la literatura (IEAE, Student Engagement Questionnaire, SESQ,
MSLQ-SF y la escala RAU), mientras que el resto son instrumentos sintéticos
diseñados para cubrir dimensiones y KPIs específicos. El catálogo completo —con el
título, la fuente, el número de ítems y de respondentes y los KPIs asociados de
cada instrumento— está documentado tanto en `kpi_mapping.json` como, en forma de
tablas, en el documento de metodología citado al inicio de esta sección.

---

## 5. Indexación del *summary* para la asociación de KPIs

La asociación automática de indicadores (KPIs) a un instrumento es una de las dos
capacidades que descansan sobre la base de datos vectorial. Su principio es la
**búsqueda semántica**: se construye una representación textual depurada del
instrumento —el *summary*—, se convierte en un vector y se compara contra el
catálogo de KPIs, también vectorizado, para recuperar los más próximos en
significado. Toda esta lógica reside en el *analysis-service*, en el módulo
`app/vectorization/`, y se apoya en tres piezas: un modelo de *embeddings*
(*sentence-transformers*), la base vectorial ChromaDB y la base de datos
relacional para persistir el resultado confirmado.

Esta sección documenta cómo se implementa la indexación del *summary* y la
inferencia de KPIs. Una decisión de diseño atraviesa toda la sección y conviene
anticiparla: **lo que se vectoriza del instrumento son únicamente sus preguntas y
sus metadatos clave, nunca las respuestas de los participantes**. Incluir las
respuestas introduciría ruido que degradaría la calidad de la búsqueda; el
objetivo es capturar *de qué trata* el instrumento, no *qué contestó la gente*.

### 5.1 Las dos colecciones vectoriales

El mecanismo opera sobre dos colecciones de ChromaDB, ambas creadas con distancia
**coseno** (`hnsw:space=cosine`) para que la similitud entre vectores normalizados
sea comparable:

- **`kpis`**: contiene un punto por cada KPI del catálogo. Es el "lado fijo" de la
  comparación y se construye con una operación de mantenimiento (apartado 5.5).
- **`summary_instrument`**: contiene un punto por instrumento, cuyo vector es el
  *summary*. Es el "lado variable": se puebla cada vez que se analiza un
  instrumento.

Ambas colecciones viven en el servidor ChromaDB (un contenedor propio), al que el
*analysis-service* se conecta por HTTP usando el nombre de servicio de la red
interna. El cliente de Chroma almacena e indexa los vectores, pero **no los
calcula**: los *embeddings* se generan por separado y se le entregan ya listos.

### 5.2 El modelo de *embeddings*

La vectorización usa un modelo multilingüe de la biblioteca
*sentence-transformers*, configurable por entorno
(`paraphrase-multilingual-mpnet-base-v2` por defecto), que produce vectores de 768
dimensiones. Dos detalles de implementación son relevantes:

- **Carga perezosa.** El modelo —de varios cientos de megabytes— se instancia la
  primera vez que se necesita, no al arrancar el servicio, de forma segura entre
  hilos. Así, ni el arranque del contenedor ni las operaciones que no tocan
  *embeddings* pagan ese costo. La caché del modelo se persiste en un volumen
  Docker compartido para no volver a descargarlo en cada recreación.
- **Normalización.** Los vectores se normalizan al generarse
  (`normalize_embeddings=True`), lo que es coherente con el uso de la distancia
  coseno como medida de cercanía.

### 5.3 Construcción del *summary*

Antes de vectorizar, el sistema construye el texto del *summary* combinando dos
fuentes, en este orden:

1. **Metadatos clave** extraídos del JSON del instrumento. No se vuelca el JSON
   entero: un extractor selecciona, según el tipo de instrumento, solo los campos
   semánticamente significativos.
2. **Instrumento original**, es decir, el texto de las preguntas sin las
   respuestas (el archivo `.md`/`.txt` que acompaña a la carga, el mismo
   `_original.txt` que produce el motor de datos sintéticos).

**Dónde reside (y dónde no) la diferencia por tipo de instrumento.** Conviene
precisar este punto, porque la construcción del *summary* está separada en dos
responsabilidades con grados de especialización distintos:

- La **extracción de metadatos clave es específica por tipo**. Es el único punto
  del flujo que distingue entre encuesta, entrevista y prueba. La correspondencia
  entre tipo y campos a extraer está declarada como una tabla de configuración
  (`CAMPOS_ESPECIFICOS_POR_TIPO`), sobre una base común de cuatro campos Dublin
  Core:

  ```python
  # Base común a los tres tipos (Dublin Core).
  DUBLIN_CORE_KEYS = ("dc:title", "dc:subject", "dc:description", "dc:coverage")

  # Campos específicos SEGÚN EL TIPO (aquí vive la diferenciación).
  CAMPOS_ESPECIFICOS_POR_TIPO = {
      TipoInstrumento.ENCUESTA: (
          "carrera", "notas_contextuales", "notas_interpretacion",
          "constructo_principal", "dimensiones", "palabras_clave",
      ),
      TipoInstrumento.ENTREVISTA: (
          "objetivo", "metodologia",
      ),
      TipoInstrumento.PRUEBA_ESTANDARIZADA: (
          "unidad_de_aprendizaje", "taxonomia_bloom",
          "objetivo_de_evaluacion", "competencias",
      ),
  }
  ```

  Así, una encuesta aporta al *summary* su constructo, dimensiones y palabras
  clave; una entrevista, su objetivo y metodología; y una prueba estandarizada, su
  unidad de aprendizaje, taxonomía de Bloom y competencias. El extractor recorre
  primero los campos Dublin Core comunes y luego los específicos del tipo, de forma
  tolerante a faltantes (si un campo no está, se omite):

  ```python
  def extract_key_metadata(data, tipo) -> dict[str, str]:
      resultado = {}
      # Base común (siempre).
      for key in DUBLIN_CORE_KEYS:
          valor = _coerce_text(dublin.get(key))
          if valor:
              resultado[ETIQUETAS_CAMPOS.get(key, key)] = valor
      # Específicos del tipo (aquí difiere encuesta / entrevista / prueba).
      for campo in CAMPOS_ESPECIFICOS_POR_TIPO[tipo]:
          valor = _resolver_carrera(data, survey) if campo == "carrera" \
                  else _coerce_text(survey.get(campo))
          if valor:
              resultado[ETIQUETAS_CAMPOS.get(campo, campo)] = valor
      return resultado
  ```

- La **construcción del texto del *summary* es genérica**. Una vez extraídos los
  metadatos, el ensamblado del texto no sabe —ni necesita saber— de qué tipo de
  instrumento se trata: simplemente concatena el diccionario de metadatos ya
  resuelto con el texto del instrumento original. Por eso la función `build_summary`
  no contiene ninguna rama por tipo:

  ```python
  def build_summary(metadatos: dict[str, str], instrumento_original: str) -> str:
      partes: list[str] = []
      if metadatos:                                 # metadatos YA diferenciados por tipo
          partes.append("## Metadatos del instrumento")
          for etiqueta, valor in metadatos.items():
              partes.append(f"{etiqueta}: {valor}")
      texto_original = (instrumento_original or "").strip()
      if texto_original:
          partes.append("")
          partes.append("## Instrumento original")
          partes.append(texto_original)             # solo preguntas, nunca respuestas
      return "\n".join(partes).strip()
  ```

Esta separación es intencional y tiene una ventaja de mantenimiento: añadir o
cambiar los campos que caracterizan a un tipo de instrumento se hace editando la
tabla de configuración, sin tocar la lógica de ensamblado ni la de vectorización.
El texto resultante —encabezado por una sección de metadatos y otra con el
instrumento original— es la entrada del *embedding*; mantenerlo limpio y centrado
en lo relevante es lo que hace que la asociación de KPIs sea precisa.

Un detalle de la implementación: cuando ciertos campos de notas (contextuales o de
interpretación) llegan vacíos en el JSON de prueba, se rellenan con un texto
*placeholder* para que el vector no quede hueco. Es un apoyo pensado para el
conjunto sintético y no afecta a instrumentos con metadatos completos.

### 5.4 Vectorización, indexado y búsqueda

Con el *summary* construido, el flujo de proposición de KPIs (el *endpoint*
`POST /vectorizacion/propuestas`, paso 1 del flujo descrito en la sección 2.4)
ejecuta tres acciones encadenadas:

1. **Vectorizar** el *summary* con el modelo de *embeddings*.
2. **Indexar** ese vector en la colección `summary_instrument`, mediante un
   *upsert* cuyo identificador de punto es el `id_instrumento`. Al ser *upsert*,
   reanalizar el mismo instrumento actualiza su punto en lugar de duplicarlo. Como
   metadatos del punto se guardan el `id_instrumento`, el tipo de instrumento y la
   sección (`summary_instrument`).
3. **Buscar** en la colección `kpis` los vectores más cercanos al del *summary*.

La búsqueda recupera los `top_k` KPIs más próximos (cinco por defecto). Para cada
candidato, la **distancia coseno** que devuelve Chroma se transforma en un *score*
de similitud en el rango [0, 1] mediante la relación `score = 1 − distancia`
(acotada por seguridad numérica), de modo que un valor más alto indica mayor
parecido. Solo se conservan los candidatos cuyo *score* supera un **umbral mínimo**
(0.30 por defecto), y la lista final se ordena de mayor a menor similitud. El
resultado es un conjunto de KPIs propuestos, cada uno con su `kpi_id`, su nombre,
sus atributos (polaridad y tipo de objetivo estratégico) y su *score*, que se
presenta al usuario para que decida.

El núcleo de este paso es la función `search_kpis`, que consulta Chroma, convierte
cada distancia en un *score* y filtra por el umbral antes de ordenar:

```python
def _distance_to_score(distance: float) -> float:
    """Convierte distancia coseno [0,2] a score de similitud [0,1]."""
    score = 1.0 - float(distance)
    return max(0.0, min(1.0, score))   # acotado por seguridad numérica

def search_kpis(summary_vector, *, top_k=None, min_score=None, collection=None):
    k = top_k or settings.KPI_SEARCH_TOP_K            # 5 por defecto
    umbral = min_score or settings.KPI_SEARCH_MIN_SCORE  # 0.30 por defecto
    coleccion = collection or chroma_client.get_or_create_collection(
        settings.CHROMA_COLLECTION_KPIS)
    res = chroma_client.query(coleccion, summary_vector, top_k=k)

    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    matches = []
    for meta, dist in zip(metadatas, distances):
        score = _distance_to_score(dist)
        if score < umbral:          # se descartan los poco parecidos
            continue
        matches.append(KpiMatch(kpi_id=int(meta["kpi_id"]),
                                nombre=str(meta.get("nombre", "")),
                                ...,
                                score=round(score, 4)))
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches
```

Conviene subrayar que este paso **no persiste nada en la base de datos
relacional** ni modifica el JSON del instrumento: solo indexa el vector del
*summary* y devuelve propuestas. La persistencia ocurre después, cuando el usuario
confirma (apartado 5.6).

### 5.5 Indexación del catálogo de KPIs

El "lado fijo" de la comparación —la colección `kpis`— se construye con una
operación de mantenimiento independiente, el *endpoint*
`POST /vectorizacion/kpis/reindex`. No se dispara en cada carga de instrumento,
sino al sembrar el catálogo de KPIs o cuando este cambia.

Cada KPI se vectoriza usando **únicamente** su campo `texto_contexto_rag_vectorial`
—un párrafo autocontenido, redactado para la recuperación semántica—, mientras que
el resto de sus columnas (nombre, polaridad, tipo de objetivo, fórmula,
descripción) viajan como metadatos escalares del punto. El identificador del punto
en Chroma es el `kpi_id` convertido a cadena, lo que permite mapear de vuelta a la
base de datos tras una búsqueda. La reindexación **borra y recrea** la colección
antes de reinsertar, de modo que no sobrevivan KPIs obsoletos ni claves de
metadato antiguas.

Que el *summary* del instrumento y el texto del KPI se proyecten al mismo espacio
vectorial —con el mismo modelo de *embeddings*— es lo que hace que la distancia
entre ambos sea una medida válida de afinidad temática.

### 5.6 Confirmación y persistencia de la evidencia

La asociación definitiva de KPIs la decide una persona, no el sistema. Cuando el
usuario acepta o rechaza las propuestas, el *endpoint* `POST /vectorizacion/confirmar`
(paso 2) persiste el resultado de forma trazable y transaccional:

- Valida que el instrumento y los KPIs aceptados existan.
- Garantiza una fila en `documento_vectorizado` que representa el *chunk* del
  *summary* (idempotente por instrumento), enlazada a la fila de
  `coleccion_vectorial` correspondiente.
- Registra cada KPI aceptado en `kpi_inferido` y, como **evidencia**, una fila en
  `kpi_inferido_chunk` que vincula el KPI con el *chunk* del *summary* y conserva
  el *score* que se mostró al usuario.
- Enriquece el JSON del instrumento agregando los KPIs aceptados bajo la clave
  `inferred_kpis` y lo devuelve.

Si la persistencia falla en cualquier punto, la transacción se revierte por
completo y no se devuelve un JSON a medias. De este modo, cada KPI asociado a un
instrumento queda respaldado por evidencia verificable —el fragmento que lo
sustentó y su grado de similitud— y no por una decisión opaca del sistema. Las
tablas relacionales guardan las **referencias** a los vectores (identificadores de
colección y de punto) y la evidencia, mientras que los vectores en sí residen en
ChromaDB.

### 5.7 Inspección del vector

Como apoyo a la verificación, el módulo expone además un *endpoint* de solo
lectura, `GET /vectorizacion/summary/{id_instrumento}`, que devuelve información
del vector del *summary* guardado para un instrumento: el modelo con el que se
generó, su dimensión (768), una muestra de sus valores, la metadata del punto y un
*preview* del texto vectorizado. Es útil para confirmar, durante el desarrollo,
qué modelo de *embeddings* se usó y que el instrumento quedó correctamente
indexado.

---

## 6. Indexación de *chunks* para la recuperación RAG

La segunda capacidad que se apoya en la base vectorial es la **recuperación
aumentada por generación (RAG)**: responder preguntas en lenguaje natural
fundamentadas en el contenido de los instrumentos. A diferencia de la asociación
de KPIs —que vectoriza un único *summary* por instrumento—, el RAG necesita
fragmentar el contenido en piezas más pequeñas (*chunks*) para poder recuperar y
citar el fragmento exacto que sustenta una respuesta. Esta lógica reside en el
*visualization-service* (módulo `app/core/`).

> **Nota sobre el estado de desarrollo.** Esta funcionalidad se encuentra **en
> construcción activa**. La infraestructura en que se apoya ya forma parte de la
> orquestación (ChromaDB y Ollama) y el flujo descrito a continuación está
> implementado y es ejercitable, pero su integración con el frontend y el ajuste
> fino de la calidad de las respuestas siguen en curso. Lo que aquí se documenta
> es el estado actual del mecanismo, no una versión cerrada.

### 6.1 Dos estrategias de troceo

El servicio implementa dos caminos para transformar un instrumento en *chunks*
indexables, y elige entre ellos según la riqueza del artefacto JSON disponible:

- **Chunks pre-redactados (camino preferente).** Cuando el JSON del instrumento
  trae su estructura completa (secciones, preguntas y respuestas de los
  respondentes), el servicio no trocea texto crudo, sino que **redacta** fragmentos
  con significado propio: un *chunk* de cabecera (título, descripción y constructo
  principal), un *chunk* de estructura por cada dimensión (sus ítems numerados) y
  *chunks* de hallazgos que **agregan** las respuestas —medias por dimensión
  Likert, interpretaciones, agrupación por desempeño, y resúmenes de preguntas
  numéricas, categóricas y binarias—, además de un resumen global. Cada bloque se
  genera dentro de su propio control de errores, de modo que si una dimensión falla
  no se cae el resto.
- **Troceo por ventanas (camino de respaldo).** Si el JSON no trae estructura
  aprovechable, el servicio recurre a un troceo genérico del texto: ventanas de
  unos 800 caracteres con un solape de 150, cortando preferentemente en límites de
  párrafo y luego de oración, y descartando fragmentos de menos de 40 caracteres.
  El solape evita perder información en las fronteras entre *chunks*, y el troceo
  por caracteres (en vez de por *tokens*) evita añadir una dependencia de
  *tokenizador*. Los parámetros se declaran como constantes del módulo y el cierre
  de cada *chunk* arrastra la cola del anterior para materializar el solape:

```python
VENTANA = 800
SOLAPE = 150
MIN_LONGITUD = 40

# ... al cerrar un chunk lleno, el siguiente arranca con la cola del anterior:
if actual:
    chunks.append(actual)
    cola = actual[-SOLAPE:].strip()               # solape de 150 caracteres
    actual = f"{cola}\n\n{unidad}" if cola else unidad
# ...
return [c.strip() for c in chunks if len(c.strip()) >= MIN_LONGITUD]
```

La existencia de los dos caminos es deliberada: el camino pre-redactado produce
*chunks* mucho más informativos y citables, mientras que el de respaldo garantiza
que cualquier instrumento, por pobre que sea su JSON, pueda indexarse.

### 6.2 Indexado por investigación

El indexado se organiza **por investigación**, no por instrumento suelto. El
*endpoint* `POST /rag/index` recibe el identificador de una investigación y la
lista de instrumentos que la componen, y vuelca sus *chunks* en una **colección de
Chroma propia de esa investigación**. Para cada instrumento, el servicio localiza
su artefacto JSON (consultando primero al *storage-service*, luego la base de datos
y, por último, un respaldo en disco), extrae su texto o construye sus *chunks*
redactados, genera los *embeddings* con el mismo modelo multilingüe descrito en la
sección 5 y los almacena con metadatos de procedencia: título, tipo, investigador
y KPIs del instrumento. La respuesta informa, por instrumento, cuántos *chunks* se
indexaron o por qué se omitió. La operación admite reindexar desde cero, borrando
la colección previa.

### 6.3 Recuperación y generación

Ante una pregunta, el *endpoint* `POST /rag/chat` vectoriza la consulta, recupera
de la colección de la investigación los *chunks* más cercanos (opcionalmente
acotados a un subconjunto de instrumentos) y construye un *prompt* en español que
antepone una instrucción estricta de fundamentación —responder únicamente a partir
del contexto recuperado, sin inventar cifras ni dimensiones— seguida de las fuentes
numeradas y la pregunta. Ese *prompt* se envía al modelo de lenguaje, y la
respuesta se devuelve citando como fuentes los instrumentos de los que proviene la
evidencia (deduplicadas por instrumento). El detalle del modelo y de la generación
se aborda en la sección 7.

---

## 7. Consulta con el modelo de lenguaje

La generación de las respuestas del chat RAG recae en un **modelo de lenguaje
servido localmente por Ollama**, que corre como un contenedor propio dentro de la
orquestación. Esta sección documenta cómo el sistema consulta al modelo y qué se
ha probado hasta el momento.

> **Nota sobre el estado de desarrollo.** La evaluación comparativa de modelos
> está **en una etapa inicial**: hasta ahora se ha trabajado con un único modelo
> base (`llama3.2:3b`). Por tanto, esta sección no presenta una comparativa de
> desempeño entre modelos —que es trabajo futuro—, sino la **arquitectura de
> consulta**, que ya está preparada para intercambiar y comparar modelos, y las
> decisiones de implementación tomadas al integrar el primero.

### 7.1 Arquitectura preparada para intercambiar modelos

Aunque solo se haya evaluado un modelo, el sistema se diseñó desde el principio
para ser **agnóstico al modelo**. La elección del modelo es un parámetro, no una
constante incrustada en el código, y opera en dos niveles:

- **Por configuración.** El modelo por defecto se define en una variable de
  entorno (`OLLAMA_MODEL`, con valor `llama3.2:3b`), de modo que cambiar el modelo
  base de todo el sistema no requiere tocar código, solo configuración.
- **Por petición.** El *endpoint* de chat acepta un parámetro `modelo` en cada
  consulta; si se indica, se usa ese modelo, y si no, se recurre al de la
  configuración. Esto habilita, sin cambios de código, el escenario de
  experimentación que se contempla como continuación del trabajo: lanzar la misma
  pregunta contra distintos modelos de Ollama y comparar sus respuestas.

Esta separación es precisamente lo que permitirá, en una fase posterior, evaluar
varios modelos para decidir cuál responde mejor, sin reescribir el servicio.

### 7.2 Integración con Ollama y optimizaciones de inferencia local

La consulta al modelo se realiza por HTTP contra el *endpoint* de generación de
Ollama. Integrar un modelo de lenguaje en hardware modesto obligó a tomar varias
decisiones de implementación que conviene documentar, pues condicionan el
rendimiento percibido del chat:

- **Modelo residente en memoria de GPU.** Por defecto, Ollama descarga el modelo
  de la memoria de la GPU tras unos minutos de inactividad, lo que introduce una
  recarga de alrededor de veinte segundos en la siguiente consulta. Para evitarlo,
  el contenedor de Ollama se configura para mantener el modelo cargado de forma
  indefinida (`OLLAMA_KEEP_ALIVE=-1`), y cada petición refuerza esa política.
- **Ventana de contexto acotada.** Las peticiones fijan una ventana de contexto de
  2048 *tokens*, suficiente para el *prompt* del RAG (la pregunta más un puñado de
  fuentes). Acotarla reduce el consumo de memoria y deja más espacio para los pesos
  del modelo, evitando que parte del cómputo se traslade a la CPU y ralentice la
  generación. En conjunto, estas dos decisiones llevaron el tiempo de respuesta de
  unos veinticuatro segundos a unos dos en el entorno de prueba.
- **Transmisión por *streaming*.** La respuesta puede entregarse token a token
  mediante eventos del servidor (*SSE*), de modo que el usuario vea la respuesta
  formándose en lugar de esperar a que termine. El API Gateway preserva este flujo
  de extremo a extremo.

### 7.3 Fundamentación y degradación grácil

Dos propiedades de la consulta buscan que las respuestas sean fiables incluso en
condiciones adversas. La primera es la **fundamentación estricta**: el *prompt*
instruye al modelo para que todas las cifras, dimensiones e ítems provengan
exclusivamente del contexto recuperado y para que, si un dato no está, lo diga en
lugar de inventarlo. La segunda es la **degradación grácil**: si Ollama no está
disponible o devuelve un error, el servicio no falla, sino que responde con un
mensaje en español explicando que el modelo local no está accesible y mostrando de
todos modos las fuentes recuperadas, marcando la respuesta como *degradada*. Así,
una caída del modelo nunca deja al usuario sin información ni rompe la interfaz. El
cliente de Ollama encapsula este comportamiento: nunca propaga la excepción, sino
que devuelve una tupla `(texto, degradado)`:

```python
async def generar_no_stream(prompt: str, modelo: str) -> tuple[str, bool]:
    payload = _payload(modelo, prompt, stream=False)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cliente:
            resp = await cliente.post(_url(), json=payload)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Ollama no disponible: %s", exc)
        return MENSAJE_DEGRADADO, True          # degradado = True
    if resp.status_code != 200:
        return MENSAJE_DEGRADADO, True
    texto = resp.json().get("response")
    if not isinstance(texto, str) or not texto:
        return MENSAJE_DEGRADADO, True
    return texto, False                         # respuesta normal
```

donde `_payload` incluye las opciones de rendimiento comentadas en el apartado 7.2
(`keep_alive` y `num_ctx`). El indicador `degradado` viaja hasta el frontend para
que la interfaz pueda señalar que la respuesta no proviene del modelo.

---

## 8. Gestión de usuarios: autenticación, roles y control de acceso

El sistema controla quién puede operar sobre los instrumentos mediante un esquema
de autenticación basado en **JSON Web Tokens (JWT)** y un modelo de **roles**
sencillo. Esta sección documenta ese mecanismo de forma completa: el modelo de
usuarios, las reglas de negocio, el ciclo de vida del token y cómo cada servicio
lo valida.

### 8.1 Modelo de usuarios y roles

Los usuarios se almacenan en la tabla `usuario` del esquema de la base de datos.
Cada cuenta tiene un identificador, un nombre, un correo electrónico único, la
contraseña **cifrada** (`password_hash`) y un **rol**. El sistema no emplea una
tabla de permisos: la autorización se resuelve en la capa de aplicación a partir
del rol.

El vocabulario de roles es cerrado y consta de dos valores:

| Rol | Capacidades |
|-----|-------------|
| `investigador` | Cargar instrumentos y eliminar **únicamente los que él mismo subió** |
| `administrador` | Acceso total: cargar y eliminar **cualquier** instrumento, y **dar de alta** a nuevos usuarios |

Estas son las reglas de negocio que gobiernan a los usuarios:

- **Solo un administrador da de alta usuarios.** El registro de cuentas
  (`POST /auth/register`) está reservado al rol administrador. No existe
  auto-registro público.
- **Problema del primer administrador.** Como un administrador solo puede ser
  creado por otro administrador, el sistema no podría arrancar sin ninguno. Para
  resolverlo, un script de datos semilla (`05_seed_usuarios.sql`) siembra, en el
  primer arranque de la base de datos, un **administrador inicial** y un
  investigador de prueba para desarrollo. Las inserciones son idempotentes
  (condicionadas al correo), de modo que ejecutar el script más de una vez no crea
  duplicados.
- **Unicidad del correo.** No puede haber dos cuentas con el mismo correo; un
  intento de alta con un correo ya existente se rechaza con un conflicto (409).
- **Rol válido.** El alta valida que el rol sea uno de los dos permitidos; en caso
  contrario, se rechaza (422).

### 8.2 Contraseñas: cifrado con *bcrypt*

Las contraseñas **nunca se almacenan ni se transmiten en texto plano**. Al dar de
alta un usuario, la contraseña se transforma con el algoritmo de *hashing*
**bcrypt** (a través de *passlib*) y solo se guarda ese *hash* en la base de datos.
Al iniciar sesión, la contraseña recibida se compara contra el *hash* almacenado
mediante la verificación propia de bcrypt, sin necesidad de descifrar nada.

Un detalle de seguridad adicional está en la verificación de credenciales: cuando
el correo no existe, el sistema igualmente ejecuta una comparación de *hash* contra
un valor de referencia antes de responder. Esto iguala el tiempo de respuesta entre
"usuario inexistente" y "contraseña incorrecta", como defensa básica contra la
enumeración de cuentas por análisis de tiempos. El fragmento que implementa esta
verificación es el siguiente:

```python
def autenticar(db: Session, email: str, password: str) -> Usuario:
    """Verifica email + password. Devuelve el Usuario o lanza 401."""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    # Verificamos el hash aunque el usuario no exista para no filtrar por tiempo
    # si un email está registrado (defensa básica contra enumeración).
    hash_ref = usuario.password_hash if usuario else "$2b$12$" + "x" * 53
    ok = verificar_password(password, hash_ref)
    if usuario is None or not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
```

Nótese que, exista o no el usuario, el camino de ejecución siempre llama a
`verificar_password`; el `hash_ref` ficticio garantiza que el costo de cómputo de
bcrypt se pague en ambos casos. El *hashing* y la verificación en sí se delegan en
*passlib*, encapsulados en dos funciones de una sola línea:

```python
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hashear_password(password_plano: str) -> str:
    """Genera el hash bcrypt de una contraseña nueva (alta de usuario)."""
    return _pwd_context.hash(password_plano)

def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara una contraseña en claro contra su hash almacenado."""
    return _pwd_context.verify(password_plano, password_hash)
```

### 8.3 El token JWT: emisión, contenido y validación

La credencial que acredita a un usuario es un **JWT firmado**. Su ciclo de vida es
el siguiente:

- **Emisión.** Al iniciar sesión correctamente (`POST /auth/login`), el API Gateway
  emite un token firmado con la clave secreta del sistema (`SECRET_KEY`) usando el
  algoritmo HS256. El token transporta en su contenido (*claims*) el identificador
  del usuario (`sub`), su rol (`rol`) y la fecha de expiración (`exp`).
- **Expiración.** El token tiene una validez limitada —60 minutos por defecto,
  configurable—. Pasado ese tiempo, deja de ser válido y el usuario debe volver a
  autenticarse.
- **Validación.** Cualquier servicio valida el token comprobando su firma con la
  **misma `SECRET_KEY` compartida** y verificando que no haya expirado y que
  contenga el identificador de usuario. Esta validación es **autónoma**: no
  requiere consultar al API Gateway ni mantener estado de sesión en el servidor, lo
  que es coherente con una arquitectura de microservicios sin estado. La
  `SECRET_KEY` se inyecta por igual a todos los servicios implicados mediante
  variables de entorno (sección 1.5), de modo que un token emitido por el *gateway*
  pueda ser verificado por cualquier servicio del backend.

La emisión y la validación del token están centralizadas en el módulo
`shared/auth/`, de modo que todos los servicios comparten exactamente la misma
lógica. La emisión arma los *claims* y firma el token:

```python
def crear_access_token(usuario_id: int, rol: str | None,
                       expires_minutes: int | None = None) -> str:
    minutos = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expira = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    payload = {
        "sub": str(usuario_id),   # identificador del usuario
        "rol": rol,               # rol para la autorización
        "exp": expira,            # expiración
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

La validación hace el camino inverso y es deliberadamente **autónoma**: verifica la
firma y la expiración, y extrae el usuario del *claim* `sub`, sin tocar la base de
datos ni llamar al *gateway*. Si algo falla —firma inválida, token expirado o
`sub` ausente— lanza un error controlado:

```python
def decodificar_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"Token inválido o expirado: {exc}") from exc

    sub = payload.get("sub")
    if sub is None:
        raise TokenError("El token no contiene 'sub' (usuario_id).")
    return TokenData(usuario_id=int(sub), rol=payload.get("rol"))
```

El transporte del token sigue el estándar: el cliente lo envía en la cabecera
`Authorization: Bearer <token>`. Como el API Gateway actúa de *proxy* transparente,
reenvía esa cabecera sin alterarla a los servicios internos, que la validan por su
cuenta.

### 8.4 Autenticación y autorización en cada petición

Dentro de cada servicio, la protección de un *endpoint* se expresa de forma
declarativa mediante dependencias de FastAPI:

- **Autenticación** (`get_current_user`): extrae el *Bearer token*, lo decodifica y
  valida, y carga el usuario correspondiente desde la base de datos. Si el token es
  inválido, expiró o el usuario no existe, responde con **401** (no autenticado).
- **Autorización por rol** (`require_rol`): sobre la autenticación anterior, exige
  que el rol del usuario esté entre los permitidos para la operación. Si no lo está,
  responde con **403** (sin permisos).

Ambas dependencias son breves y componibles. `get_current_user` decodifica el token
y resuelve el usuario; `require_rol` se construye sobre ella y filtra por rol:

```python
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                     db: Annotated[Session, Depends(get_db)]) -> Usuario:
    cred_exc = HTTPException(status_code=401,
                            detail="No autenticado. Token inválido o expirado.",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        data = decodificar_token(token)
    except TokenError:
        raise cred_exc
    usuario = db.get(Usuario, data.usuario_id)
    if usuario is None:
        raise cred_exc
    return usuario

def require_rol(*roles: str):
    """Crea una dependencia que exige que el usuario tenga uno de `roles`."""
    def _checker(usuario: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403,
                                detail="No tienes permisos para esta operación.")
        return usuario
    return _checker
```

Así, proteger un *endpoint* es tan declarativo como anotar su dependencia; por
ejemplo, la carga de instrumentos se restringe con
`Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))`.

La **regla de propiedad** del borrado de instrumentos —un investigador solo puede
eliminar los suyos— no se expresa con `require_rol` (que solo mira el rol), sino en
la capa de servicio: el *endpoint* admite a investigadores y administradores, y es
la lógica de negocio la que, para un investigador, comprueba que el instrumento le
pertenezca antes de borrarlo, devolviendo **403** si intenta borrar uno ajeno.

### 8.5 Estado actual: validación heterogénea entre servicios

Un aspecto que conviene documentar con precisión es que, en el estado actual del
desarrollo, **no todos los servicios validan el JWT del mismo modo**:

- El **API Gateway** y el **instrument-service** aplican la validación JWT
  completa descrita arriba: exigen un *Bearer token* válido y resuelven el usuario
  y su rol a partir de él.
- El **analysis-service** incorpora todavía un **modo de desarrollo**
  (`AUTH_DEV_MODE`) que, cuando está activo, resuelve un usuario fijo de prueba sin
  exigir token. Su propio código documenta que la integración con el JWT del
  *gateway* queda pendiente de cerrar desactivando ese modo. Esto es coherente con
  que el *gateway* consuma el *analysis-service* de forma directa (sección 2.4) y
  no por el *proxy* autenticado.

Esta diferencia es un reflejo del grado de madurez de cada servicio y no de una
decisión de diseño definitiva: la meta es que todos los servicios validen el token
de forma homogénea con la lógica compartida, que ya está centralizada en el módulo
`shared/auth/` (emisión y validación de JWT, *hashing* de contraseñas y catálogo de
roles) justamente para evitar divergencias entre servicios.
