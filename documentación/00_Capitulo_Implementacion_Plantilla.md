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

### 6.2 Construcción del *summary* y generación de *embeddings*

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

### 6.3 Indexación en ChromaDB y asociación a KPIs

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

### 6.4 Consulta mediante RAG

La segunda gran etapa del flujo es la consulta mediante recuperación aumentada
por generación (RAG), que aprovecha la misma base vectorial construida en la
etapa anterior. El principio de funcionamiento es el siguiente: ante una
pregunta formulada en lenguaje natural, el sistema recupera de ChromaDB los
fragmentos de texto más relevantes para esa pregunta y los proporciona como
contexto al modelo de lenguaje servido por Ollama, el cual genera una respuesta
fundamentada en dicho contexto. Cada consulta se registra en la tabla `rag_log`,
que conserva la pregunta, la respuesta, el modelo utilizado, el número de
fragmentos empleados y la latencia, lo que permite auditar y evaluar el
comportamiento del sistema.

> **Nota sobre el estado de implementación.** En el estado actual del
> desarrollo, el núcleo de vectorización e inferencia de KPIs descrito en las
> secciones 6.2 y 6.3 se encuentra implementado y operativo. La consulta RAG
> aquí descrita corresponde a la etapa diseñada que se apoya en la misma
> infraestructura vectorial (ChromaDB) y en el modelo de lenguaje (Ollama) ya
> integrados en la orquestación; su implementación completa se contempla como la
> continuación natural de este flujo.

---

## 7. Implementación del frontend
[Cómo se construyó la interfaz y su conexión con el backend.]

### 7.1 Estructura de componentes
[Organización de componentes, páginas y recursos (assets).]

### 7.2 Integración con la API
[Consumo de los endpoints del API Gateway, manejo de estado y de errores.]

### 7.3 Estilos y experiencia de usuario
[Hojas de estilo, framework de UI, recursos visuales.]

---

## 8. Integración de los componentes
[Cómo se unieron todas las piezas para funcionar como un solo sistema.]

### 8.1 Autenticación y manejo de usuarios
[Flujo completo de autenticación paso a paso: registro/login, generación y
validación de tokens (JWT), cifrado de contraseñas (bcrypt), y protección de
los endpoints a través del API Gateway.]

### 8.2 Privacidad y protección de datos de los usuarios
[Qué datos del usuario se almacenan, cómo se protegen (cifrado de contraseñas,
control de acceso) y qué consideraciones de privacidad se aplicaron.]

### 8.3 Flujo de datos de extremo a extremo
[Recorrido de una operación completa: desde el frontend, por el gateway,
hasta el servicio y la base de datos, y de regreso.]

### 8.4 Manejo de errores y validaciones
[Estrategia global de errores y validación de datos.]

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
