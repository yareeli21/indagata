# Capítulo: Implementación

> Plantilla de organización para el capítulo de Implementación de la tesis.
> El diseño del sistema (arquitectura, modelo de datos, UI, infraestructura) ya
> fue cubierto en el capítulo de Diseño, por lo que aquí solo se hacen
> referencias breves a él y el foco está en **cómo se construyó** el sistema.
> Las notas entre corchetes `[...]` indican qué debe contener cada sección;
> elimínalas conforme redactes.

---

## 1. Introducción del capítulo
[Párrafo breve: qué cubre este capítulo (la construcción del sistema), cómo
retoma lo definido en el capítulo de Diseño y cómo está organizado. Un pequeño
mapa de lo que leerá el lector.]

### 1.1 Objetivo de la implementación
[Qué se construyó y para qué, enlazando con los objetivos de la tesis.]

### 1.2 Relación con el capítulo de Diseño
[Resumen de una página o menos: recuerda al lector la arquitectura de
microservicios y las decisiones de diseño clave que ahora se materializan.
Referencia cruzada: "ver Capítulo X, sección Y".]

---

## 2. Entorno y herramientas de desarrollo

Antes de describir la construcción de cada componente, en esta sección se
presentan las tecnologías, herramientas y convenciones que conformaron el
entorno de desarrollo de la plataforma. Conocer este contexto resulta necesario
para comprender las decisiones técnicas que se detallan a lo largo del capítulo.

### 2.1 Tecnologías y lenguajes

La plataforma se construyó siguiendo una arquitectura de microservicios, en la
que coexisten tecnologías distintas según la capa del sistema. A continuación se
describen las principales herramientas empleadas en cada una de ellas.

**Backend (microservicios).** Los servicios que conforman el backend se
desarrollaron en el lenguaje **Python 3.12**, utilizando el framework
**FastAPI** para la construcción de las APIs y el servidor **Uvicorn** como
servidor de aplicaciones. Para la validación de datos y la gestión de la
configuración se emplearon **Pydantic** y *Pydantic Settings*, mientras que el
acceso a la base de datos se realizó mediante el ORM **SQLAlchemy** junto con el
controlador **psycopg**. La comunicación entre servicios se apoyó en el cliente
HTTP **httpx**, y la autenticación en el API Gateway se implementó con
*python-jose* y *passlib/bcrypt* para el manejo de tokens y el cifrado de
contraseñas.

**Componentes de análisis e inteligencia artificial.** El servicio de análisis
incorpora capacidades de procesamiento de lenguaje natural mediante **Ollama**,
que ejecuta modelos de lenguaje de forma local, y **ChromaDB** como base de
datos vectorial para el almacenamiento y la consulta de *embeddings*. La
generación de dichos *embeddings* se realizó con la librería
**sentence-transformers**.

**Frontend.** La interfaz de usuario se desarrolló con la biblioteca **React
18**, utilizando **Vite** como herramienta de construcción y servidor de
desarrollo, y **Tailwind CSS** para el diseño de estilos. Para las animaciones
de la interfaz se empleó **Framer Motion**.

**Base de datos y almacenamiento.** Como sistema gestor de base de datos
relacional se utilizó **PostgreSQL 16**. Adicionalmente, se incorporó **Redis**
como almacén en memoria para el manejo de caché y datos de sesión.

La siguiente tabla resume el conjunto de tecnologías empleadas, organizadas por
capa:

| Capa | Tecnología | Versión / detalle |
|------|------------|-------------------|
| Lenguaje backend | Python | 3.12 |
| Framework de APIs | FastAPI | 0.115.6 |
| Servidor de aplicaciones | Uvicorn | 0.30.0 |
| ORM / acceso a datos | SQLAlchemy + psycopg | 2.0.25 / 3.2.3 |
| Validación y configuración | Pydantic | 2.9.0 |
| Comunicación entre servicios | httpx | 0.27.0 |
| Autenticación | python-jose + passlib/bcrypt | — |
| Modelos de lenguaje (IA) | Ollama | — |
| Base de datos vectorial | ChromaDB | 1.0.0 |
| Embeddings | sentence-transformers | 3.0.0 |
| Biblioteca de frontend | React | 18.3 |
| Herramienta de construcción | Vite | 6.0 |
| Estilos | Tailwind CSS | 3.4 |
| Base de datos relacional | PostgreSQL | 16 |
| Caché en memoria | Redis | 7 |

### 2.2 Control de versiones y gestión del código

El desarrollo del sistema se gestionó mediante el sistema de control de
versiones **Git**, que permitió llevar un registro histórico de los cambios y
mantener la trazabilidad del trabajo realizado. El código fuente se organizó en
un repositorio con una estructura *monorepo*, en la que conviven, dentro de un
mismo proyecto, los microservicios del backend, la interfaz de usuario, la
infraestructura y los scripts de la base de datos. Este enfoque facilitó la
coordinación entre componentes y simplificó la gestión de las dependencias
compartidas entre servicios.

### 2.3 Convenciones de codificación

Durante la construcción del sistema se siguieron convenciones orientadas a
mantener la legibilidad y la coherencia del código. En el backend se adoptó la
nomenclatura estándar del lenguaje Python (*snake_case* para variables y
funciones, *PascalCase* para clases), conforme a las recomendaciones de la guía
de estilo PEP 8. La organización del proyecto se estructuró de manera que cada
microservicio constituyera un módulo independiente, con sus propias
dependencias declaradas en un archivo *requirements.txt*, mientras que la lógica
común a varios servicios se centralizó en un módulo compartido (*shared*). Esta
organización favoreció la separación de responsabilidades y la reutilización de
código entre los distintos servicios de la plataforma.

---

## 3. Estructura general del proyecto

El código fuente del sistema se organizó en un único repositorio (*monorepo*),
en el que cada responsabilidad del proyecto se separó en un directorio
específico. Esta organización permite ubicar con facilidad cada componente y
refleja de manera directa la arquitectura de microservicios descrita en el
capítulo de Diseño. A continuación se presenta el árbol de carpetas en su nivel
superior, seguido de una descripción de cada elemento:

```text
indagata/
├── services/              # Microservicios que conforman el backend
│   ├── api-gateway/        # Punto de entrada y enrutamiento de peticiones
│   ├── instrument-service/ # Gestión de instrumentos
│   ├── analysis-service/   # Análisis y procesamiento con IA
│   ├── metadata-service/   # Gestión de metadatos
│   ├── storage-service/    # Almacenamiento de archivos y datos
│   └── visualization-service/ # Generación de datos para visualización
├── shared/                # Código común reutilizado por los servicios
│   ├── auth/               # Lógica de autenticación
│   ├── db/                 # Conexión y utilidades de base de datos
│   ├── models/             # Modelos de datos (ORM)
│   ├── repositories/       # Acceso a datos (patrón repositorio)
│   └── schemas/            # Esquemas de validación (Pydantic)
├── pixel-perfect-pixel/   # Interfaz de usuario (frontend)
│   ├── src/
│   │   ├── routes/         # Rutas de la aplicación (TanStack Router)
│   │   ├── features/       # Módulos por dominio (auth, upload,
│   │   │                   #   instruments, research, chat, kpis)
│   │   ├── components/     # Componentes de interfaz compartidos
│   │   ├── api/            # Capa de acceso a datos / API
│   │   ├── hooks/          # Hooks de React reutilizables
│   │   ├── lib/            # Utilidades
│   │   ├── types/          # Tipos de dominio compartidos
│   │   ├── mocks/          # Datos de ejemplo (sustituibles por la API)
│   │   └── styles.css      # Tokens de estilo (color, tipografía, sombras)
│   └── public/             # Recursos estáticos
├── infrastructure/        # Configuración de infraestructura
│   ├── docker/             # Dockerfiles de cada servicio
│   └── postgres/           # Esquema, migraciones y datos semilla
├── storage/               # Volumen de almacenamiento de archivos
├── chromadb/              # Datos de la base vectorial
├── docker-compose.yml     # Orquestación de todos los contenedores
├── .env.example           # Plantilla de variables de entorno
└── .gitignore
```

La estructura responde a una separación clara de responsabilidades:

- **`services/`** agrupa los seis microservicios que componen el backend. Cada
  uno constituye un módulo independiente, con su propio archivo de dependencias
  (*requirements.txt*) y su punto de entrada (*main.py*). Internamente, cada
  servicio organiza su lógica en subdirectorios según su función; por ejemplo,
  el *API Gateway* separa la lógica de la aplicación (*app*) de la de
  enrutamiento hacia los demás servicios (*proxy*).

- **`shared/`** contiene el código común que se reutiliza en los distintos
  servicios, evitando la duplicación. Aquí se concentran la autenticación
  (*auth*), la conexión a la base de datos (*db*), los modelos del ORM
  (*models*), el acceso a datos mediante el patrón repositorio
  (*repositories*) y los esquemas de validación (*schemas*).

- **`pixel-perfect-pixel/`** aloja la interfaz de usuario del sistema,
  desarrollada como una aplicación de React (con TypeScript) construida sobre el
  framework TanStack Start y la herramienta Vite. Su código fuente, ubicado en
  `src/`, se organiza siguiendo un enfoque *por features* (dominios): el
  directorio `features/` agrupa la lógica de cada área funcional de la
  aplicación —autenticación, carga de instrumentos, instrumentos,
  investigación, chat e indicadores (KPIs)—, mientras que `components/` reúne
  los componentes de interfaz compartidos. El enrutamiento se define de forma
  declarativa mediante archivos en `routes/`, y toda interacción con los datos
  se canaliza a través de la capa `api/`, lo que permite sustituir los datos de
  ejemplo (`mocks/`) por llamadas reales a la API del backend sin modificar las
  pantallas. Los tipos de dominio compartidos residen en `types/`, y la
  identidad visual (colores, tipografía y sombras) se centraliza como *tokens*
  semánticos en `styles.css`. Los recursos estáticos se ubican en `public/`.

- **`infrastructure/`** reúne todo lo relacionado con el despliegue y la
  configuración del sistema: los *Dockerfiles* de cada servicio y los scripts de
  la base de datos PostgreSQL, incluyendo el esquema, las migraciones y los
  datos semilla.

- **`storage/`** y **`chromadb/`** funcionan como directorios de persistencia
  para los archivos manejados por el sistema y para la base de datos vectorial,
  respectivamente.

- En la raíz del proyecto se ubica el archivo **`docker-compose.yml`**, que
  orquesta la ejecución conjunta de todos los contenedores, así como la
  plantilla de variables de entorno (**`.env.example`**).

Esta organización facilita el mantenimiento del sistema, pues cada componente
puede desarrollarse y modificarse de forma aislada, al tiempo que la carpeta
*shared* garantiza la coherencia de la lógica común entre los servicios.

---

## 4. Implementación de la base de datos

La base de datos constituye el cimiento del sistema, pues todos los
microservicios dependen de ella para persistir y consultar información. Por esta
razón, su implementación se aborda en primer lugar. Como motor de base de datos
se utilizó PostgreSQL, y la totalidad del modelo se concentró en un único script
que funciona como fuente de verdad del esquema, complementado con scripts de
datos iniciales y de migración.

### 4.1 Creación del esquema

El esquema de la base de datos se definió en el script de inicialización
`01_schema.sql`, el cual se ejecuta automáticamente durante el primer arranque
del contenedor de PostgreSQL. Todas las tablas se agruparon bajo un esquema
propio de PostgreSQL denominado `tt_rag`, lo que permite aislar los objetos del
sistema del resto de la base de datos.

El modelo de datos refleja directamente el flujo de procesamiento de la
plataforma, que parte de la recepción de un instrumento en crudo y culmina con
su vectorización y la inferencia de indicadores (KPIs). Las tablas pueden
agruparse de la siguiente manera según su responsabilidad:

**Usuarios y control de acceso.** La tabla `usuario` almacena los datos de las
cuentas, incluyendo el correo electrónico (único), la contraseña cifrada
(`password_hash`) y el rol del usuario. El rol es el que autoriza las
operaciones de carga y borrado de instrumentos; el sistema no emplea una tabla
de permisos, sino que la validación se realiza en la capa de aplicación.

**Datos de los instrumentos.** La tabla `raw_data` es la tabla padre del modelo:
registra cada instrumento recibido en crudo y conserva tanto el archivo
respondido como el instrumento original sin respuestas, este último destinado a
la vectorización semántica. De ella derivan, mediante relaciones de clave
foránea, la tabla `instrumento_procesado` (que representa el instrumento ya
procesado y lleva el control de su estado dentro del pipeline) y las tablas de
metadatos: `metadatos_dc`, basada en el estándar Dublin Core, y las tablas de
metadatos enriquecidos especializadas por tipo de instrumento
(`metadatos_enriquecidos_encuestas`, `..._entrevistas` y `..._pruebas`).

**Indicadores y variables.** Las tablas `kpi`, `variable` y la tabla puente
`kpi_variable` definen el catálogo de indicadores del sistema y las variables
que los componen. Los resultados de la inferencia se almacenan en `kpi_inferido`
y `valor_variable_inferido`, que registran los KPIs asociados a cada instrumento
procesado y los valores calculados para sus variables.

**Vectorización y RAG.** Las tablas `coleccion_vectorial`,
`documento_vectorizado`, `kpi_inferido_chunk`, `prompts` y `rag_log` dan soporte
al núcleo de inteligencia del sistema. Estas tablas no almacenan los vectores en
sí —estos residen en la base de datos vectorial ChromaDB—, sino las referencias
a ellos (identificadores de colección y de vector), los fragmentos de texto
(*chunks*) generados a partir de cada instrumento, la evidencia que sustenta cada
KPI inferido y el registro histórico de las consultas RAG.

El control de la integridad referencial se garantizó mediante claves foráneas
con borrado en cascada (`ON DELETE CASCADE`), de modo que al eliminar un
instrumento se eliminen también sus metadatos, chunks e inferencias asociadas.
Asimismo, se definieron índices sobre las columnas de uso más frecuente
(propietario del instrumento, estado de procesamiento, relaciones con KPIs y
chunks) con el fin de optimizar el rendimiento de las consultas.

### 4.2 Datos semilla (seed)

Dado que el sistema requiere al menos un usuario administrador para poder operar
—pues solo un administrador puede dar de alta a nuevos usuarios—, se incluyó el
script `05_seed_usuarios.sql` para sembrar las cuentas iniciales durante el
primer arranque de la base de datos. Este script crea un usuario administrador,
necesario para arrancar el sistema, y un usuario investigador de prueba para el
entorno de desarrollo. Las contraseñas se almacenan cifradas mediante *bcrypt*,
nunca en texto plano, y las inserciones son idempotentes (condicionadas al
correo electrónico), de modo que ejecutar el script más de una vez no genera
duplicados ni errores.

### 4.3 Migraciones y evolución del esquema

Puesto que los scripts de inicialización únicamente se ejecutan en el primer
arranque de la base de datos, los cambios posteriores al esquema se gestionaron
mediante scripts de migración independientes, ubicados en el directorio
`migrations`. Estos scripts están diseñados para aplicarse sobre bases de datos
ya existentes y se construyeron de forma idempotente, lo que permite ejecutarlos
varias veces sin provocar errores ni inconsistencias.

Un ejemplo representativo es la migración que integró nuevas capacidades al
sistema, la cual incorporó estados adicionales al pipeline de procesamiento,
agregó columnas a tablas existentes y creó nuevas tablas, migrando además los
datos previos al nuevo esquema. Para cada migración se mantuvo, cuando fue
pertinente, un script de reversión (*rollback*) que permite deshacer los
cambios en caso necesario. Este enfoque posibilitó la evolución controlada del
modelo de datos a lo largo del desarrollo, preservando la información ya
almacenada.

---

## 5. Implementación de los microservicios

El backend de la plataforma se construyó como un conjunto de microservicios
independientes, cada uno responsable de una parte específica del dominio. Todos
se desarrollaron con la misma base tecnológica —Python y el framework FastAPI—
y siguen una estructura homogénea: un punto de entrada (`main.py`) que crea la
aplicación, configura el registro de eventos (*logging*) y el middleware de
CORS, y agrupa los *endpoints* en enrutadores (*routers*) según su función. Cada
servicio escucha en un puerto propio y expone, como mínimo, un *endpoint*
`GET /health` que permite verificar su disponibilidad.

### 5.1 Visión general y comunicación entre servicios

La comunicación entre los servicios se realiza mediante peticiones HTTP sobre
una API de tipo REST, utilizando el formato JSON para el intercambio de datos.
Cada servicio se ejecuta en su propio contenedor y se comunica con los demás a
través de la red interna definida en la orquestación, empleando como dirección
el nombre del servicio en lugar de direcciones fijas. El API Gateway actúa como
punto de entrada único del sistema: recibe las peticiones del frontend y las
redirige al servicio correspondiente. La siguiente tabla resume los servicios y
el puerto en que opera cada uno:

| Servicio | Puerto | Responsabilidad principal |
|----------|--------|---------------------------|
| API Gateway | 8000 | Autenticación y punto de entrada |
| Instrument Service | 8001 | Carga y registro de instrumentos |
| Analysis Service | 8002 | Vectorización e inferencia de KPIs |
| Metadata Service | 8003 | Gestión de metadatos (Dublin Core y enriquecidos) |
| Storage Service | 8004 | Persistencia de artefactos |
| Visualization Service | 8005 | Visualización de resultados |

### 5.2 API Gateway

El API Gateway (puerto 8000) constituye la puerta de entrada del sistema. En su
estado actual, concentra el módulo de autenticación mediante tokens JWT y está
preparado para enrutar las peticiones hacia los demás servicios, cuyas
direcciones recibe por configuración. Expone los siguientes *endpoints*
principales:

- `POST /auth/login`: recibe el correo y la contraseña del usuario y, de ser
  válidos, devuelve un token JWT.
- `GET /auth/me`: devuelve los datos del usuario asociado al token recibido.
- `POST /auth/register`: da de alta a un nuevo usuario, operación reservada al
  administrador.

El detalle del flujo de autenticación y su relación con la seguridad del sistema
se aborda en la sección 8.

### 5.3 Servicio de instrumentos (Instrument Service)

El servicio de instrumentos (puerto 8001) es responsable de la carga de los
instrumentos al sistema. Su *endpoint* principal, `POST /instrumentos/upload`,
recibe tanto el instrumento respondido como el archivo original sin respuestas,
identifica el tipo de instrumento y registra la información en la tabla
`raw_data`, dejando los archivos disponibles para las etapas posteriores del
pipeline. El servicio también expone un *endpoint* de borrado, cuya autorización
depende del rol del usuario, de acuerdo con el modelo de control de acceso
descrito en la sección de la base de datos. Al arrancar, el servicio prepara el
directorio de almacenamiento de archivos crudos.

### 5.4 Servicio de análisis (Analysis Service)

El servicio de análisis (puerto 8002) es el encargado de la vectorización de los
instrumentos y de la inferencia de KPIs por similitud semántica, apoyándose en
la base de datos vectorial ChromaDB y en el modelo de *embeddings*. Expone
*endpoints* para proponer KPIs a partir de la similitud
(`POST /vectorizacion/propuestas`), para enriquecer el JSON del instrumento con
los KPIs aceptados por el usuario (`POST /vectorizacion/confirmar`) y para
reindexar la colección de KPIs (`POST /vectorizacion/kpis/reindex`).

Por constituir el núcleo funcional de la plataforma, el flujo completo de
indexación, asociación a KPIs y consulta mediante RAG se documenta de manera
detallada en la sección 6; aquí se describe únicamente el servicio como
componente del backend.

### 5.5 Servicio de metadata (Metadata Service)

El servicio de metadata (puerto 8003) gestiona todas las operaciones
relacionadas con los metadatos de los instrumentos, tanto los basados en el
estándar Dublin Core como los metadatos enriquecidos específicos de cada tipo de
instrumento. Organiza su lógica en enrutadores separados para el registro y la
consulta de metadatos (*metadata*) y para su enriquecimiento (*enrichment*). Al
iniciarse, el servicio verifica e inicializa la conexión con la base de datos.

### 5.6 Servicio de almacenamiento (Storage Service)

El servicio de almacenamiento (puerto 8004) está destinado a centralizar la
persistencia de los distintos artefactos del sistema: archivos crudos, JSON
estructurados, archivos SAV y datos de la base vectorial. En el estado actual
del desarrollo, este servicio se encuentra implementado como un componente
preliminar (*stub*) que expone únicamente el *endpoint* de salud (`/health`),
de modo que participa en la orquestación y puede iniciarse junto con el resto
del sistema, mientras su lógica de persistencia queda pendiente de
implementación en una etapa posterior.

### 5.7 Servicio de visualización (Visualization Service)

El servicio de visualización (puerto 8005) tiene como finalidad generar los
datos y las representaciones (gráficas, agregaciones e información para el
tablero) que consumirá el frontend. Al igual que el servicio de almacenamiento,
en el estado actual se encuentra implementado como un componente preliminar
(*stub*) que expone solo el *endpoint* de salud, quedando su lógica de
visualización pendiente de desarrollo. Su inclusión desde esta etapa permite
reservar su lugar dentro de la arquitectura y la orquestación del sistema.

---

## 6. Flujo de procesamiento e inteligencia del sistema

El procesamiento inteligente de los instrumentos constituye el núcleo funcional
de la plataforma y, por su importancia, se documenta en una sección propia. Este
flujo es el que permite transformar un instrumento cargado en conocimiento
accionable: primero se vectoriza su contenido semántico y se asocia
automáticamente con los indicadores (KPIs) pertinentes, y posteriormente ese
mismo contenido vectorizado habilita la consulta mediante recuperación aumentada
por generación (RAG). Toda esta lógica reside en el servicio de análisis y se
apoya en tres piezas: un modelo de *embeddings* (sentence-transformers), una
base de datos vectorial (ChromaDB) y el modelo de lenguaje servido por Ollama.

### 6.1 Visión general del flujo

El flujo se concibió en dos grandes etapas, separadas de forma deliberada por
una decisión humana. En la primera etapa, el sistema analiza un instrumento ya
procesado y propone los KPIs que considera relacionados, calculando para cada
uno un grado de similitud; el usuario revisa estas propuestas y decide cuáles
acepta. En la segunda etapa, una vez confirmados los KPIs, la información
vectorizada queda disponible para ser consultada en lenguaje natural. Esta
separación en dos pasos —proponer y confirmar— es intencional: garantiza que la
asociación final de indicadores siempre quede validada por una persona y no
dependa únicamente del juicio del modelo.

La siguiente tabla resume los *endpoints* que materializan el flujo en el
servicio de análisis:

| Etapa | Endpoint | Función |
|-------|----------|---------|
| Propuesta | `POST /vectorizacion/propuestas` | Vectoriza el instrumento y propone KPIs por similitud |
| Confirmación | `POST /vectorizacion/confirmar` | Persiste los KPIs aceptados y enriquece el JSON |
| Mantenimiento | `POST /vectorizacion/kpis/reindex` | Reindexa el catálogo de KPIs en la base vectorial |

### 6.2 Limpieza y estandarización de los instrumentos

Antes de que un instrumento pueda vectorizarse, debe atravesar dos etapas
previas que son determinantes para la calidad del resultado: la **limpieza** y
la **estandarización**. La limpieza aplica un procesamiento sencillo de ciencia
de datos sobre el instrumento cargado —depurando y normalizando su contenido—,
mientras que la estandarización lo transforma en una estructura homogénea
(un JSON estructurado) y lo enriquece con metadatos, de modo que instrumentos de
distinta procedencia queden representados de forma uniforme. Esta normalización
es la que permite que la posterior comparación semántica entre instrumentos y
KPIs sea consistente.

Técnicamente, estas etapas se reflejan en el campo `estado` de la tabla
`instrumento_procesado`, que actúa como control del avance del instrumento a lo
largo del pipeline. El estado evoluciona de forma secuencial a través de valores
como `recibido`, `limpieza_en_proceso`, `limpio`, `metadatos_registrados`,
`estandarizado` y, finalmente, `vectorizado`. El enriquecimiento de metadatos lo
coordina el servicio de metadata, que expone *endpoints* para crear las
propuestas de metadatos enriquecidos (`POST /enrichment/{id}/create`),
consultarlas y aprobarlas o rechazarlas (`POST /enrichment/{id}/approve`); una
vez aprobadas, el instrumento queda listo para la generación del JSON
estandarizado que alimentará la vectorización.

### 6.3 Construcción del *summary* y generación de *embeddings*

El primer paso del procesamiento consiste en preparar el texto que será
vectorizado. En lugar de vectorizar el instrumento completo, el sistema
construye un *summary*: un texto depurado que combina los metadatos clave del
instrumento con su versión original (únicamente las preguntas, sin las
respuestas de los participantes). Esta decisión es relevante, pues mantener el
texto limpio y centrado en lo semánticamente significativo es lo que permite que
la asociación de indicadores sea precisa; incluir las respuestas introduciría
ruido que degradaría la calidad de la búsqueda.

Una vez construido el *summary*, este se convierte en un vector numérico
(*embedding*) mediante un modelo multilingüe de la biblioteca
*sentence-transformers*. El modelo se carga de forma perezosa —solo la primera
vez que se necesita— y los vectores se normalizan, lo que resulta coherente con
el uso posterior de la similitud coseno como medida de cercanía.

### 6.4 Indexación en ChromaDB y asociación a KPIs

El vector del *summary* se almacena en una colección de la base de datos
vectorial ChromaDB destinada a los instrumentos. De forma paralela, el catálogo
de KPIs del sistema se mantiene vectorizado en una colección propia, que puede
regenerarse mediante el *endpoint* de reindexación cada vez que el catálogo se
actualiza.

La asociación de un instrumento con sus KPIs se realiza por búsqueda semántica:
el vector del *summary* se consulta contra la colección de KPIs y se recuperan
los más cercanos. Para cada candidato, la distancia coseno que devuelve ChromaDB
se transforma en un *score* de similitud en el rango de 0 a 1 (donde un valor
mayor indica mayor parecido), y únicamente se conservan los KPIs cuyo *score*
supera un umbral configurable. El resultado es una lista ordenada de KPIs
propuestos, cada uno acompañado de su grado de similitud, que se presenta al
usuario.

Cuando el usuario confirma los KPIs que acepta, el sistema los persiste en la
base de datos relacional: se registra la inferencia en la tabla `kpi_inferido`
y, de manera trazable, se guardan en `kpi_inferido_chunk` los fragmentos de
evidencia que sustentaron cada asociación junto con su *score*. Finalmente, el
JSON del instrumento se enriquece con los indicadores confirmados. De este modo,
cada KPI asociado queda respaldado por evidencia verificable y no por una
decisión opaca del sistema.

### 6.5 Consulta mediante RAG

La segunda etapa prevista del flujo es la consulta mediante recuperación
aumentada por generación (RAG), que reutiliza la misma base vectorial construida
en la etapa anterior. De manera general, su principio de funcionamiento consiste
en recuperar de ChromaDB los fragmentos de texto más relevantes para una
pregunta formulada en lenguaje natural y entregarlos como contexto al modelo de
lenguaje servido por Ollama, de modo que la respuesta generada se fundamente en
la información del propio sistema. El esquema de la base de datos ya contempla la
tabla `rag_log` para registrar estas consultas (pregunta, respuesta, modelo y
métricas asociadas).

Cabe precisar que esta funcionalidad se encuentra en una etapa temprana de
desarrollo: la infraestructura en la que se apoya —la base vectorial ChromaDB y
el modelo Ollama— ya forma parte de la orquestación del sistema, y actualmente
se trabaja en su integración con el frontend. No obstante, el flujo RAG aún no
opera en su totalidad, por lo que su implementación completa se contempla como
la continuación natural del trabajo descrito en este capítulo.

---

## 7. Implementación del frontend

La interfaz de usuario de la plataforma se desarrolló como una aplicación web de
una sola página (SPA) con React y TypeScript, construida sobre el framework
TanStack Start y la herramienta Vite. La totalidad de la interfaz se diseñó en
español —tanto los textos como los nombres de las rutas y del dominio en el
código— y se organizó siguiendo un enfoque por *features* (dominios), de modo
que cada área funcional del sistema reside en su propio módulo.

### 7.1 Estructura de componentes y organización por features

El código fuente del frontend se organiza, dentro de `src/`, separando la lógica
de cada dominio de los elementos reutilizables. El directorio `features/` agrupa
las áreas funcionales de la aplicación —autenticación, carga de instrumentos,
instrumentos, investigación, chat e indicadores (KPIs)—, cada una con sus
propios componentes y lógica. Los componentes de interfaz compartidos entre
distintas áreas se ubican en `components/`, siguiendo la convención de un
componente por archivo con sus propiedades (*props*) tipadas. Los tipos de
dominio comunes se centralizan en `types/`.

El enrutamiento se definió de manera declarativa mediante TanStack Router, cuyos
archivos de ruta residen en `routes/`. La aplicación emplea un *layout* global
—la ruta de panel— del que dependen las distintas pantallas internas del
sistema: la carga de un nuevo instrumento, el listado de instrumentos, la
investigación, los KPIs y el chat.

### 7.2 Integración con la API

Una de las decisiones de diseño más relevantes del frontend es que las pantallas
nunca acceden directamente a los datos: toda interacción con información se
canaliza a través de una capa dedicada en `api/`. Cada módulo de esta capa
expone funciones asíncronas (que devuelven promesas), de manera que la interfaz
depende de esas firmas y no de su implementación interna. Gracias a ello, es
posible sustituir los datos de ejemplo (ubicados en `mocks/`) por llamadas HTTP
reales al backend sin modificar las pantallas; basta con reemplazar el cuerpo de
las funciones de la capa `api/`.

El acceso al backend se concentra en un cliente HTTP común. Este cliente define
la dirección base del API Gateway (configurable mediante variables de entorno),
un ayudante genérico para realizar las peticiones y la gestión del token de
autenticación. Cuando el usuario inicia sesión, el token JWT devuelto por el
backend se almacena de forma persistente (en `localStorage`, con respaldo en
memoria) y se adjunta de manera automática —en la cabecera de autorización— a
las peticiones que así lo requieren. El cliente también centraliza el manejo de
errores: traduce los códigos de respuesta HTTP a mensajes claros en español, de
modo que, por ejemplo, un intento de inicio de sesión fallido se presenta al
usuario con un mensaje comprensible.

> **Nota sobre el estado de integración.** La integración de la autenticación y
> de las operaciones principales con el backend se encuentra en marcha. En el
> caso particular de la consulta mediante RAG (descrita en la sección 6.5), su
> conexión con el frontend apenas se está incorporando y aún no opera en su
> totalidad.

### 7.3 Estilos y experiencia de usuario

El diseño visual de la interfaz se apoya en Tailwind CSS, complementado con una
biblioteca de componentes accesibles basada en Radix UI, lo que proporciona
elementos de interfaz consistentes (diálogos, menús, pestañas, formularios,
entre otros). Para preservar la coherencia visual, los colores, la tipografía y
las sombras se definieron exclusivamente como *tokens* semánticos centralizados
en la hoja de estilos principal (`styles.css`), evitando el uso de valores de
color literales en los componentes. Este enfoque facilita el mantenimiento de la
identidad visual y permite ajustar el aspecto de toda la aplicación desde un
único punto.

---

## 8. Integración de los componentes

Una vez construidos los componentes de manera independiente, la integración
consistió en hacerlos operar como un sistema único y coherente. Esta sección
describe los mecanismos transversales que atraviesan a todos los servicios: la
autenticación de los usuarios, la protección de sus datos, el recorrido completo
de una operación a través del sistema y la estrategia de manejo de errores.

### 8.1 Autenticación y manejo de usuarios

La autenticación del sistema se centraliza en el API Gateway y se basa en tokens
JSON Web Token (JWT). El flujo completo opera de la siguiente manera:

1. **Inicio de sesión.** El usuario envía su correo y contraseña al *endpoint*
   `POST /auth/login`. El servicio busca al usuario por su correo y verifica la
   contraseña recibida contra el *hash* almacenado. Si las credenciales son
   correctas, genera un token JWT firmado; en caso contrario, responde con un
   error de autenticación (código HTTP 401).

2. **Generación del token.** El token se firma con una clave secreta
   (`SECRET_KEY`) mediante el algoritmo HS256 e incluye, como información
   (*claims*), el identificador del usuario, su rol y la fecha de expiración.
   De este modo, el token funciona como una credencial autocontenida y con
   vigencia limitada.

3. **Acceso a recursos protegidos.** En las peticiones subsecuentes, el token se
   envía en la cabecera de autorización (`Authorization: Bearer <token>`). Una
   dependencia del gateway lo valida —comprobando su firma y vigencia— y, a
   partir de él, identifica al usuario. Si el token es inválido o ha expirado,
   la petición se rechaza con un error 401.

4. **Autorización por rol.** El sistema define un vocabulario cerrado de dos
   roles: *investigador* y *administrador*. Determinadas operaciones exigen un
   rol específico; por ejemplo, el alta de nuevos usuarios
   (`POST /auth/register`) está reservada al administrador. Cuando un usuario
   autenticado carece del rol necesario, la operación se rechaza con un error de
   permisos (código HTTP 403).

Un aspecto relevante del diseño es que los tokens son *autocontenidos* y de
validación independiente: cualquier servicio puede verificar un token con la
misma clave secreta, sin necesidad de consultar la base de datos ni de invocar
nuevamente al gateway. Esto simplifica la comunicación entre microservicios y
evita acoplamientos innecesarios.

### 8.2 Privacidad y protección de datos de los usuarios

La protección de los datos de los usuarios se abordó mediante varias medidas
concretas aplicadas durante la implementación:

- **Cifrado de contraseñas.** Las contraseñas nunca se almacenan en texto plano.
  Al dar de alta a un usuario, la contraseña se transforma mediante el algoritmo
  de *hashing* **bcrypt**, y únicamente se guarda ese *hash* en la base de
  datos. Durante el inicio de sesión, la contraseña recibida se compara contra
  el *hash* almacenado, sin que el valor original llegue a persistirse en ningún
  momento.

- **Defensa frente a la enumeración de cuentas.** El proceso de autenticación se
  diseñó para verificar siempre un *hash* de contraseña, incluso cuando el
  correo no corresponde a ningún usuario registrado. Con ello se evita que las
  diferencias en el tiempo de respuesta revelen si un correo determinado existe
  o no en el sistema, una medida básica contra los intentos de enumeración de
  usuarios.

- **Control de acceso basado en roles.** Como se describió, el acceso a las
  operaciones sensibles —como el alta de usuarios o el borrado de instrumentos—
  se restringe según el rol del usuario. El sistema no emplea una tabla de
  permisos independiente, sino que la autorización se valida en la capa de
  aplicación a partir del rol.

- **Minimización de datos.** De cada usuario se almacena únicamente la
  información necesaria para la operación del sistema: nombre, correo electrónico
  (único), el *hash* de la contraseña, el rol y la fecha de registro. No se
  recopilan datos personales adicionales.

### 8.3 Flujo de datos de extremo a extremo

Para ilustrar cómo se integran los componentes, puede seguirse el recorrido de
una operación típica. La petición se origina en el frontend, que la dirige al
API Gateway adjuntando, cuando corresponde, el token de autenticación. El
gateway valida la credencial y, según la naturaleza de la operación, la atiende
directamente —en el caso de la autenticación— o la encamina hacia el
microservicio responsable. El servicio correspondiente ejecuta la lógica de
negocio y accede a la base de datos PostgreSQL —o, en el caso del procesamiento
inteligente, a la base vectorial ChromaDB— para leer o persistir la información.
Finalmente, la respuesta recorre el camino inverso hasta el frontend, que la
presenta al usuario. El intercambio de datos se realiza en todo momento en
formato JSON a través de la red interna que conecta a los contenedores.

### 8.4 Manejo de errores y validaciones

El sistema aplica una estrategia de validación y manejo de errores en varias
capas. En el backend, la validación de los datos de entrada se apoya en los
esquemas de *Pydantic*, que garantizan que las peticiones cumplan con la
estructura y los tipos esperados antes de ser procesadas; las violaciones de
estas reglas se traducen en respuestas de error con el código HTTP
correspondiente (por ejemplo, 422 para datos no válidos o 409 para conflictos
como un correo duplicado). En el frontend, el cliente HTTP centraliza la
interpretación de estos códigos y los traduce a mensajes claros en español,
de modo que el usuario reciba una retroalimentación comprensible ante
situaciones como credenciales incorrectas o errores de validación.

---

## 9. Containerización y despliegue local
[Cómo se empaquetó y ejecutó el sistema. En tu caso: Docker y docker-compose.]

### 9.1 Imágenes Docker de cada servicio
[Explicación de los Dockerfiles: imagen base, dependencias, puertos.]

### 9.2 Orquestación con docker-compose
[Definición de servicios, redes, volúmenes y dependencias entre contenedores.]

### 9.3 Variables de entorno y configuración
[Manejo de configuración y secretos mediante archivos de entorno.]

---

## 10. Dificultades técnicas y soluciones
[Problemas relevantes durante la construcción y cómo se resolvieron.
Aporta madurez y pensamiento crítico al trabajo.]

---

## 11. Conclusión del capítulo
[Cierre: resume lo construido y enlaza con el siguiente capítulo
(pruebas, resultados o conclusiones).]

---

## Anexos del capítulo (opcional)
[Fragmentos extensos de código, Dockerfiles completos, scripts de base de datos
y diccionario de datos que resulten demasiado largos para el cuerpo del texto.]
