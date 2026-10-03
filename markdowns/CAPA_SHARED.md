# La capa `shared/`: fundamento del desarrollo de los microservicios

> Documento de carácter escolar. Describe **por qué** existe la carpeta `shared/`
> dentro de Indagata, qué problema resuelve y por qué representa el punto de
> partida del desarrollo backend sobre FastAPI. No documenta la base de datos en
> sí (el esquema Los IDs de Chroma son strings (los que asignas a cada documento) y las colecciones tienen UUID. chroma_id INTEGER y collection_id INTEGER no van a poder guardar esos valores. No estoy de acuerdo con dejar un solo chroma_id en INSTRUMENTO_PROCESADO porque un instrumento genera muchos vectores. Yo haría una tabla chunk (id_chunk PK, id_procesado FK, indice, seccion, chroma_vector_id TEXT, n_tokens) y una tabla coleccion_vectorial (nombre, embedding_model, chunk_size, chunk_overlap), y quitaría chroma_id y collection_id de INSTRUMENTO_PROCESADO. El riesgo de dejarlo así es que no puedas borrar ni reindexar los vectores de un instrumento específico, y vectorizado sería un estado sin nada verificable detrás.físico se describe en otra parte del documento); aquí se explica
> la capa de software que se apoya en ese esquema.

---

## 1. Contexto: de un monolito a varios microservicios

El sistema pasó de ser una sola aplicación (un "monolito") a dividirse en varios
**microservicios** independientes:

- `instrument-service` — recibe y registra los instrumentos (encuestas,
  entrevistas, pruebas).
- `analysis-service` — limpia, enriquece, estandariza y vectoriza la información.
- `api-gateway`, `metadata-service`, `storage-service`, `visualization-service` —
  responsabilidades complementarias.

Cada microservicio es un programa que se ejecuta por separado, pero **todos
hablan con la misma base de datos PostgreSQL**. Y ahí aparece el problema que
`shared/` viene a resolver.

---

## 2. El problema que resuelve `shared/`: la redundancia

Si cada microservicio definiera por su cuenta cómo se ven las tablas de la base
de datos, tendríamos el **mismo código repetido** en varios lugares:

- El `instrument-service` tendría su propia definición de la tabla `usuario`.
- El `analysis-service` tendría *otra* definición de la tabla `usuario`.
- Lo mismo con `instrumento_procesado`, `kpi`, `raw_data`, etc.

Esto genera redundancia, y la redundancia trae un riesgo concreto: la
**desincronización**. Si un día cambia una columna en la base de datos y solo se
actualiza en un servicio, los demás quedan apuntando a una estructura que ya no
existe. El sistema "funciona a medias" y los errores aparecen en producción, no
al programar.

`shared/` elimina esa redundancia aplicando un principio clásico de ingeniería de
software: **DRY (Don't Repeat Yourself — no te repitas)**. Existe **una sola
definición** de cada tabla, de cada DTO y de cada utilidad común, y **todos los
microservicios la importan desde el mismo lugar**:

```python
# Cualquier servicio obtiene lo mismo, desde la misma fuente:
from shared.db.session import get_db
from shared.models import InstrumentoProcesado, Usuario
from shared.schemas import MetadatosDCBase
```

Si mañana cambia una columna, se corrige **una vez** en `shared/` y todos los
servicios quedan alineados automáticamente.

---

## 3. La idea central: una única fuente de verdad

La columna vertebral de todo el diseño es el archivo de esquema SQL
(`infrastructure/postgres/init/01_schema.sql`), que es la **fuente única de
verdad** sobre cómo se ve la base de datos.

La capa `shared/` **refleja** ese esquema en código Python; no inventa su propia
versión. El flujo mental es:

```
                 01_schema.sql  (fuente única de verdad: la base de datos)
                        │
                        │  se refleja 1:1 en código
                        ▼
                     shared/   (modelos, DTOs, utilidades comunes)
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
 instrument-service  analysis-service  …otros servicios
   (importan de shared, no redefinen nada)
```

Esto hace que el código y la base de datos **no puedan contradecirse en silencio**:
si un modelo de `shared/` no coincide con el SQL, se corrige el modelo, nunca al
revés.

---

## 4. Qué contiene `shared/` y por qué

La carpeta está organizada por responsabilidades. Cada subcarpeta cumple un papel
claro dentro de una arquitectura típica de FastAPI:

### `shared/db/` — la conexión y la base común
Centraliza *cómo* los servicios se conectan a la base de datos:

- **`base.py`** define la `Base` de SQLAlchemy de la que heredan **todos** los
  modelos. Al compartir una sola `Base`, SQLAlchemy conoce el mapa completo de
  tablas sin importar qué servicio la cargue. También fija el esquema `tt_rag`
  donde viven las tablas.
- **`session.py`** crea el motor de conexión y la función `get_db()`, que FastAPI
  usa para entregar una sesión de base de datos por cada petición y cerrarla al
  terminar. Es el patrón estándar de **inyección de dependencias** de FastAPI.
- **`security.py`** reúne utilidades de seguridad (manejo de contraseñas, tokens)
  para que la autenticación se haga igual en todos los servicios.
- **`core/`** guarda la configuración (`config.py`) y las **constantes de dominio**
  (`domain_constants.py`): los vocabularios cerrados del sistema (tipos de
  instrumento, estados del pipeline, etc.) definidos **una sola vez** para que
  modelos y validaciones no se desincronicen.

### `shared/models/` — los modelos ORM (el "mapeo")
Aquí vive el **mapeo objeto-relacional (ORM)**: cada tabla de la base de datos se
representa como una clase de Python. Por ejemplo, la tabla `usuario` se vuelve una
clase `Usuario`, y cada columna se vuelve un atributo de esa clase.

Esto es lo que permite trabajar con la base de datos **en términos de objetos**
(`usuario.email`) en lugar de escribir SQL a mano en cada servicio. Es
precisamente "el mapeo que se va a ocupar en los servicios" sin duplicarlo.

> Punto clave del realineado reciente: cada clase de `shared/models/` corresponde
> **exactamente** a una tabla del SQL (mismos nombres, mismas columnas, mismas
> llaves). Se eliminaron modelos que ya no tenían tabla real para no arrastrar
> código muerto ni confusión.

### `shared/schemas/` — los DTOs (contratos de datos)
Los **schemas de Pydantic** definen la forma de los datos que *entran y salen* por
la API (los DTOs — Data Transfer Objects). Mientras los modelos describen cómo se
guarda la información en la base, los schemas describen cómo se **expone** hacia
afuera.

Separar ambas cosas es una buena práctica: la API puede mostrar solo lo necesario
(por ejemplo, nunca el `password_hash`) sin cambiar la estructura interna.

### `shared/repositories/` — acceso a datos reutilizable (patrón repositorio)
El **patrón repositorio** aísla las consultas a la base de datos en funciones
reutilizables (crear, buscar, actualizar, borrar), para que la lógica de negocio
de cada servicio no tenga SQL regado por todos lados. Es otra pieza que, al vivir
en `shared/`, no se reescribe por servicio.

---

## 5. Por qué esto es el inicio de la arquitectura FastAPI

En una aplicación FastAPI bien estructurada, las capas se separan en:

1. **Modelos** (cómo se guardan los datos) → `shared/models/`
2. **Schemas / DTOs** (cómo viajan los datos por la API) → `shared/schemas/`
3. **Dependencias** (conexión y sesión por petición) → `shared/db/session.py`
4. **Repositorios / servicios** (lógica de acceso y de negocio) → `shared/repositories/` y la carpeta de cada servicio
5. **Routers** (los endpoints HTTP) → dentro de cada microservicio

Las cuatro primeras capas son **transversales**: las necesitan todos los
servicios. Por eso `shared/` se construye **primero**. Es el cimiento sobre el que
después cada microservicio levanta solo lo que le es propio (sus routers y su
lógica particular).

En otras palabras: **`shared/` es el punto de partida del desarrollo backend.**
Hasta que esta base no está alineada con la base de datos, no tiene sentido
construir los servicios encima, porque todos dependen de ella.

---

## 6. Resumen de los puntos clave

| Idea | Qué aporta |
|------|-----------|
| **Fuente única de verdad** | La base de datos (`01_schema.sql`) manda; `shared/` la refleja, nunca la contradice. |
| **Sin redundancia (DRY)** | Una sola definición de cada tabla/DTO/utilidad, importada por todos los servicios. |
| **Sin desincronización** | Un cambio se hace una vez y queda alineado en todo el sistema. |
| **Separación de capas** | Modelos, schemas, conexión y repositorios bien divididos: la base de una arquitectura FastAPI limpia. |
| **Cimiento del desarrollo** | `shared/` se construye primero porque todos los microservicios dependen de él. |

En conjunto, la capa `shared/` convierte a varios microservicios independientes en
un sistema **coherente**: hablan el mismo idioma de datos, evitan repetir código y
parten de una base común y confiable. Ese es el verdadero inicio del desarrollo.
