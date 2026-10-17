# Capítulo: Desarrollo

> Versión actualizada a partir de `00_Capitulo_Implementacion_Plantilla.md`.
> Se conservó la redacción original donde seguía vigente y se actualizó lo que
> cambió en el código: los microservicios de limpieza (`cleaning-service`) y de
> conocimiento (`knowledge-service`), la implementación completa de los
> servicios de almacenamiento y visualización, el RAG en operación y la nueva
> asociación de KPIs por unidades. Las notas entre corchetes `[...]` marcan
> datos que conviene confirmar o referencias cruzadas por completar.

---

## 1. Introducción del capítulo

Este capítulo describe la construcción de Indagata, la plataforma para gestionar
y consultar instrumentos de investigación educativa (encuestas, entrevistas y
pruebas estandarizadas). Mientras que el capítulo de Diseño definió la
arquitectura, el modelo de datos y la interfaz, aquí el foco está en **cómo se
materializaron** esas decisiones: las tecnologías empleadas, la organización del
código, la implementación de cada componente y los mecanismos que los integran
en un sistema único.

El capítulo se organiza de la siguiente manera. La sección 2 presenta el entorno
y las herramientas de desarrollo, y la sección 3 la estructura del repositorio.
La sección 4 aborda la base de datos, cimiento del resto del sistema. La sección
5 describe cada uno de los ocho microservicios del *backend*, y la sección 6
recorre el flujo de procesamiento que transforma un archivo cargado en
conocimiento consultable: limpieza asistida, metadatos, perfil semántico,
asociación de indicadores (KPIs), documento final, indexación vectorial y
consulta mediante RAG. La sección 7 trata la interfaz de usuario; la sección 8,
los mecanismos transversales de integración (autenticación, privacidad y manejo
de errores), y la sección 9, la contenerización y el despliegue local. El
capítulo cierra con las dificultades técnicas enfrentadas y sus soluciones
(sección 10) y una conclusión (sección 11).

### 1.1 Objetivo de la implementación

El objetivo de la implementación fue construir una plataforma funcional que
permita a un investigador cargar un instrumento, depurarlo con apoyo del
sistema, describirlo con metadatos estandarizados, asociarlo a los indicadores
educativos pertinentes y, finalmente, consultarlo en lenguaje natural junto con
el resto del acervo. Dos principios guiaron toda la construcción:

- **La decisión final es humana.** El sistema analiza, sugiere y preselecciona,
  pero cada paso que modifica el significado del instrumento —qué se limpia, qué
  metadatos se aprueban, qué KPIs se aceptan— queda confirmado por el
  investigador.
- **Trazabilidad completa.** Cada transformación queda registrada: el archivo
  crudo nunca se modifica, cada repetición de un proceso genera una versión
  nueva y cada KPI aceptado conserva la evidencia que lo sustenta.

[Enlazar aquí con los objetivos específicos de la tesis: ver Capítulo X, sección Y.]

### 1.2 Relación con el capítulo de Diseño

La implementación respeta la arquitectura de microservicios definida en el
capítulo de Diseño [ver Capítulo X, sección Y]: servicios independientes
desarrollados en Python con FastAPI, una base de datos relacional compartida
(PostgreSQL), una base de datos vectorial (ChromaDB), un modelo de lenguaje
local (Ollama) y una interfaz web en React que se comunica con el *backend* a
través de una puerta de enlace única (*API Gateway*).

Durante la construcción, el diseño original se extendió en dos puntos que
conviene adelantar al lector, pues se detallan a lo largo del capítulo:

1. Se incorporó un **servicio de limpieza** (`cleaning-service`) entre la carga
   del instrumento y el registro de metadatos, de modo que los metadatos se
   calculen siempre sobre datos depurados.
2. Se incorporó un **servicio de conocimiento** (`knowledge-service`) que separa
   los distintos usos del JSON del instrumento: un *perfil semántico* acotado
   para asociar KPIs y un *documento final* completo, con las respuestas
   interpretadas, como insumo del RAG.

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

**Backend (microservicios).** Los servicios que conforman el *backend* se
desarrollaron en el lenguaje **Python 3.12**, utilizando el framework
**FastAPI** para la construcción de las APIs y **Uvicorn** como servidor de
aplicaciones. Para la validación de datos y la gestión de la configuración se
emplearon **Pydantic** y *Pydantic Settings*, mientras que el acceso a la base de
datos se realizó mediante el ORM **SQLAlchemy** junto con el controlador
**psycopg**. La comunicación entre servicios se apoyó en el cliente HTTP
**httpx**, y la autenticación se implementó con *python-jose* (tokens JWT) y
*passlib/bcrypt* (cifrado de contraseñas). La lectura de los formatos de archivo
admitidos se resolvió con *openpyxl* y *xlrd* (hojas de cálculo), *pypdf* (PDF)
y *python-docx* (Word). Las reglas editables de limpieza y de interpretación se
expresan en archivos YAML, leídos con *PyYAML*, y los documentos finales se
validan con *jsonschema*.

**Componentes de análisis e inteligencia artificial.** El procesamiento de
lenguaje natural se apoya en tres piezas: el modelo de *embeddings*
multilingüe **paraphrase-multilingual-mpnet-base-v2** (vectores de 768
dimensiones), ejecutado con la librería **sentence-transformers** sobre
*PyTorch* en CPU; la base de datos vectorial **ChromaDB**, que almacena y
consulta los vectores por similitud de coseno, y el modelo de lenguaje
**Llama 3.2 de 3 mil millones de parámetros** (`llama3.2:3b`), servido
localmente por **Ollama** con aceleración por GPU. Los cálculos estadísticos
de la limpieza se implementaron con **NumPy**, y la exportación al formato de
SPSS (`.sav`) con *pandas* y *pyreadstat*.

**Frontend.** La interfaz de usuario se desarrolló con **React 19** y
**TypeScript**, sobre el framework **TanStack Start** (con TanStack Router para
el enrutamiento y TanStack Query para la gestión de datos remotos) y **Vite**
como herramienta de construcción y servidor de desarrollo. Los estilos se
definieron con **Tailwind CSS 4**, y los componentes de interfaz accesibles se
tomaron de la colección *shadcn/ui*, construida sobre **Radix UI**. Las
animaciones se implementaron con **Motion**, las gráficas con **Recharts** y la
visualización del espacio vectorial con módulos de **D3** (escalas, *zoom*,
contornos y triangulación de Delaunay).

**Base de datos y almacenamiento.** Como sistema gestor de base de datos
relacional se utilizó **PostgreSQL 16**. Los archivos (crudos, limpios, JSON y
exportaciones) se almacenan en disco bajo la administración exclusiva del
servicio de almacenamiento. La orquestación incluye además **Redis 7** como
almacén en memoria, aunque en el estado actual la caché de lecturas del servicio
de almacenamiento se resuelve dentro del propio proceso. [Confirmar si Redis se
usará en una etapa posterior o si conviene retirarlo de la orquestación.]

La siguiente tabla resume el conjunto de tecnologías empleadas, organizadas por
capa:

| Capa | Tecnología | Versión / detalle |
|------|------------|-------------------|
| Lenguaje backend | Python | 3.12 |
| Framework de APIs | FastAPI | 0.115.6 |
| Servidor de aplicaciones | Uvicorn | 0.30.0 |
| ORM / acceso a datos | SQLAlchemy + psycopg | 2.0.25 / 3.2.3 |
| Validación y configuración | Pydantic + Pydantic Settings | 2.9.0 / 2.5.0 |
| Comunicación entre servicios | httpx | 0.27.0 |
| Autenticación | python-jose + passlib/bcrypt | 3.3.0 / 1.7.4 |
| Lectura de archivos | openpyxl, xlrd, pypdf, python-docx | 3.1.2 / 2.0.1 / 4.1.0 / 1.1.0 |
| Reglas editables y validación | PyYAML + jsonschema | 6.0.2 / 4.23.0 |
| Cálculo numérico | NumPy | 1.26.4 |
| Exportación SPSS | pandas + pyreadstat | 2.2.2 / 1.2.7 |
| Modelo de lenguaje | Ollama + Llama 3.2 | `llama3.2:3b` |
| Base de datos vectorial | ChromaDB (cliente HTTP) | 1.0.0 |
| Embeddings | sentence-transformers + PyTorch (CPU) | 3.0.0 / 2.2.2 |
| Modelo de embeddings | paraphrase-multilingual-mpnet-base-v2 | 768 dimensiones |
| Biblioteca de frontend | React + TypeScript | 19.2 / 5.8 |
| Framework de frontend | TanStack Start / Router / Query | 1.168 / 1.170 / 5.x |
| Herramienta de construcción | Vite | 8.1 |
| Estilos y componentes | Tailwind CSS + shadcn/ui (Radix UI) | 4.2 |
| Animación y gráficas | Motion, Recharts, D3 | 14.x / 2.15 / — |
| Base de datos relacional | PostgreSQL | 16 |
| Caché en memoria | Redis | 7 |
| Contenedores | Docker + Docker Compose | — |

### 2.2 Control de versiones y gestión del código

El desarrollo del sistema se gestionó mediante el sistema de control de
versiones **Git**, que permitió llevar un registro histórico de los cambios y
mantener la trazabilidad del trabajo realizado. El código fuente se organizó en
un repositorio con una estructura *monorepo*, en la que conviven, dentro de un
mismo proyecto, los microservicios del *backend*, la interfaz de usuario, la
infraestructura y los scripts de la base de datos. Este enfoque facilitó la
coordinación entre componentes y simplificó la gestión de las dependencias
compartidas entre servicios.

El trabajo se organizó en ramas. Las funcionalidades nuevas se desarrollaron en
ramas de trabajo (por ejemplo, la integración de la interfaz con el *backend* y
la limpieza de instrumentos) y se integraron en la rama `pruebas`, que concentra
la versión funcional del sistema, mientras la rama de refactorización de
microservicios se conservó como referencia. [Ajustar a la estrategia de ramas
definitiva del equipo.]

### 2.3 Convenciones de codificación

Durante la construcción del sistema se siguieron convenciones orientadas a
mantener la legibilidad y la coherencia del código:

- **Idioma.** El código, los identificadores, las rutas de la API, los textos de
  la interfaz y la documentación se escribieron en español, de modo que el
  vocabulario del dominio (instrumento, reactivo, respondente, limpieza) sea el
  mismo en todas las capas.
- **Estilo.** En el *backend* se adoptó la nomenclatura estándar de Python
  (*snake_case* para variables y funciones, *PascalCase* para clases), conforme
  a la guía de estilo PEP 8. En el *frontend* se siguió la convención de un
  componente por archivo, con sus propiedades (*props*) tipadas.
- **Capas.** Todos los servicios siguen la misma secuencia de capas: los
  enrutadores (*routers*) reciben la petición, las dependencias tipadas
  (*dependencies*) resuelven la sesión de base de datos y el usuario
  autenticado, los servicios (*services*) contienen la lógica de negocio y los
  modelos compartidos (*shared*) acceden a los datos.
- **Documentación en el código.** Cada módulo inicia con un comentario que
  explica su propósito y, cuando aplica, el razonamiento detrás de sus reglas.
  Las funciones y clases relevantes se documentan con *docstrings*.
- **Reglas fuera del código.** Los umbrales, las expresiones regulares y los
  diccionarios que un investigador podría querer ajustar (por ejemplo, las
  escalas Likert reconocidas) se definieron en archivos YAML, de modo que
  puedan modificarse sin tocar el código.
- **Fuente única de verdad del esquema.** El script SQL de la base de datos es
  la referencia: si un modelo del ORM difiere de él, se corrige el modelo, nunca
  el SQL.

Cada microservicio constituye un módulo independiente, con sus propias
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
├── services/                  # Microservicios que conforman el backend
│   ├── api-gateway/            # Autenticación y enrutamiento de peticiones
│   ├── instrument-service/     # Carga y registro de instrumentos
│   ├── cleaning-service/       # Limpieza automática y asistida
│   ├── metadata-service/       # Dublin Core, metadatos del tipo y JSON técnico
│   ├── knowledge-service/      # Perfil semántico, interpretación y documento final
│   ├── analysis-service/       # Embeddings y asociación de KPIs
│   ├── storage-service/        # Archivos, versiones e ingesta a ChromaDB
│   └── visualization-service/  # Catálogo, tableros, espacio vectorial y chat RAG
├── shared/                    # Código común reutilizado por los servicios
│   ├── auth/                   # JWT de usuario, roles y tokens de servicio
│   ├── config/                 # Reglas compartidas (escalas Likert)
│   ├── db/                     # Conexión, sesión y configuración única
│   ├── models/                 # Modelos del ORM (espejo del esquema SQL)
│   ├── parsing/                # Lectores de CSV, XLSX, PDF, DOCX y TXT
│   ├── repositories/           # Acceso a datos (patrón repositorio)
│   └── schemas/                # Esquemas de validación (Pydantic)
├── pixel-perfect-pixel/       # Interfaz de usuario (frontend)
│   └── src/
│       ├── routes/             # Rutas de la aplicación (TanStack Router)
│       ├── features/           # Módulos por dominio
│       ├── components/         # Componentes compartidos y de interfaz
│       ├── api/                # Capa de acceso a datos / API
│       ├── types/              # Tipos de dominio compartidos
│       ├── mocks/              # Datos de ejemplo aún no conectados
│       └── styles.css          # Tokens de estilo (color, tipografía, sombras)
├── infrastructure/            # Configuración de infraestructura
│   ├── docker/                 # Dockerfiles de cada servicio
│   ├── postgres/               # Esquema, migraciones y datos semilla
│   └── chroma-viewer/          # Visor de solo lectura de la base vectorial
├── storage/                   # Volumen de almacenamiento de archivos
├── markdowns/                 # Guías técnicas y para investigadores
├── documentación/             # Capítulos de la tesis
├── docker-compose.yml         # Orquestación de todos los contenedores
├── CLAUDE.md                  # Guía técnica del repositorio
└── .env.example               # Plantilla de variables de entorno
```

La estructura responde a una separación clara de responsabilidades:

- **`services/`** agrupa los ocho microservicios que componen el *backend*. Cada
  uno constituye un módulo independiente, con su propio archivo de dependencias
  (*requirements.txt*) y su punto de entrada (*main.py*). Coexisten dos
  organizaciones internas: los servicios más antiguos (*api-gateway*,
  *instrument-service* y *analysis-service*) agrupan su código en un paquete
  `app/`, mientras que los demás usan una organización plana, con los
  directorios `routers/` y `services/` y los archivos `models.py` y
  `dependencies.py` en la raíz del servicio. Ambas organizaciones siguen la
  misma secuencia de capas descrita en la sección 2.3.

- **`shared/`** contiene el código común que se reutiliza en los distintos
  servicios, evitando la duplicación. Aquí se concentran la autenticación
  (*auth*), la configuración única de todos los servicios y sus vocabularios
  cerrados (*db/core*), los modelos del ORM (*models*), los esquemas de
  validación (*schemas*), los lectores de archivos que comparten la carga y la
  limpieza (*parsing*) y las reglas que usan dos o más servicios, como el
  diccionario de escalas Likert (*config*). Como los contenedores solo comparten
  esta carpeta, cualquier recurso que deban leer varios servicios debe residir
  en ella.

- **`pixel-perfect-pixel/`** aloja la interfaz de usuario, desarrollada como una
  aplicación de React con TypeScript sobre TanStack Start y Vite. Su código se
  organiza por *features* (dominios): autenticación, inicio, carga de
  instrumentos, instrumentos, investigación, chat, KPIs, espacio vectorial y
  gestión de usuarios. Su organización se detalla en la sección 7.

- **`infrastructure/`** reúne todo lo relacionado con el despliegue: los
  *Dockerfiles* de cada servicio; los scripts de PostgreSQL (esquema,
  migraciones con su reversión y datos semilla, incluido el catálogo de KPIs en
  CSV), y un visor web independiente que proyecta en dos dimensiones el
  contenido de ChromaDB para inspeccionarlo durante el desarrollo.

- **`storage/`** es el directorio de persistencia de los archivos que maneja el
  sistema. Los datos de PostgreSQL, ChromaDB, Ollama y la caché de modelos de
  *embeddings* residen en volúmenes de Docker.

- **`markdowns/`** contiene la documentación técnica del proyecto y las guías
  para investigadores, como la explicación de las medidas estadísticas de la
  limpieza.

- En la raíz del proyecto se ubican el archivo **`docker-compose.yml`**, que
  orquesta la ejecución conjunta de todos los contenedores; la plantilla de
  variables de entorno (**`.env.example`**), y una guía técnica del repositorio
  (**`CLAUDE.md`**) que resume la arquitectura, los puertos y las convenciones.

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
sistema del resto de la base de datos. Los modelos del ORM (`shared/models`) y
los esquemas de validación (`shared/schemas`) reflejan este script uno a uno.

El modelo de datos refleja directamente el flujo de procesamiento de la
plataforma, que parte de la recepción de un instrumento en crudo y culmina con
su documento final, su vectorización y la inferencia de indicadores (KPIs). Las
tablas pueden agruparse de la siguiente manera según su responsabilidad:

**Usuarios y control de acceso.** La tabla `usuario` almacena los datos de las
cuentas, incluyendo el correo electrónico (único), la contraseña cifrada
(`password_hash`) y el rol del usuario. El rol es el que autoriza las
operaciones de carga y borrado de instrumentos; el sistema no emplea una tabla
de permisos, sino que la validación se realiza en la capa de aplicación.

**Datos de los instrumentos.** La tabla `raw_data` es la tabla padre del modelo:
registra cada instrumento recibido en crudo y conserva la ruta del archivo
respondido, la del instrumento original sin respuestas (destinado al análisis
semántico) y, en las pruebas estandarizadas tabulares, la de la clave de
respuestas (`raw_archivo_clave`). De ella derivan, mediante relaciones de clave
foránea, la tabla `instrumento_procesado` —que representa el instrumento
procesado y lleva el control de su estado dentro del *pipeline*— y las tablas de
metadatos: `metadatos_dc`, basada en el estándar Dublin Core, y las tablas de
metadatos especializadas por tipo de instrumento
(`metadatos_enriquecidos_encuestas`, `..._entrevistas` y `..._pruebas`).

**Limpieza.** La tabla `limpieza_ejecucion` registra cada ejecución de la
limpieza de un instrumento como una versión numerada. Guarda su estado
(`esperando_decisiones`, `confirmada` o `fallida`), el investigador que la
realizó, las fechas de cada etapa, la ruta del CSV limpio y el *reporte de
limpieza* completo en una columna JSONB, con las transformaciones aplicadas, los
hallazgos, las decisiones del investigador y las métricas antes y después. Una
restricción `UNIQUE (id_crudo, version)` impide duplicar versiones.

**Conocimiento del instrumento.** La tabla `version_conocimiento` registra, en
una sola fila por versión, todo lo que el sistema construye a partir de un
instrumento ya limpio y con metadatos aprobados: el *perfil semántico* (JSONB),
las decisiones sobre los KPIs —aceptados y rechazados, con su puntaje, su
evidencia y su justificación— (JSONB) y el registro del documento final (ruta en
el almacenamiento, versión del esquema, avisos y su huella SHA-256). Su estado
avanza de `perfil_aprobado` a `kpis_confirmados`, `borrador` y `vigente`; al
publicar una versión nueva, la anterior pasa a `reemplazado`. Concentrar estas
tres etapas en una sola tabla, en lugar de crear una por artefacto, simplificó
el modelo sin perder la trazabilidad.

**Indicadores y variables.** Las tablas `kpi`, `variable` y la tabla puente
`kpi_variable` definen el catálogo de indicadores del sistema y las variables
que los componen. Cada KPI conserva, además de su nombre y su fórmula, una
descripción educativa ampliada, su comportamiento direccional y el texto de
contexto que se vectoriza (`texto_contexto_rag_vectorial`). Los resultados de la
asociación se almacenan en `kpi_inferido` y `valor_variable_inferido`.

**Vectorización y RAG.** Las tablas `coleccion_vectorial`,
`documento_vectorizado`, `kpi_inferido_chunk`, `prompts` y `rag_log` dan soporte
al núcleo de inteligencia del sistema. Estas tablas no almacenan los vectores en
sí —estos residen en ChromaDB—, sino las referencias a ellos (identificadores
de colección y de vector), los fragmentos de texto (*chunks*) de cada
instrumento, la evidencia que sustenta cada KPI inferido y el registro de las
consultas RAG (pregunta, respuesta, modelo, número de fragmentos y latencia).

El control de la integridad referencial se garantizó mediante claves foráneas
con borrado en cascada (`ON DELETE CASCADE`), de modo que al eliminar un
instrumento se eliminen también sus metadatos, limpiezas, versiones de
conocimiento, *chunks* e inferencias. Los valores de estado se restringieron con
cláusulas `CHECK` y se definieron índices sobre las columnas de uso más
frecuente (propietario, estado de procesamiento, relaciones con KPIs y *chunks*,
y las combinaciones instrumento–estado de las tablas de limpieza y de
conocimiento) con el fin de optimizar el rendimiento de las consultas.

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

El catálogo de indicadores se carga por separado desde el archivo
`KPI_Ampliacion.csv`, que funciona como fuente de verdad del catálogo. El script
`seed_kpis.py` del servicio de análisis lee ese archivo, inserta los KPIs en la
tabla `kpi` y genera sus *embeddings* en la colección `kpis` de ChromaDB. El
catálogo actual contiene 55 indicadores. [Confirmar la cifra si el catálogo
cambia.]

### 4.3 Migraciones y evolución del esquema

Puesto que los scripts de inicialización únicamente se ejecutan en el primer
arranque de la base de datos, los cambios posteriores al esquema se gestionaron
mediante scripts de migración independientes, ubicados en el directorio
`migrations`, que se montan en el contenedor de PostgreSQL y se aplican de forma
manual. Estos scripts se construyeron de forma idempotente, lo que permite
ejecutarlos varias veces sin provocar errores ni inconsistencias, y cada uno
cuenta con un script de reversión (*rollback*) que deshace sus cambios.

A lo largo del desarrollo se aplicaron tres migraciones principales:

| Migración | Cambios |
|-----------|---------|
| `2026_09_sis_integration` | Estados adicionales del *pipeline*, columnas nuevas en tablas existentes y migración de los datos previos al nuevo esquema |
| `2026_10_limpieza` | Tabla `limpieza_ejecucion` y columna `raw_data.raw_archivo_clave` |
| `2026_11_conocimiento` | Tabla `version_conocimiento` |

Tras aplicar cada migración se actualizaron, en el mismo cambio, el script
`01_schema.sql`, los modelos del ORM y los esquemas de validación, y se
documentó el cambio en `SCHEMA_CHANGES.md`. Este procedimiento posibilitó la
evolución controlada del modelo de datos, preservando la información ya
almacenada y manteniendo una base nueva idéntica a una base migrada.

---

## 5. Implementación de los microservicios

El *backend* de la plataforma se construyó como un conjunto de microservicios
independientes, cada uno responsable de una parte específica del dominio. Todos
se desarrollaron con la misma base tecnológica —Python y FastAPI— y siguen una
estructura homogénea: un punto de entrada (`main.py`) que crea la aplicación,
configura el registro de eventos (*logging*) y el *middleware* de CORS, y agrupa
los *endpoints* en enrutadores según su función. Cada servicio escucha en un
puerto propio y expone un *endpoint* `GET /health` que permite verificar su
disponibilidad.

### 5.1 Visión general y comunicación entre servicios

La comunicación entre los servicios se realiza mediante peticiones HTTP sobre
una API de tipo REST, utilizando JSON para el intercambio de datos. Cada
servicio se ejecuta en su propio contenedor y se comunica con los demás a través
de la red interna definida en la orquestación, empleando como dirección el
nombre del servicio en lugar de direcciones fijas. El API Gateway actúa como
punto de entrada del sistema: recibe las peticiones del *frontend* y las
redirige al servicio correspondiente. La siguiente tabla resume los servicios,
su puerto y su responsabilidad:

| Servicio | Puerto | Responsabilidad principal |
|----------|--------|---------------------------|
| API Gateway | 8000 (8006 en el anfitrión) | Autenticación y punto de entrada |
| Instrument Service | 8001 | Carga, validación y registro de instrumentos |
| Analysis Service | 8002 | Embeddings y asociación de KPIs |
| Metadata Service | 8003 | Dublin Core, metadatos del tipo y JSON técnico |
| Storage Service | 8004 | Archivos versionados e ingesta a ChromaDB |
| Visualization Service | 8005 | Catálogo, tableros, espacio vectorial y chat RAG |
| Cleaning Service | 8007 | Limpieza automática y asistida |
| Knowledge Service | 8009 | Perfil semántico, interpretación y documento final |

Junto a los microservicios se ejecutan los servicios de infraestructura:
PostgreSQL (5432), ChromaDB (8000 interno, 8008 en el anfitrión), Ollama
(11434), Redis (6379) y el visor de la base vectorial (8085).

### 5.2 API Gateway

El API Gateway (puerto 8000) constituye la puerta de entrada del sistema y
cumple dos funciones. La primera es la **autenticación**, mediante tokens JWT:

- `POST /auth/login`: recibe el correo y la contraseña del usuario y, de ser
  válidos, devuelve un token JWT.
- `GET /auth/me`: devuelve los datos del usuario asociado al token recibido.
- `POST /auth/register`: da de alta a un nuevo usuario, operación reservada al
  administrador.

La segunda es el **enrutamiento** (*proxy*) hacia los demás servicios. El
*gateway* reenvía cada petición según el prefijo de su ruta, sin renombrarla ni
envolver la respuesta: los códigos de estado y los cuerpos llegan intactos al
*frontend*. Conserva la cabecera de autorización y devuelve las cabeceras que
acompañan a las descargas (nombre del archivo y su huella SHA-256). La
correspondencia entre prefijos y servicios es la siguiente:

| Prefijo | Servicio destino |
|---------|------------------|
| `/instrumentos/*` | Instrument Service |
| `/limpieza/*` | Cleaning Service |
| `/api/metadata/*`, `/api/enrichment/*` | Metadata Service |
| `/conocimiento/*` | Knowledge Service |
| `/visualizacion/*`, `/rag/*` | Visualization Service |
| `/almacenamiento/*` | Storage Service (solo administradores) |

Cada prefijo registra dos rutas explícitas: la base (por ejemplo,
`/instrumentos`) y una ruta comodín para los subniveles
(`/instrumentos/{path:path}`). Con ello se evita que FastAPI responda a la ruta
base con una redirección 307 y se preserva la ruta exacta que se reenvía al
servicio. La ruta del chat (`/rag/chat`) se trata de forma especial para
retransmitir la respuesta en flujo (*Server-Sent Events*) a medida que el modelo
la genera. El servicio de análisis es la única excepción al enrutamiento: el
*frontend* lo invoca de forma directa, validando el mismo token.

El detalle del flujo de autenticación y su relación con la seguridad del sistema
se aborda en la sección 8.

### 5.3 Servicio de instrumentos (Instrument Service)

El servicio de instrumentos (puerto 8001) es responsable de la carga de los
instrumentos al sistema. Su *endpoint* principal, `POST /instrumentos/upload`,
orquesta el primer paso del *pipeline*:

1. Valida el tipo de instrumento declarado por el investigador (encuesta,
   entrevista o prueba estandarizada).
2. Identifica el formato de cada archivo recibido —el respondido, el original
   opcional y, en las pruebas tabulares, la clave de respuestas— por su
   extensión y por la firma de sus primeros bytes, de modo que un archivo con
   una extensión falsa sea rechazado.
3. Verifica que el archivo respondido sea coherente con el tipo declarado (por
   ejemplo, que una encuesta sea tabular) y lo procesa con la familia de lector
   correspondiente para confirmar que puede leerse.
4. Entrega los archivos al servicio de almacenamiento, que los guarda sin
   modificarlos.
5. Registra el instrumento en `raw_data` y crea su `instrumento_procesado` en
   estado `recibido`.

La operación es transaccional: si la escritura en la base de datos falla, se
eliminan los archivos ya guardados para no dejar huérfanos. El almacenamiento se
abstrae mediante un puerto con dos implementaciones —una que delega en el
servicio de almacenamiento por HTTP y otra local—, seleccionadas por
configuración. El servicio expone además el listado de instrumentos y su
borrado, este último sujeto a la regla de propiedad descrita en la sección 8.2.

### 5.4 Servicio de limpieza (Cleaning Service)

El servicio de limpieza (puerto 8007) depura cada instrumento recién cargado
antes de que se calculen sus metadatos. Se incorporó al diseño original al
constatar que los metadatos y las estadísticas calculados sobre el archivo crudo
heredaban sus defectos: columnas ajenas al instrumento, duplicados, valores
fuera de rango o escalas mal reconocidas. Su lógica se basa en el documento de
reglas de limpieza del proyecto [ver anexo o capítulo correspondiente] y se
describe con detalle en la sección 6.2.

El servicio se construyó alrededor de un **contrato de motores**: cada tipo de
instrumento tiene un motor que implementa dos pasos puros, sin acceso a la red
ni a la base de datos:

- `automatica`: aplica las transformaciones que no requieren decisión y detecta
  los *hallazgos* que el investigador debe revisar, cada uno con sus opciones y
  una opción sugerida.
- `aplicar`: aplica las decisiones del investigador y produce el resultado
  final (filas del CSV limpio, métricas después de la limpieza y una vista
  final).

Un registro asocia cada combinación de tipo de instrumento y familia de archivo
con su motor: encuestas tabulares, entrevistas en documento, y pruebas
estandarizadas tanto tabulares como en documento. Como el archivo crudo nunca
cambia y ambos pasos son deterministas, al confirmar se repite la fase
automática y se aplican las decisiones guardadas, lo que evita almacenar
archivos intermedios.

Los *endpoints* materializan el ciclo de vida de una ejecución:

| Método | Ruta | Uso |
|--------|------|-----|
| POST | `/limpieza/{id}/ejecuciones` | Ejecuta la fase automática: crea una versión nueva o retoma la que espera decisiones |
| GET | `/limpieza/{id}/ejecuciones/actual` | Última versión |
| GET | `/limpieza/{id}/ejecuciones/{v}` | Fase asistida de la versión `v` |
| PATCH | `/limpieza/{id}/ejecuciones/{v}/decisiones` | Guardado parcial de decisiones |
| POST | `/limpieza/{id}/ejecuciones/{v}/confirmar` | Aplica las decisiones y guarda el CSV limpio |
| GET | `/limpieza/{id}/ejecuciones/{v}/vista-final` | Cifras clave, estadísticas y muestra del resultado |

Las decisiones se guardan conforme el investigador las toma, de modo que pueda
retomar la fase asistida si cierra la página. Al confirmar, el CSV limpio
(separado por punto y coma, en UTF-8 con BOM para que Excel en español muestre
correctamente los acentos) se envía al servicio de almacenamiento, y el reporte
de limpieza se guarda en `limpieza_ejecucion`. Las reglas editables —símbolos de
vacío, patrones de columnas ajenas, umbrales de calidad, opciones válidas de las
pruebas— residen en `config/limpieza.yaml`, y el diccionario de escalas Likert,
compartido con el servicio de conocimiento, en `shared/config/escalas_likert.yaml`.

### 5.5 Servicio de metadata (Metadata Service)

El servicio de metadata (puerto 8003) garantiza que todo instrumento tenga
metadatos completos y aprobados por su autor antes de entrar al RAG. Gestiona
dos familias de metadatos: los trece campos del estándar **Dublin Core**
(título, creador, descripción, tema, cobertura, entre otros) y los metadatos
específicos de cada tipo de instrumento (por ejemplo, población objetivo y
constructo principal en las encuestas, o unidad de aprendizaje y taxonomía de
Bloom en las pruebas).

Sus *endpoints* siguen el orden del flujo de carga:

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/api/metadata/{id}/propuesta` | Dublin Core propuesto |
| GET | `/api/enrichment/{id}/propuesta` | Metadatos del tipo propuestos |
| POST | `/api/metadata/{id}/vista-previa` | JSON técnico y errores de validación, sin guardar |
| POST | `/api/metadata/{id}/aprobar` | Aprobación del autor: persistencia, JSON técnico e ingesta |
| POST | `/api/metadata/{id}/finalizar` | Agrega al JSON los KPIs aceptados |
| DELETE | `/api/metadata/{id}` | Retira la aprobación (el instrumento sale del RAG) |

Las propuestas se calculan a partir de la **última limpieza confirmada**: el
servicio lee el CSV limpio a través del servicio de almacenamiento y toma del
reporte de limpieza la etiqueta original, el rol y el tipo de cada columna.
Las propuestas combinan heurísticas sobre el contenido —número de respondentes,
dimensiones detectadas por los encabezados, preguntas de las entrevistas,
reactivos por sección de las pruebas— con el modelo de lenguaje local, que
completa los campos interpretativos que no pueden inferirse del archivo
(objetivo, constructo, población). Cada valor propuesto indica su origen
(automático, archivo, inferido, LLM o aprobado), y el modelo de lenguaje nunca
es un requisito: si no responde, el autor captura esos campos.

Al aprobar, el servicio persiste los metadatos, genera el **JSON técnico** del
instrumento —con los metadatos, el tipo y las estadísticas de cada pregunta y el
resumen de la limpieza— y lo guarda en el servicio de almacenamiento.

### 5.6 Servicio de conocimiento (Knowledge Service)

El servicio de conocimiento (puerto 8009) se incorporó para resolver un problema
detectado durante las pruebas del flujo: el JSON técnico se utilizaba a la vez
para asociar KPIs y para alimentar el RAG, y ninguno de los dos usos quedaba bien
atendido. Para la asociación de KPIs, el JSON contenía ruido —métricas,
conteos, tipos técnicos y respuestas codificadas— que distorsionaba la
similitud semántica; para el RAG, en cambio, le faltaba información: no incluía
las respuestas individuales ni su significado. El servicio separa estos usos en
artefactos distintos:

| Artefacto | Dónde se muestra | Propósito |
|-----------|------------------|-----------|
| JSON técnico (metadata-service) | No se muestra | Trazabilidad |
| Perfil semántico | Paso «Aprobar metadatos» | Único insumo de la asociación de KPIs |
| Documento final | Paso «Guardar» | Insumo de los fragmentos del RAG |

El servicio se organiza en cuatro módulos: la construcción de la estructura del
instrumento (secciones y preguntas, a partir del instrumento original o de los
encabezados del CSV limpio); la construcción del perfil; una **capa de
interpretación** determinística que convierte cada respuesta codificada en su
significado, y el constructor del documento final para cada tipo de
instrumento. Su funcionamiento se detalla en las secciones 6.4 y 6.6.

| Método | Ruta | Uso |
|--------|------|-----|
| POST | `/conocimiento/{id}/perfil/vista-previa` | Perfil con los metadatos del formulario, sin guardar |
| POST | `/conocimiento/{id}/perfil` | Perfil con los metadatos aprobados; crea la versión N |
| GET | `/conocimiento/{id}/perfil` | Perfil de la versión actual |
| POST | `/conocimiento/{id}/documento` | Genera, valida y guarda el documento final como borrador |
| GET | `/conocimiento/{id}/documento` | Vista ligera del documento |
| GET | `/conocimiento/{id}/documento/json` | Documento completo |
| POST | `/conocimiento/{id}/documento/{v}/publicar` | Publica la versión (`vigente`) |

### 5.7 Servicio de análisis (Analysis Service)

El servicio de análisis (puerto 8002) concentra el cálculo de *embeddings* y la
asociación de los instrumentos con el catálogo de KPIs. Mantiene la colección
`kpis` de ChromaDB, regenerable mediante `POST /vectorizacion/kpis/reindex`, y
expone dos grupos de *endpoints* de asociación:

- **Asociación desde el perfil semántico** (flujo vigente):
  `POST /vectorizacion/perfil/propuestas` calcula los KPIs sugeridos con su
  puntaje, las preguntas que los sustentan y una justificación breve, y
  `POST /vectorizacion/perfil/confirmar` registra los aceptados y los
  rechazados.
- **Asociación por resumen** (flujo original): `POST /vectorizacion/propuestas`
  y `POST /vectorizacion/confirmar` comparan un único vector del resumen del
  instrumento con el catálogo. Se conservan para los instrumentos anteriores y
  como línea base de comparación.

El modelo de *embeddings* se carga de forma perezosa —solo la primera vez que se
necesita— y sus vectores se normalizan, lo que resulta coherente con el uso de
la similitud coseno. Para redactar las justificaciones, el servicio incorpora un
cliente de Ollama con degradación controlada. La fórmula de asociación se
describe en la sección 6.5.

### 5.8 Servicio de almacenamiento (Storage Service)

El servicio de almacenamiento (puerto 8004) es la autoridad de todo el
almacenamiento de la plataforma. Ningún otro servicio escribe en el disco: todos
le entregan sus archivos y le solicitan su lectura. Sus responsabilidades son
dos:

- **Archivos versionados.** Guarda el instrumento crudo tal como lo subió el
  usuario, el CSV limpio, los JSON (técnico, perfil y documento final) y las
  exportaciones a SPSS. Cada artefacto recibe una clave estable con la forma
  `<tipo>/<instrumento>/<versión>__<nombre>`; las escrituras son atómicas y cada
  archivo conserva su huella SHA-256, que se verifica en cada descarga.
- **Ingesta vectorial.** Es el único escritor de la colección `instrumentos` de
  ChromaDB y de la tabla `documento_vectorizado`, y solo ingiere instrumentos
  cuyos metadatos aprobó su autor (sección 6.7).

Ofrece además lectores que devuelven el contenido tabular o textual de un
archivo (CSV, XLSX, PDF, DOCX, TXT), de modo que los demás servicios no
necesiten conocer el formato; una caché en proceso con tiempo de vida; la purga
de todos los archivos y vectores de un instrumento, y tareas de mantenimiento
como la limpieza de temporales. Es un servicio interno: los demás servicios lo
invocan con un token de servicio, y a través del *gateway* solo pueden usarlo los
administradores. Toda ruta recibida se verifica para garantizar que quede dentro
de la raíz del almacenamiento.

### 5.9 Servicio de visualización (Visualization Service)

El servicio de visualización (puerto 8005) presenta la información de forma útil
para el investigador. Es de solo lectura sobre la base de datos y ChromaDB, con
la única excepción del registro de consultas RAG. Sus funciones son:

- **Catálogo.** Listado de instrumentos con filtros (texto, tipo, nivel
  educativo, KPI, autor, año, estado) y facetas, y la ficha de cada instrumento
  con sus metadatos, preguntas y estadísticas.
- **Tableros de KPIs.** El catálogo de indicadores, métricas del acervo y, para
  cada KPI, qué preguntas de cada instrumento lo miden. Esta relación se obtiene
  buscando, dentro de la colección `instrumentos`, los fragmentos de tipo
  pregunta más cercanos al vector del KPI.
- **Instrumentos relacionados.** Instrumentos de otros autores vinculados por
  KPIs compartidos, nivel educativo o similitud semántica.
- **Descargas.** El archivo crudo, el JSON y una exportación al formato `.sav`
  de SPSS, generada desde la tabla de respuestas con etiquetas de variables y de
  valores. De los instrumentos ajenos solo se permite descargar el crudo.
- **Espacio vectorial.** Un mapa bidimensional explicable de los KPIs y los
  instrumentos, con búsqueda semántica (sección 6.9).
- **Chat RAG.** Consultas en lenguaje natural sobre una investigación o sobre
  todo el acervo (sección 6.8).

---

## 6. Flujo de procesamiento e inteligencia del sistema

El procesamiento de los instrumentos constituye el núcleo funcional de la
plataforma y, por su importancia, se documenta en una sección propia. Este flujo
transforma un archivo cargado en conocimiento consultable: lo depura, lo
describe, lo asocia con los indicadores pertinentes, interpreta sus respuestas y
lo indexa para que pueda consultarse en lenguaje natural. La lógica se reparte
entre seis servicios y se apoya en tres piezas de inteligencia: el modelo de
*embeddings*, la base de datos vectorial ChromaDB y el modelo de lenguaje
servido por Ollama.

### 6.1 Visión general del flujo

Desde la interfaz, el flujo se presenta como un asistente de siete pasos. Cada
paso corresponde a una o más llamadas a los servicios y deja su resultado
persistido antes de continuar:

| Paso | Servicio | Resultado |
|------|----------|-----------|
| 1. Archivo | instrument-service | Archivo crudo guardado y registrado (`recibido`) |
| 2. Limpieza | cleaning-service | CSV limpio y reporte de limpieza (versión confirmada) |
| 3. Dublin Core | metadata-service | Trece campos propuestos y revisados por el autor |
| 4. Metadatos del tipo | metadata-service | Metadatos específicos propuestos y revisados |
| 5. Aprobar metadatos | metadata-service + knowledge-service | Metadatos persistidos, JSON técnico y perfil semántico |
| 6. KPIs sugeridos | analysis-service | KPIs aceptados y rechazados, con evidencia y justificación |
| 7. Guardar | knowledge-service + metadata-service | Documento final publicado e instrumento disponible para el RAG |

Tres decisiones atraviesan todo el flujo. Primero, **el sistema propone y el
investigador decide**: la limpieza, los metadatos y los KPIs se presentan con
una opción sugerida, pero ninguno se aplica sin confirmación. Segundo, **los
pasos son versionados y no destructivos**: el archivo crudo nunca se modifica;
repetir la limpieza o volver a aprobar los metadatos genera versiones nuevas, y
cada etapa posterior usa la última versión confirmada. Tercero, **el modelo de
lenguaje es un apoyo y nunca un requisito**: solo interviene donde su aporte es
interpretativo (sugerir metadatos, redactar justificaciones y responder en el
chat), siempre con un mecanismo alterno cuando no está disponible.

El avance de cada instrumento se refleja en el campo `estado` de
`instrumento_procesado`, que evoluciona de `recibido` a `limpieza_en_proceso`,
`limpio`, `metadatos_registrados`, `estandarizado` y, finalmente, `vectorizado`.

### 6.2 Limpieza asistida de los instrumentos

La limpieza se divide en una fase automática, una fase asistida y una
confirmación. Su implementación varía según el tipo de instrumento.

**Encuestas (CSV, XLSX, XLS).** La fase automática aplica primero las
*transformaciones universales*, que no requieren decisión: conversión a UTF-8,
unificación de los espacios repetidos, conversión de las distintas
representaciones de vacío («NA», «N/A», «-», «sin respuesta», entre otras) a
un valor nulo, y eliminación de las filas y columnas completamente vacías. Cada
columna conserva su encabezado original como etiqueta y recibe un
identificador seguro (en minúsculas, sin acentos ni símbolos) que se usa como
encabezado del CSV limpio.

A continuación, el motor propone qué columnas no pertenecen al instrumento —
marcas temporales, identificadores de respuesta, fechas de inicio y fin, correos
y nombres—, mediante expresiones regulares configurables, y sugiere el rol de
cada columna: *pregunta*, *contexto* (edad, carrera, semestre, turno) o
*eliminar*. Después infiere el **tipo canónico** de cada pregunta con un orden
de prioridad fijo, en el que gana el primer tipo que aplica: cuadrícula,
*ranking*, opción múltiple, Likert, binaria, escala lineal, calificación,
numérica, categórica y texto corto o largo.

La detección de escalas Likert merece mención aparte, pues es el tipo de
pregunta más común en los instrumentos educativos. Cuando la escala viene en
texto («Totalmente de acuerdo», «Casi nunca»), el motor compara los valores
normalizados contra un diccionario de escalas en español (acuerdo, frecuencia,
satisfacción, importancia y calidad, con sus sinónimos) y considera Likert una
columna si al menos el 90 % de sus valores coinciden con una misma escala, aunque
no aparezcan todas las opciones. Las respuestas «No sé», «No aplica» y
similares se tratan como faltantes y no como un punto de la escala. Al convertir
el texto en códigos numéricos se conserva el **libro de códigos**, de modo que
el significado de cada número no se pierde.

Con los tipos inferidos se calculan las métricas de calidad (completitud,
proporción de nulos, duplicados) y las medidas estadísticas: descriptivos por
columna, frecuencias, valores atípicos —por ±4 desviaciones estándar o por rango
intercuartílico, solo en columnas numéricas— y la fiabilidad mediante el
**alfa de Cronbach** por bloque de ítems Likert, con la correlación ítem-total y
el alfa si se elimina cada ítem. Los bloques se reconocen por la forma de los
encabezados («Pregunta [aspecto]» o un prefijo con numeración, como
`Dedicacion_item3`).

La fase asistida presenta al investigador los hallazgos que requieren su
decisión: columnas ajenas, roles dudosos, columnas muy incompletas, filas
duplicadas, valores fuera de rango, escalas que parecen Likert pero no están en
el diccionario (para que confirme su orden), ítems posiblemente invertidos,
encuestados que responden siempre la misma opción («en línea recta»),
encuestados que dejaron sin responder más de la mitad del cuestionario y el
tratamiento de las respuestas «No sé / No aplica».

**Entrevistas (DOCX, TXT, PDF).** El motor extrae el texto y aplica un ciclo de
limpieza de ruido —marcas de tiempo, identificadores, números de página,
palabras cortadas y espacios irregulares— que se repite hasta tres veces y se
detiene antes si ya no detecta ruido o si una iteración no produce cambios.
Después identifica a los hablantes y sus turnos, y sugiere el rol de cada uno
(entrevistador, entrevistado u otro) a partir de su etiqueta y de la proporción
de sus turnos que son preguntas. En la fase asistida, el investigador confirma
los roles, decide qué hacer con el ruido residual y, si no se reconoce la
estructura de hablantes, recibe un aviso explícito. La salida es un CSV con un
turno por fila.

**Pruebas estandarizadas.** En el formato tabular, el motor recibe las
respuestas de los alumnos y la clave de respuestas, y aplica las validaciones en
orden: formato y delimitador, estructura (columnas faltantes o sobrantes,
identificadores de alumno duplicados), opciones válidas (por defecto A, B, C, D y
NR) y anulación de las respuestas múltiples, con caracteres inválidos o
ilegibles. Para cada alumno y reactivo registra si la respuesta es correcta, su
estado (válida, nula o no respondida) y el motivo. Calcula además el análisis de
reactivos: índice de dificultad, índice de discriminación con grupos extremos
del 27 %, correlación punto-biserial, distribución de opciones (para detectar
distractores que nadie elige), puntajes y la fiabilidad **KR-20**. La salida
tiene formato largo —una fila por alumno y reactivo— y conserva al final las
columnas de contexto del alumno.

Al terminar, la vista final muestra al investigador una muestra del resultado,
las cifras clave y una comparación de las métricas antes y después de la
limpieza. Un resumen en lenguaje sencillo, generado con reglas fijas y sin
modelo de lenguaje, señala lo que conviene atender (por ejemplo, un alfa bajo en
un bloque). Desde esta vista, el investigador puede volver a ajustar la limpieza
o continuar a los metadatos.

### 6.3 Metadatos y JSON técnico

Con la limpieza confirmada, el servicio de metadata propone los campos Dublin
Core y los metadatos del tipo a partir del CSV limpio y del reporte de limpieza,
como se describió en la sección 5.5. El investigador los revisa en los pasos 3 y
4 y los aprueba en el paso 5. Al aprobar, se persisten los metadatos y se genera
el JSON técnico, que conserva toda la información del instrumento —metadatos,
tipos, estadísticas por pregunta y resumen de la limpieza— con fines de
trazabilidad.

### 6.4 Perfil semántico

En el mismo paso de aprobación, el servicio de conocimiento construye el
**perfil semántico**: una descripción del instrumento que contiene únicamente lo
que aporta significado para la búsqueda semántica. Incluye el título, el
objetivo, los temas, las palabras clave, el nivel educativo, la población, un
texto de contexto y las preguntas agrupadas por sección, con sus opciones solo
cuando estas aportan significado (preguntas categóricas, binarias y de opción
múltiple). Deliberadamente **no** incluye métricas, conteos, respuestas,
identificadores de columna, rutas, formatos ni tipos técnicos; las anclas de las
escalas Likert («De acuerdo», «En desacuerdo») tampoco se incluyen, pues se
repiten en decenas de preguntas y no distinguen un instrumento de otro.

Las preguntas se obtienen preferentemente del **instrumento original** (el
archivo sin respuestas), que contiene el texto completo y la organización en
secciones. Cada columna del CSV limpio se empareja con una pregunta del original
por similitud de palabras, tolerante a encabezados truncados, o por sección y
posición cuando los encabezados vienen codificados. Si no se subió el original,
las preguntas se toman de las etiquetas del CSV limpio. Cuando algo no se
encuentra, la respuesta incluye avisos para el investigador. Cada sección y
pregunta recibe un identificador global y estable (por ejemplo,
`INS-0012-p03`), que el documento final reutiliza. El perfil se valida contra un
esquema JSON antes de guardarse.

### 6.5 Asociación de KPIs por unidades

La asociación del instrumento con el catálogo de KPIs se realiza por similitud
semántica entre el perfil y la colección `kpis`, cuyos vectores se generan a
partir del texto de contexto de cada indicador y no se modifican en este
proceso. La implementación original comparaba un único vector del resumen del
instrumento contra el catálogo; en un instrumento de decenas de preguntas, ese
vector «promediaba» todos los temas y diluía la similitud. Por ello se adoptó
una **asociación por unidades**:

- **U₀, perfil general**: el perfil en texto legible con una plantilla
  («Instrumento: … / Objetivo: … / Temas: … / Población: …»).
- **Uᵢ, una unidad por pregunta**: «Sección: … / Pregunta: … / Opciones: …».
  Los reactivos sin texto real no forman unidad.

Nunca se vectoriza el JSON: las llaves, comillas y nombres de campo serían ruido
para el modelo. Cada unidad se convierte en un vector con el mismo modelo usado
para los KPIs, y para cada indicador *k* se calcula:

- *g* = cos(U₀, *k*): similitud con el perfil general.
- *p*: media de las tres mayores similitudes cos(Uᵢ, *k*) entre las preguntas.
- *c* = min(1, |E*k*| / 3): cobertura, donde E*k* son las preguntas cuya
  similitud con el KPI alcanza el umbral de evidencia (0.45).

El puntaje final es **score = 0.45·*g* + 0.45·*p* + 0.10·*c***. El componente
*g* captura el propósito declarado del instrumento; *p* premia que existan
preguntas que realmente miden el indicador, y tomar las tres mejores evita que
una sola frase casual decida; *c* desempata a favor de los KPIs respaldados por
varias preguntas. Los candidatos son la unión de los diez KPIs más cercanos al
perfil general y de los tres más cercanos a cada pregunta, y se presentan los
que superan un puntaje de 0.30, hasta un máximo de ocho. Los pesos y umbrales
se definen en la configuración compartida, de modo que pueden calibrarse sin
modificar el código; el umbral de evidencia se ajustó comparando ambos métodos
sobre instrumentos reales con un script de comparación incluido en el servicio.

Para cada KPI sugerido, la interfaz muestra su puntaje, las preguntas que lo
sustentan con su similitud y una **justificación breve**. Esta es la única pieza
del flujo de conocimiento generada por el modelo de lenguaje: se le pide
explicar en dos o tres oraciones la relación, usando solo la definición del
indicador, el objetivo del instrumento y las preguntas de evidencia, sin
inventar datos. Si el modelo no responde o su respuesta no es útil, se usa una
plantilla determinística. El investigador puede editar la justificación antes
de aceptar, y su origen queda registrado (`llm`, `llm_revisada`, `plantilla` o
`plantilla_revisada`).

Al confirmar, las decisiones —aceptadas y rechazadas, con sus componentes,
evidencia y justificación— se guardan en `version_conocimiento`; los KPIs
aceptados se agregan al perfil y se registran además en `kpi_inferido` y
`kpi_inferido_chunk`, que alimentan los tableros.

### 6.6 Interpretación de respuestas y documento final

En una encuesta, una respuesta registrada como «2» carece de significado hasta
saber que, en esa pregunta, 2 equivale a «En desacuerdo». Para que el RAG pueda
responder con exactitud, el servicio de conocimiento incorpora una **capa de
interpretación** que convierte cada valor del CSV limpio en una respuesta con su
valor original, su significado (la etiqueta exacta), un *nivel* que la agrupa
para las consultas (desacuerdo, neutral o acuerdo; baja, media o alta) y su
estado (respondida, sin respuesta o no interpretada). Las reglas dependen del
tipo de pregunta:

| Tipo | Regla de interpretación |
|------|-------------------------|
| Likert y cuadrícula | Código → etiqueta del libro de códigos → nivel; en los ítems invertidos se agrega el valor recodificado |
| Binaria | Sí/No, 1/0, Verdadero/Falso → «Sí» o «No» |
| Categórica | Etiqueta normalizada a su grafía más frecuente |
| Opción múltiple y *ranking* | Lista de opciones seleccionadas (ordenada en el *ranking*) |
| Escala lineal | «4 en escala 1–5, donde 1 = Nada y 5 = Mucho», o «4 de 5» si no hay anclas |
| Calificación y numérica | Valor con su escala o su unidad («14 horas») |
| Texto | Tal cual |
| Respuesta vacía | Estado «sin respuesta»: nunca se omite |
| Prueba estandarizada | Letra → texto de la opción del original (o «Opción C»), más si es correcta, su estado y su motivo |

Los niveles se asignan por posición dentro de la escala, de modo que sirven para
escalas de 4, 5 o 7 puntos. La capa es completamente determinística: no utiliza
el modelo de lenguaje, para que ninguna interpretación pueda inventarse.

Con las respuestas interpretadas se construye el **documento final**, que será
el insumo de los fragmentos del RAG. Su estructura depende del tipo de
instrumento:

- **Encuesta:** las preguntas con su definición, su escala, sus KPIs
  relacionados y un **resumen precalculado** (distribución por significado y
  por nivel, porcentajes, media y una interpretación en una frase), y los
  respondentes anonimizados con su contexto y sus respuestas interpretadas.
- **Prueba estandarizada:** los reactivos con su texto, opciones, respuesta
  correcta, porcentaje de acierto, distractor más elegido, dificultad y
  discriminación, y los alumnos con su puntaje y sus respuestas.
- **Entrevista:** los participantes con sus intercambios, donde lo que dice el
  entrevistador es la pregunta y lo que responde el participante hasta la
  siguiente intervención del entrevistador es la respuesta.

El documento sigue cuatro principios: cada respuesta aparece una sola vez,
dentro de su respondente; los identificadores son globales, para consultar
varios instrumentos a la vez; la relación entre KPIs y preguntas puede
recorrerse en ambos sentidos, y los resúmenes vienen calculados, porque un
modelo de lenguaje no cuenta filas de forma confiable. El documento no contiene
datos personales (sección 8.2) y se valida contra un **JSON Schema** por tipo
de instrumento antes de guardarse: si no cumple el esquema, no se almacena.

El documento se guarda en el servicio de almacenamiento como borrador al entrar
al paso «Guardar», y se publica como versión vigente al guardar el instrumento.
Para comprobar que contiene lo necesario, se implementó un conjunto de funciones
de consulta determinísticas que responden preguntas como «¿qué respondió el
respondente R017?», «¿qué porcentaje del turno vespertino está de acuerdo con
la pregunta 4?» o «¿qué preguntas miden este KPI?»; su verificación se presenta
en el capítulo de Pruebas.

### 6.7 Indexación en ChromaDB

Una vez aprobados los metadatos, el servicio de almacenamiento ingiere el
instrumento en la colección `instrumentos` de ChromaDB. El JSON se divide en
fragmentos de tres clases: un *encabezado* con la ficha del instrumento
(título, objetivo, Dublin Core, metadatos del tipo y KPIs), un fragmento por
*pregunta* (sección, texto, opciones y resultados) y, en entrevistas y pruebas,
el *contenido* textual completo. Los textos largos se cortan en ventanas de unos
800 caracteres con un solapamiento de 150, respetando los límites de párrafo y
de oración.

Cada vector lleva metadatos filtrables —instrumento, título, tipo, autor, nivel
educativo, año, sección, pregunta y KPIs—, lo que permite restringir las
búsquedas a una investigación. Cada fragmento se registra también en
`documento_vectorizado`, y reingerir un instrumento reemplaza sus vectores
anteriores. Solo se ingieren instrumentos aprobados por su autor, que pasan al
estado `vectorizado`.

En el estado actual, la ingesta se alimenta del JSON técnico. Como trabajo
siguiente, se reemplazará por fragmentos derivados del documento final, que
incorporan las respuestas interpretadas, junto con una tabla de respuestas en
formato largo para resolver consultas estructuradas (por ejemplo, encontrar a
un respondente que cumpla varias condiciones a la vez).

### 6.8 Consulta mediante RAG

La consulta mediante recuperación aumentada por generación (RAG) se implementó
en el servicio de visualización y se encuentra en operación. El investigador
agrupa instrumentos en una investigación y formula preguntas en el chat. El
sistema convierte la pregunta en un vector, recupera de ChromaDB los fragmentos
más cercanos —filtrando por los instrumentos de la investigación o, sin filtro,
sobre todo el acervo aprobado— y construye un *prompt* que incluye el contexto
de la investigación (objetivo, población, nivel) y los fragmentos recuperados.
El modelo de lenguaje genera la respuesta, que se transmite al navegador en
flujo mientras se produce, acompañada de las **fuentes citadas**. Cada consulta
queda registrada en `rag_log` con la pregunta, la respuesta, el modelo, el
número de fragmentos y la latencia.

La generación se integró con **degradación controlada**: si el modelo de
lenguaje no está disponible, el sistema igualmente recupera y muestra las
fuentes, lo que permite demostrar la recuperación semántica —la parte
sustantiva del RAG— de forma independiente. Si no se encuentra información
relevante, el sistema lo indica explícitamente en lugar de generar una
respuesta sin fundamento.

### 6.9 Espacio vectorial

Para hacer comprensible la asociación semántica, se construyó una vista que
proyecta el espacio de *embeddings* en dos dimensiones. El servicio de
visualización ajusta un **análisis de componentes principales (PCA)** de dos
componentes sobre los vectores de los KPIs y de los instrumentos, y proyecta con
la misma transformación los fragmentos del RAG y las consultas del usuario. El
mapa informa la varianza explicada por cada componente y advierte cuando la
suma de ambos es baja (menor al 25 %), pues entonces la proyección simplifica
demasiado.

Dado que una distancia en el plano es solo una aproximación, la similitud entre
elementos —los vecinos de un punto o los resultados de una búsqueda— se calcula
siempre con el coseno sobre los vectores originales, igual que en el RAG. El
mapa agrupa los KPIs en *clusters* semánticos mediante *k-means* esférico, y
cada instrumento hereda el *cluster* de su KPI más parecido. Ofrece además una
vista alineada que centra cada grupo en su propio centroide, para compensar la
diferencia de estilo entre una definición breve de KPI y el texto extenso de un
instrumento. Un buscador permite escribir una frase libre, ubicarla en el mapa y
listar sus vecinos. El resultado se guarda en memoria y solo se recalcula cuando
cambian los datos.

---

## 7. Implementación del frontend

La interfaz de usuario de la plataforma se desarrolló como una aplicación web
con React y TypeScript, construida sobre TanStack Start y Vite. La totalidad de
la interfaz se diseñó en español —tanto los textos como los nombres de las rutas
y del dominio en el código— y se organizó siguiendo un enfoque por *features*
(dominios), de modo que cada área funcional del sistema reside en su propio
módulo.

### 7.1 Estructura de componentes y organización por features

El código fuente del *frontend* se organiza, dentro de `src/`, separando la
lógica de cada dominio de los elementos reutilizables. El directorio
`features/` agrupa las áreas funcionales de la aplicación:

| Feature | Contenido |
|---------|-----------|
| `auth` | Sesión del usuario y contexto de autenticación |
| `inicio` | Página de inicio con accesos a cada módulo |
| `upload` | Asistente de carga de siete pasos, incluidas la limpieza asistida y las vistas del perfil y del documento final |
| `instruments` | Catálogo con filtros, vista rápida, descargas y borrado |
| `research` | Armado de una investigación a partir de instrumentos propios y relacionados |
| `chat` | Chat RAG con fuentes citadas |
| `kpis` | Tableros de indicadores y gráficas |
| `espacio-vectorial` | Mapa interactivo de *embeddings*, búsqueda y recorrido guiado |
| `usuarios` | Alta de usuarios (solo administradores) |

Los componentes compartidos se ubican en `components/`, dividido en
componentes de diseño de página (*layout*), piezas compartidas (paneles,
estados vacíos, indicadores de carga, *stepper*), componentes de interfaz
basados en Radix UI y efectos visuales. Los tipos de dominio comunes se
centralizan en `types/`.

El enrutamiento se definió de manera declarativa mediante TanStack Router, cuyos
archivos de ruta residen en `routes/`. La aplicación emplea un *layout*
autenticado —la ruta de panel— del que dependen las pantallas internas: inicio,
carga de un instrumento, instrumentos, investigación, KPIs, espacio vectorial,
chat y usuarios. El árbol de rutas se genera automáticamente a partir de estos
archivos.

El asistente de carga merece mención especial, pues concentra la mayor parte de
la integración. Cada paso solicita al servicio correspondiente su propuesta al
entrar y ejecuta la llamada de persistencia al avanzar, de modo que una carga
interrumpida puede retomarse —por ejemplo, si se cierra la página durante la
limpieza—. La fase asistida de la limpieza presenta cada hallazgo como una
tarjeta con sus opciones y la sugerida preseleccionada, y la vista final ofrece
pestañas de estadística y de comparación antes y después.

### 7.2 Integración con la API

Una de las decisiones de diseño más relevantes del *frontend* es que las
pantallas nunca acceden directamente a los datos: toda interacción con
información se canaliza a través de una capa dedicada en `api/`, con un módulo
por área (autenticación, carga, limpieza, conocimiento, instrumentos, KPIs,
espacio vectorial, chat y usuarios). Cada módulo expone funciones asíncronas, de
manera que la interfaz depende de esas firmas y no de su implementación interna.
Gracias a ello fue posible sustituir progresivamente los datos de ejemplo por
llamadas reales sin modificar las pantallas.

El acceso al *backend* se concentra en un cliente HTTP común. Este cliente
define la dirección del API Gateway y la del servicio de análisis (configurables
mediante variables de entorno), un ayudante genérico para realizar las
peticiones y la gestión del token de autenticación. Cuando el usuario inicia
sesión, el token JWT se almacena de forma persistente en el navegador y se
adjunta automáticamente en la cabecera de autorización. El cliente también
centraliza el manejo de errores: traduce los códigos de respuesta HTTP a
mensajes claros en español.

> **Nota sobre el estado de integración.** Las operaciones principales
> —autenticación, carga, limpieza, metadatos, KPIs, documento final, catálogo,
> tableros, espacio vectorial, descargas y chat RAG— operan contra el
> *backend*. Permanecen con datos simulados las noticias del panel del chat y
> el listado de investigaciones, que se conserva en el almacenamiento local del
> navegador.

### 7.3 Estilos y experiencia de usuario

El diseño visual se apoya en Tailwind CSS y en una biblioteca de componentes
accesibles basada en Radix UI, que proporciona elementos consistentes
(diálogos, menús, pestañas, formularios, entre otros). Para preservar la
coherencia visual, los colores, la tipografía y las sombras se definieron
exclusivamente como *tokens* semánticos centralizados en la hoja de estilos
principal (`styles.css`), evitando el uso de valores de color literales en los
componentes. Este enfoque facilita el mantenimiento de la identidad visual y
permite ajustar el aspecto de toda la aplicación desde un único punto.

En una iteración posterior se rediseñó la interfaz para aprovechar todo el
ancho de la pantalla, aumentar la escala tipográfica y adaptarse a monitores
grandes, ventanas reducidas y dispositivos móviles. Se incorporaron
animaciones de entrada, contadores animados para las cifras clave y estados de
carga y vacíos más informativos, y se redujeron los contenedores angostos que
desperdiciaban espacio.

---

## 8. Integración de los componentes

Una vez construidos los componentes de manera independiente, la integración
consistió en hacerlos operar como un sistema único y coherente. Esta sección
describe los mecanismos transversales que atraviesan a todos los servicios: la
autenticación de los usuarios y de los propios servicios, la protección de los
datos, el recorrido completo de una operación y la estrategia de manejo de
errores.

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
   (*claims*), el identificador del usuario, su rol y la fecha de expiración,
   fijada en 60 minutos.

3. **Acceso a recursos protegidos.** En las peticiones subsecuentes, el token se
   envía en la cabecera de autorización (`Authorization: Bearer <token>`). Cada
   microservicio lo valida —comprobando su firma y vigencia— y, a partir de él,
   identifica al usuario. Si el token es inválido o ha expirado, la petición se
   rechaza con un error 401.

4. **Autorización por rol.** El sistema define dos roles de usuario:
   *investigador* y *administrador*. Determinadas operaciones exigen un rol
   específico; por ejemplo, el alta de nuevos usuarios está reservada al
   administrador. Cuando un usuario autenticado carece del rol necesario, la
   operación se rechaza con un error de permisos (código HTTP 403).

Un aspecto relevante del diseño es que los tokens son *autocontenidos*:
cualquier servicio puede verificarlos con la misma clave secreta, sin consultar
la base de datos ni invocar de nuevo al *gateway*. Esto simplifica la
comunicación entre microservicios y evita acoplamientos innecesarios. Como
consecuencia, todos los servicios deben compartir exactamente la misma clave: una
diferencia se manifiesta como un error 401.

Para las llamadas entre servicios en las que no interviene un usuario —por
ejemplo, cuando el servicio de instrumentos guarda el archivo crudo en el de
almacenamiento— se implementaron **tokens de servicio**: tokens JWT de vida
corta (cinco minutos), firmados con la misma clave y con un rol técnico
`servicio`, que se generan en cada llamada.

### 8.2 Privacidad y protección de datos

La protección de los datos se abordó mediante varias medidas concretas aplicadas
durante la implementación:

- **Cifrado de contraseñas.** Las contraseñas nunca se almacenan en texto plano.
  Al dar de alta a un usuario, la contraseña se transforma mediante el algoritmo
  de *hashing* **bcrypt**, y únicamente se guarda ese *hash*.

- **Defensa frente a la enumeración de cuentas.** El proceso de autenticación
  verifica siempre un *hash* de contraseña, incluso cuando el correo no
  corresponde a ningún usuario registrado. Con ello se evita que las diferencias
  en el tiempo de respuesta revelen si un correo existe en el sistema.

- **Control de acceso reforzado en el backend.** Las reglas de autorización se
  validan en los servicios, no solo en la interfaz, para que no puedan eludirse
  llamando directamente a la API. Solo el administrador da de alta usuarios; un
  investigador solo puede eliminar los instrumentos que él subió (en caso
  contrario recibe un error 403), mientras que el administrador puede eliminar
  cualquiera. Proponer, aprobar y limpiar un instrumento está reservado a su
  autor o a un administrador, y de los instrumentos ajenos solo puede
  descargarse el archivo crudo.

- **Servicio de almacenamiento interno.** El acceso directo a los archivos está
  reservado a los servicios y a los administradores; los investigadores
  descargan a través del servicio de visualización, que aplica la regla de
  propiedad.

- **Anonimización del documento final.** El documento que alimenta al RAG
  identifica a los respondentes, alumnos y participantes con identificadores
  anónimos (R001, A001, E01). Las columnas con datos personales —nombre,
  correo, matrícula, teléfono, CURP, boleta, entre otras— se detectan con una
  lista configurable, comparando por palabra completa del encabezado (de modo
  que «id» no confunda «idioma»), y nunca se incluyen, ni siquiera como
  contexto. En las entrevistas, los nombres de los hablantes se reemplazan
  también dentro del texto. Dado que no es posible anonimizar por completo un
  texto libre —por ejemplo, otros nombres mencionados en una respuesta—, el
  sistema lo advierte al investigador.

- **Minimización de datos de los usuarios.** De cada usuario se almacena
  únicamente la información necesaria para la operación del sistema: nombre,
  correo electrónico, el *hash* de la contraseña, el rol y la fecha de registro.

- **Procesamiento local.** El modelo de lenguaje y el de *embeddings* se ejecutan
  en la propia infraestructura del sistema, por lo que el contenido de los
  instrumentos no se envía a servicios externos.

### 8.3 Flujo de datos de extremo a extremo

Para ilustrar cómo se integran los componentes, puede seguirse el recorrido de
la carga de una encuesta. El *frontend* envía los archivos al *gateway*, que
valida el token y los reenvía al servicio de instrumentos; este los guarda en el
servicio de almacenamiento mediante un token de servicio y registra el
instrumento en PostgreSQL. En el paso de limpieza, el servicio de limpieza lee el
crudo a través del almacenamiento, ejecuta su motor y, al confirmar, guarda el
CSV limpio y su reporte. El servicio de metadata propone los metadatos a partir
de esa limpieza y, al aprobarlos, el servicio de conocimiento construye el perfil
semántico. El *frontend* consulta entonces de forma directa al servicio de
análisis, que compara las unidades del perfil con la colección `kpis` y devuelve
las sugerencias. Al guardar, el servicio de conocimiento genera y publica el
documento final, y el instrumento queda indexado en ChromaDB y disponible en el
catálogo, los tableros, el espacio vectorial y el chat. El intercambio de datos
se realiza en todo momento en formato JSON a través de la red interna que
conecta a los contenedores.

### 8.4 Manejo de errores y validaciones

El sistema aplica una estrategia de validación y manejo de errores en varias
capas. En el *backend*, la validación de los datos de entrada se apoya en los
esquemas de *Pydantic*, que garantizan que las peticiones cumplan con la
estructura y los tipos esperados; las violaciones se traducen en respuestas con
el código HTTP correspondiente (422 para datos no válidos, 409 para conflictos
como un correo duplicado o un paso que aún no puede ejecutarse, por ejemplo
proponer metadatos de un instrumento sin limpieza confirmada). Los vocabularios
cerrados del dominio (tipos de instrumento, estados del *pipeline*) se
comprueban contra constantes compartidas al iniciar cada servicio, y los
artefactos complejos —el perfil semántico y el documento final— se validan
contra su esquema JSON antes de guardarse.

Los errores de la limpieza se redactaron para el investigador: cuando un archivo
no puede procesarse, el mensaje explica la causa y la ejecución queda en estado
`fallida`, sin enviar nada al servicio de metadata. Las fallas de un servicio
dependiente se distinguen de los errores propios (503 cuando el almacenamiento
no responde, 502 cuando responde con error). En el *frontend*, el cliente HTTP
centraliza la interpretación de estos códigos y los traduce a mensajes claros en
español.

Finalmente, todas las funciones que dependen del modelo de lenguaje cuentan con
**degradación controlada**: las propuestas de metadatos quedan para captura
manual, las justificaciones de KPIs usan una plantilla y el chat muestra las
fuentes recuperadas. De este modo, la falta de disponibilidad del modelo nunca
bloquea el flujo principal.

---

## 9. Contenerización y despliegue local

La plataforma se empaquetó en contenedores de Docker y se orquestó con Docker
Compose, de modo que el sistema completo —ocho microservicios, la interfaz y
cinco servicios de infraestructura— pueda iniciarse con un solo comando en
cualquier equipo con Docker instalado.

### 9.1 Imágenes Docker de cada servicio

Cada microservicio cuenta con su propio *Dockerfile*, ubicado en
`infrastructure/docker/`. Todos siguen el mismo patrón de **construcción en dos
etapas** sobre la imagen `python:3.12-slim`:

1. En la etapa de construcción se instalan las herramientas de compilación
   (`gcc` y las cabeceras de PostgreSQL) y las dependencias del servicio
   declaradas en su *requirements.txt*.
2. En la etapa final se parte de nuevo de la imagen ligera, se instala solo la
   biblioteca de ejecución de PostgreSQL y se copian los paquetes ya instalados,
   el código del servicio y la carpeta `shared/`.

De esta forma, las herramientas de compilación no forman parte de la imagen
final, que resulta más ligera. Cada imagen expone el puerto de su servicio e
inicia el servidor Uvicorn.

Los tres servicios que calculan *embeddings* —análisis, almacenamiento y
visualización— instalan **PyTorch en su variante para CPU** antes del resto de
las dependencias. Sin este paso, la librería *sentence-transformers* descarga la
variante para GPU de NVIDIA, de varios gigabytes, que no se utiliza dentro de los
contenedores: la GPU queda reservada para Ollama. Instalarla primero, y en una
capa anterior a la copia del *requirements.txt*, evita además volver a
descargarla cada vez que cambia una dependencia.

La interfaz se construye sobre `node:20-alpine`: una primera etapa instala las
dependencias de Node y la segunda copia el código y ejecuta el servidor de
desarrollo de Vite en el puerto 3000, expuesto fuera del contenedor. Los
servicios de infraestructura usan imágenes oficiales: `postgres:16-alpine`,
`chromadb/chroma`, `ollama/ollama` y `redis:7-alpine`.

### 9.2 Orquestación con docker-compose

El archivo `docker-compose.yml` define todos los contenedores, la red que los
comunica y los volúmenes que persisten sus datos:

- **Red.** Todos los contenedores se conectan a una red puente
  (`indagata_network`), dentro de la cual se localizan por el nombre del
  servicio (por ejemplo, `http://storage-service:8004`).
- **Puertos.** Cada servicio publica su puerto en el equipo anfitrión. Se
  reasignaron dos para evitar colisiones: el *gateway* se publica en el 8006 y
  ChromaDB en el 8008, pues ambos escuchan internamente en el 8000.
- **Dependencias y salud.** PostgreSQL y Redis declaran comprobaciones de salud
  (*healthchecks*), y los microservicios esperan a que la base de datos esté
  disponible antes de iniciar (`depends_on` con `condition: service_healthy`).
  Los servicios que necesitan el almacenamiento, ChromaDB u Ollama declaran
  también esa dependencia. El *gateway* expone su propia comprobación de salud.
- **Volúmenes.** Los datos de PostgreSQL, ChromaDB, Ollama y Redis se guardan en
  volúmenes con nombre, que sobreviven a la recreación de los contenedores. Un
  volumen adicional (`hf_cache`) conserva el modelo de *embeddings* descargado
  y lo comparte entre los servicios que lo usan, evitando descargarlo de nuevo
  en cada reconstrucción.
- **Código montado.** El código de cada servicio y la carpeta `shared/` se
  montan desde el repositorio, de modo que un cambio en el código se refleja
  reiniciando el contenedor, sin reconstruir la imagen. La reconstrucción solo es
  necesaria cuando cambian las dependencias.
- **Inicialización de la base de datos.** El directorio de scripts de PostgreSQL
  se monta como directorio de inicialización —se ejecuta solo cuando el volumen
  de datos está vacío— y el de migraciones se monta aparte, para aplicarlas
  manualmente sobre una base existente.
- **GPU.** El contenedor de Ollama reserva la GPU del equipo. Se configuró para
  mantener el modelo cargado en memoria de forma indefinida, lo que evita
  recargarlo tras cada periodo de inactividad.

La orquestación incluye también el visor de solo lectura de ChromaDB (puerto
8085), útil durante el desarrollo para inspeccionar las colecciones sin afectar
al resto del sistema.

### 9.3 Variables de entorno y configuración

La configuración se gestiona en dos niveles. Todos los servicios de Python leen
una **configuración única**, definida con *Pydantic Settings* en
`shared/db/core/config.py`, con valores por defecto adecuados para ejecutar un
servicio fuera de Docker (direcciones en `localhost`). Docker Compose
sobrescribe esos valores con variables de entorno que apuntan a los nombres de
los contenedores.

Los valores sensibles o propios de cada instalación se definen en un archivo
`.env` en la raíz del proyecto, que Docker Compose lee automáticamente. El
repositorio incluye una plantilla (`.env.example`), mientras que el archivo real
está excluido del control de versiones. Las variables principales son:

| Variable | Uso |
|----------|-----|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credenciales de la base de datos |
| `SECRET_KEY` | Firma de los tokens JWT; debe ser la misma en todos los servicios |
| `OLLAMA_MODEL` | Modelo de lenguaje (por defecto `llama3.2:3b`) |
| `EMBEDDING_MODEL` | Modelo de *embeddings* |
| `METADATA_USAR_LLM` | Activa las sugerencias de metadatos con el modelo de lenguaje |
| `VITE_API_URL`, `VITE_ANALYSIS_URL` | Direcciones del *gateway* y del servicio de análisis para la interfaz |
| `NODE_ENV` | Modo de ejecución de la interfaz (`development` en el entorno local) |

Las direcciones internas de los servicios (`*_SERVICE_URL`), los parámetros de
la asociación de KPIs (pesos y umbrales) y las rutas de almacenamiento tienen
valores por defecto y solo se modifican para calibrar el sistema. Las reglas de
dominio que un investigador podría querer ajustar no son variables de entorno,
sino archivos YAML versionados junto con el código (sección 2.3).

---

## 10. Dificultades técnicas y soluciones

Durante la construcción surgieron problemas que obligaron a revisar decisiones
técnicas. A continuación se describen los más relevantes y la forma en que se
resolvieron.

**Ruido en la asociación de KPIs.** La primera versión asociaba los KPIs
comparando un único vector del instrumento, generado a partir del mismo JSON que
alimentaba al RAG. Ese JSON incluía métricas, conteos y respuestas codificadas
que no aportan significado, y en instrumentos extensos el vector único diluía los
temas. *Solución:* se separaron los artefactos según su propósito —el perfil
semántico para la asociación y el documento final para el RAG— y se adoptó la
asociación por unidades descrita en la sección 6.5, que además permite mostrar
qué preguntas sustentan cada KPI.

**Respuestas sin significado para el RAG.** En las encuestas y pruebas, las
respuestas se almacenan como códigos («4», «C») que no significan nada fuera de
su escala. *Solución:* la capa de interpretación determinística convierte cada
código en su etiqueta y su nivel a partir del libro de códigos generado durante
la limpieza, y los resúmenes se precalculan para que el modelo de lenguaje no
tenga que contar.

**Errores en la inferencia de tipos de pregunta.** Al probar la limpieza con una
encuesta real de 180 participantes se detectaron dos errores: los bloques con
encabezados del tipo `Aportacion_item1` no se reconocían como un mismo bloque,
por lo que solo se calculaba un alfa de Cronbach global, y una columna de horas
de trabajo, con valores entre 0 y 100, se clasificaba como calificación.
*Solución:* se ampliaron los patrones de bloque (sufijos `_item1`, `_1` y `.1`) y
se agregó una lista configurable de palabras que indican cantidades (horas, edad,
años), cuyas columnas se tratan como numéricas.

**Descarga de PyTorch para GPU.** Al construir las imágenes, la instalación de
*sentence-transformers* descargaba la variante de PyTorch para GPU de NVIDIA,
que no se utiliza dentro de los contenedores. En el servicio de análisis, esta
descarga rondaba los 7 GB y la construcción tardaba unos 20 minutos.
*Solución:* instalar primero PyTorch desde el índice de paquetes para CPU
(sección 9.1). Con ello, la construcción del servicio de análisis bajó a unos 2
minutos, y la imagen del servicio de visualización pasó de unos 3 GB a unos
800 MB.

**Incompatibilidad entre dependencias.** El paquete completo de ChromaDB entraba
en conflicto con la versión de FastAPI del proyecto, y su cliente utilizaba un
tipo de dato eliminado en NumPy 2.0. *Solución:* se usó el cliente HTTP ligero
de ChromaDB, compatible con el servidor y con el mismo código, y se fijó NumPy en
una versión 1.x.

**Recursos limitados de la GPU.** El equipo de desarrollo cuenta con una GPU de
4 GiB. Con la configuración por defecto, el modelo de lenguaje se descargaba de
la memoria tras unos minutos de inactividad y tardaba alrededor de 24 segundos en
volver a responder. *Solución:* se limitó la ventana de contexto a 2048 *tokens*
y se configuró Ollama para mantener el modelo cargado de forma indefinida; con
ello, el modelo opera por completo en la GPU y las respuestas se reducen a unos
2 segundos.

**Conflictos del entorno local.** Dos problemas del entorno de desarrollo en
Windows impidieron levantar el sistema completo. La instalación nativa de Ollama
ocupaba el puerto 11434 que requiere el contenedor, y la interfaz se ejecutaba
con `NODE_ENV=production` por omisión mientras el contenedor iniciaba el servidor
de desarrollo de Vite, lo que puede omitir las dependencias de desarrollo e
inhabilitar la recarga en caliente. *Solución:* se desactivó el inicio automático
de Ollama en Windows y se definió `NODE_ENV=development` en el archivo `.env` del
entorno local.

**Redirecciones del proxy.** Con una sola ruta comodín por prefijo, FastAPI
respondía a la ruta base con una redirección 307 en lugar de reenviarla al
servicio. *Solución:* cada prefijo del *gateway* registra explícitamente tanto
la ruta base como la ruta comodín (sección 5.2). [Si recuerdas el síntoma
concreto que observaron en la interfaz, conviene añadirlo aquí.]

**Recursos compartidos entre contenedores.** El diccionario de escalas Likert
residía dentro del servicio de limpieza, pero el servicio de conocimiento también
lo necesita, y los contenedores solo comparten la carpeta `shared/`.
*Solución:* el diccionario se trasladó a `shared/config/`, sin cambiar su
contenido, y ambos servicios lo leen desde ahí.

**Colisión de módulos en las pruebas.** Los servicios con organización plana
comparten nombres de módulos de primer nivel (`main`, `models`, `services`), que
colisionan si se ejecutan sus pruebas en un mismo proceso. *Solución:* las
pruebas se ejecutan por servicio, desde su propio directorio, con una
configuración que agrega al *path* solo ese servicio y la raíz del repositorio.

**Datos personales en los instrumentos.** Algunos instrumentos incluyen columnas
con nombres, correos o matrículas, que no deben llegar al RAG. Una primera
detección por subcadena habría eliminado columnas legítimas, pues «id» aparece en
«idioma» o «identidad». *Solución:* la detección compara por palabra completa del
encabezado normalizado y utiliza una lista configurable (sección 8.2).

[Agregar aquí otras dificultades que consideres relevantes, por ejemplo de
coordinación del equipo o de integración entre ramas.]

---

## 11. Conclusión del capítulo

En este capítulo se describió la construcción de Indagata como un sistema de
ocho microservicios que comparten una base de datos relacional, una base de datos
vectorial y un modelo de lenguaje local, integrados mediante una puerta de enlace
única y una interfaz web en español. El flujo implementado lleva un instrumento
desde su carga hasta su consulta en lenguaje natural: lo depura con una limpieza
asistida que conserva la decisión en manos del investigador, lo describe con
metadatos estandarizados, lo asocia a los indicadores educativos con evidencia
verificable, interpreta sus respuestas sin intervención del modelo de lenguaje
y lo pone a disposición de un RAG que cita sus fuentes.

Durante la construcción, el diseño original se extendió con dos servicios —el de
limpieza y el de conocimiento— que respondieron a problemas observados al probar
el sistema con instrumentos reales: datos crudos con defectos que contaminaban
los metadatos, y un único JSON que no servía bien ni a la asociación de
indicadores ni a la consulta. Estas extensiones reforzaron los dos principios que
guiaron el trabajo: la decisión humana sobre cada transformación y la
trazabilidad de cada resultado.

Quedan como trabajo inmediato la generación de los fragmentos del RAG a partir
del documento final y la tabla de respuestas en formato largo para las consultas
estructuradas. El siguiente capítulo presenta las pruebas realizadas para
verificar el funcionamiento de cada componente y del flujo completo.

---

## Anexos del capítulo (opcional)

[Fragmentos extensos que no caben en el cuerpo del texto. Sugerencias:
`docker-compose.yml` completo, un *Dockerfile* de referencia,
`01_schema.sql`, `config/limpieza.yaml`, `shared/config/escalas_likert.yaml`,
la fórmula de asociación (`asociacion.py`) y un ejemplo de perfil semántico y de
documento final de una encuesta.]
