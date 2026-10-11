# Diseño técnico — Rediseño de la calidad del indexado RAG (visualization-service)

> **Iteración 2** — revisión de `design-review.json` incorporada. Las respuestas puntuales a los
> 10 hallazgos (2 HIGH, 6 MEDIUM, 2 NIT) están en §14. Los cambios de fondo se integran en el
> cuerpo del diseño (sobre todo §4.2, §5.1, §5.3, §5.4, §6.3, §7).

## 1. Resumen y objetivo

El chat RAG de Indagata recupera fuentes pero el LLM (Ollama `llama3.2:3b`) responde que
"la información es muy general" porque los chunks indexados son texto pobre: nombres de
columna crudos del CSV más opciones numéricas sueltas. Un chunk real indexado hoy es, por
ejemplo:

```
Organización_y__item1
1
2
3
4
5

Motivación_item3
1
2
3
4
5
```

El objetivo es rediseñar **qué texto** se indexa (no el troceo ni el contrato HTTP) para que
cada chunk sea prosa densa, en español y citable: qué mide el instrumento y qué respondieron
los 180 participantes, agregado por dimensión. Nada de este cambio toca el request/response de
`/rag/index` ni de `/rag/chat`, ni `ollama_client.py`.

El stack queda fijado al existente del `visualization-service` y **no se añaden dependencias
nuevas**: Python 3, FastAPI, `numpy==1.26.4` (ya en `requirements.txt`) y la stdlib
(`statistics`, `re`, `pathlib`, `collections`, `unicodedata`). SQLAlchemy 2.0 (ya presente) para
leer la ruta del `.txt` original desde la BD. Todo el texto generado es en español.

## 2. Confirmación de la causa raíz (verificada leyendo el código y los datos reales)

He leído los archivos citados en el encargo y los datos reales en `storage/raw/`. La causa
raíz queda confirmada:

- **`app/core/sources.py` → `extraer_texto(instrumento_json)`** arma el texto como
  `title + objective + dimensions_explored + (por pregunta) text + options`. Para un
  instrumento subido real (`storage/raw/114c9cc8…__inst_1.estandarizado.v1.json`,
  `instrument_id="upload_1"`), eso produce basura porque:
  - `instrument.title = "enc_01_respondido.csv"` (nombre de archivo, no título real).
  - `instrument.objective = ""` y `instrument.dimensions_explored = []`.
  - `metadata.dublin_core = {}` y `metadata.survey_specific = {}` (quedan vacíos; se pueblan
    sólo si el wizard los rellenó — confirmado leyendo el JSON real).
  - Cada `question.text` es el **nombre de columna crudo** (`"Organizaci├│n_y__item1"`,
    `"Motivaci├│n_item3"`), y `options = ["1","2","3","4","5"]`.
  - Las respuestas de los **180 `respondents[]`** no se agregan ni entran al texto indexado
    en absoluto. Confirmado: `extraer_texto` nunca mira `data["respondents"]`.

- **`app/core/chunking.py` → `trocear(texto)`**: ventanas de ~800 chars con solape 150,
  cortando por párrafo/oración. La lógica es correcta; el problema es la calidad del texto de
  entrada, no el troceo. **No se modifica.**

- **`app/routers/rag.py` → `POST /rag/index`**: por cada `instrumentoId` hace
  `resolver_artefacto(id)` → `extraer_texto` → `chunking.trocear` → `embeddings.embed_texts`
  → `chroma_client.upsert` con metadata `{instrumentoId, titulo, tipo, investigador, kpis,
  investigacionId, chunk_index}`. El chat recupera top_k y arma el prompt con `prompt.py`.

### 2.1 Estructura de datos real (confirmada)

JSON de instrumento subido (`upload_<id_crudo>`), claves top-level: `instrument_id`,
`schema_version`, `instrument{title, objective, dimensions_explored, sections[]}`,
`metadata{dublin_core, survey_specific}`, `design_reference{kpi_hints, note}`, `respondents[]`.

- `instrument.sections[].questions[]` = `{question_id (q1,q2,…), text (nombre de columna
  crudo), type, options?, scale_min?, scale_max?}`. Tipos vistos: `likert`,
  `numerica_continua`, `opcion_multiple`, `binaria`, `abierta`.
- `respondents[]` (180 en inst_1) = `{respondent_id, demographics{edad,genero,semestre},
  answers{ q<id>: valor }}`. `answers` mapea `question_id → valor`: `int`/`float` para
  likert/numérica, `str` para opcion_multiple/binaria/abierta (los binarios llegan como los
  strings `"True"`/`"False"`). Confirmado con el primer respondente real (`q13..q33` llevan
  enteros 1..5; `q6=2.92`, `q7=6`, `q11="False"`).

### 2.2 Dos hallazgos nuevos y críticos descubiertos en los datos reales

Ambos condicionan el diseño del mapeo `question_id → dimensión`:

1. **Mojibake en los nombres de columna del JSON.** El prefijo real indexado es
   `"Organizaci├│n_y__item1"`, `"Motivaci├│n_item1"` (UTF-8 releído como cp1252). Nótese que el
   mojibake está **sólo en el JSON estandarizado**: la cabecera del CSV respondido
   (`storage/raw/*enc_01_respondido.csv`) y el `.txt` original están **bien codificados** en
   UTF-8 (verificado leyendo ambos). Por tanto la reparación de encoding sólo aplica a los
   nombres de columna del JSON, no al `.txt` (ver §5.4 y §14 F10).

2. **El prefijo del JSON está truncado a 15 caracteres y COLISIONA.** `"Habilidades_par_item*"`
   aparece **dos veces** en inst_1 — para "Habilidades para el examen" (q20–q22) y para
   "Habilidades para jerarquizar" (q31–q33). Un mapeo *sólo por prefijo* fusionaría dos
   dimensiones distintas en una. Por eso el método primario de mapeo debe ser **posicional
   contra el `.txt` original** (ver §5.4), con el prefijo como fallback degradado.

El `.txt` original (`storage/raw/*enc_01_original.txt`) tiene 21 ítems redactados en 6
secciones (`--- ORGANIZACIÓN Y PLANIFICACIÓN ---` 7 ítems, `--- HABILIDADES PARA EL EXAMEN ---`
3, `--- MOTIVACIÓN ---` 3, `--- RECURSOS DE APRENDIZAJE ---` 2, `--- ESTRATEGIAS DE CONTROL Y
CONSOLIDACIÓN ---` 3, `--- HABILIDADES PARA JERARQUIZAR ---` 3). El JSON tiene exactamente 21
ítems likert (`q13..q33`) en el **mismo orden**. Esa correspondencia posicional 1-a-1 es la
base del mapeo robusto. El `.txt` también trae en su cabecera `INSTRUMENTO: Inventario de
Estrategias de Aprendizaje y Estudio (IEAE)`, que es la **única fuente del título legible** del
instrumento (porque `dc:title` está vacío e `instrument.title` es el nombre del CSV).

## 3. Decisión de arquitectura

Se introduce un nuevo módulo de agregación estadística y un nuevo módulo de parseo del `.txt`
original, y se reescribe `sources.extraer_texto` para que delegue en ellos y produzca **una
lista de chunks ya redactados** (no un único texto monolítico que luego trocea `chunking`).

### 3.1 ¿Un texto monolítico troceado, o chunks pre-redactados? → Chunks pre-redactados

Dos enfoques posibles:

- **(A) Seguir devolviendo un `str` grande** y dejar que `chunking.trocear` lo parta. Simple,
  cero cambios en `rag.py`, pero el troceo por 800 chars **cortaría** un chunk de hallazgos a la
  mitad (p.ej. partiría la frase de la media de una dimensión), rompiendo la unidad semántica
  "un chunk = una dimensión" que la usuaria pidió explícitamente.

- **(B) Devolver una `list[ChunkIndexable]` ya redactada**, un elemento por dimensión/sección y
  por bloque de hallazgos, cada uno diseñado para caber holgado en la ventana (~800 chars) sin
  trocearse. `rag.py` indexa esa lista directamente.

**Se elige (B).** Es la única forma de garantizar la granularidad pedida ("un chunk por
dimensión", "un chunk de resumen global") y de adjuntar metadata por chunk
(`clase_chunk`, `dimension`). Para no romper `chunking.py` ni duplicar su lógica, cada texto de
chunk se pasa igualmente por un **saneo de longitud**: si un chunk individual excediera la
ventana (raro: una dimensión con muchísimos ítems), se vuelve a trocear con
`chunking.trocear(texto_del_chunk)` heredando la misma metadata, aplanando antes de numerar
(ver §6.4 para la asignación de `id`/`chunk_index`, que resuelve el riesgo de ids duplicados).

Esto exige un cambio **aditivo y retrocompatible** en el contrato interno entre `sources` y
`rag.py` (ver §7): `extraer_texto` se mantiene (devolviendo `str`, para no romper tests ni el
fallback), y se añade `construir_chunks(artefacto, instrumento_id) -> list[ChunkIndexable]`.

## 4. Módulo nuevo: `app/core/agregacion.py` (estadística de respuestas)

Agrega las respuestas de `respondents[]` **por dimensión** y produce prosa en español. Usa
`numpy` para los cálculos vectoriales y la stdlib donde baste. **Nunca** genera un chunk por
respondente.

### 4.1 Tipos y firmas

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ResumenItem:
    question_id: str
    texto: str              # texto redactado del .txt si existe; si no, etiqueta de columna normalizada
    media: float
    de: float               # desviación estándar (poblacional, ddof=0)
    n: int

@dataclass(frozen=True)
class HallazgoDimension:
    dimension: str          # nombre completo de la dimensión
    tipo: str               # "likert" | "numerica" | "categorica"
    n: int                  # nº de respondentes con al menos un valor válido
    # Likert:
    media: float | None = None
    de: float | None = None
    pct_alto: float | None = None       # % que respondió en el extremo alto
    item_mas_alto: ResumenItem | None = None
    item_mas_bajo: ResumenItem | None = None
    # Numérica (promedio_gpa, horas_trabajo_semana):
    minimo: float | None = None
    maximo: float | None = None
    # Categórica / binaria: top categorías con su %
    distribucion: list[tuple[str, float]] = field(default_factory=list)

# Coacción numérica única (ver §4.2):
def _num(v) -> float | None: ...

def agregar_likert(items: list[tuple[str, str, int, int]],
                   respondents: list[dict], dimension: str) -> HallazgoDimension | None: ...
# items = [(question_id, texto_redactado, scale_min, scale_max), ...] de la dimensión.

def agregar_numerica(question_id: str, texto: str,
                     respondents: list[dict]) -> HallazgoDimension | None: ...

def agregar_categorica(question_id: str, texto: str, tipo: str,
                       respondents: list[dict], top: int = 5) -> HallazgoDimension | None: ...

def redactar_hallazgo(h: HallazgoDimension) -> str: ...          # un chunk de prosa
def redactar_resumen_global(hallazgos: list[HallazgoDimension],
                            n_respondentes: int, titulo: str) -> str: ...
```

### 4.2 Reglas de cálculo (tipado y coacción numérica explícitos)

**Coacción numérica única (`_num`)** — aplicada en toda la agregación para no reventar con
`str` no numéricos ni confundir `bool` con número:

```python
def _num(v) -> float | None:
    if isinstance(v, bool):          # bool ES subclase de int en Python: excluir explícito
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None
```

- **Likert por dimensión:**
  - Se recorren los `respondents`. Para cada respondente se toman sus valores en los
    `question_id` de la dimensión, pasados por `_num`; los `None` se descartan.
  - Vector agregado de la dimensión = concatenación de todos los valores válidos (todos los
    ítems × todos los respondentes).
  - `n` (de la dimensión) = **nº de respondentes con ≥1 valor `_num` no-`None`** en la
    dimensión. Si `n == 0`, `agregar_likert` devuelve `None` y **no se emite chunk** (§4.4).
  - `media = float(np.mean(vector))`, `de = float(np.std(vector, ddof=0))`.
  - `pct_alto`: por defecto `% de valores >= 4` sobre escala 1..5. Si `scale_min/scale_max`
    difieren de 1..5, el umbral es el **tercio superior** del rango efectivo:
    `umbral = scale_min + 2*(scale_max - scale_min)/3` y `pct_alto = media(valor >= umbral)*100`.
    El rango efectivo es el de los `items` (todos comparten escala en un instrumento likert); si
    `scale_min >= scale_max` o faltan, se usa 1..5 (§8).
  - `item_mas_alto`/`item_mas_bajo`: por cada `question_id` se calcula un `ResumenItem` con su
    media/DE/n sobre valores válidos; se toma el de media máxima y el de media mínima. Si un ítem
    no tiene ningún valor válido, se excluye del cómputo de extremos.
- **Numérica (`numerica_continua`):** se recogen los `_num` válidos de ese `question_id` en
  todos los respondentes. Si quedan 0 valores ⇒ `None` (sin chunk). Si no: `media`, `de`,
  `minimo`, `maximo`. Cada numérica es su propia "dimensión" (un chunk).
- **Categórica/binaria (`opcion_multiple`, `binaria`):** `collections.Counter` sobre
  `str(valor).strip()` de los valores no vacíos/no `None`; se descartan vacíos. Si `n == 0`
  (ningún valor) ⇒ `None` (sin chunk). Se reportan las `top` categorías con su porcentaje
  `cuenta/n*100`. Para `binaria`, los literales `"True"`/`"False"` se redactan como "sí"/"no".
- **`abierta`:** NO se agrega (p.ej. `id_respondente`). Se omite de hallazgos.
- **Resumen global:** `n` respondentes, lista de dimensiones evaluadas y 2–3 hallazgos más
  salientes (dimensión likert con media más alta y más baja, numérica destacada).

### 4.3 Estilo de redacción (español, prosa densa y citable)

Toda redacción **sólo se produce cuando los campos existen** (nunca se formatea un `None`/`nan`;
ver §4.4). `redactar_hallazgo` produce, para una dimensión likert con `.txt` disponible:

> En la dimensión **Motivación**, la media de respuesta fue 4.1/5 (DE 0.8) y el 72 % del
> estudiantado respondió 4 o 5. El ítem con media más alta fue «Me esfuerzo más cuando el tema
> me parece interesante» (media 4.4) y el más bajo «Encuentro significativo el contenido de lo
> que estudio» (media 3.6). n = 180 respondentes.

En **modo degradado** (sin `.txt`), el `ResumenItem.texto` no es la pregunta redactada sino la
**etiqueta de columna normalizada** (prefijo normalizado + número de ítem). La misma frase
quedaría, por ejemplo: *«El ítem con media más alta fue "Motivación ítem 1" (media 4.4)…»*. Es
decir, se cita el ítem con su etiqueta legible, nunca el mojibake crudo (coherente con §5.4
método 2 y §14 F9).

Para numérica:

> El promedio general (GPA) de los 180 respondentes fue 3.1 (DE 0.5; mínimo 1.5, máximo 4.0).

Para categórica:

> Respecto al tipo de universidad, el 54 % declaró asistir a una institución privada, el 33 %
> pública y el 13 % mixta (n = 180).

Todos los números se formatean con un decimal (`f"{x:.1f}"`) y porcentajes enteros
(`round(pct)`), para evitar ruido numérico que confunda al LLM.

### 4.4 Casos borde numéricos (comportamiento definido)

Para que `nan`/división por cero no se cuelen jamás al texto citable:

- Si tras filtrar con `_num` el conjunto queda vacío (`n == 0`), la función `agregar_*`
  devuelve **`None`** y el orquestador **no emite** ese chunk (consistente con la degradación
  de §6.3). No se llama a `np.mean([])` para formatear.
- Los porcentajes (`pct_alto`, distribución categórica) **sólo se calculan con `n > 0`**; nunca
  se divide por cero.
- `redactar_hallazgo`/`redactar_resumen_global` comprueban que cada campo necesario no sea
  `None` antes de interpolarlo; si por defensa en profundidad recibieran un `HallazgoDimension`
  con un campo clave en `None`, omiten esa cláusula en vez de imprimir `nan`.

## 5. Módulo nuevo: `app/core/original_txt.py` (estructura + mapeo a dimensión)

Responsable de (a) localizar y leer el `.txt` original, (b) parsearlo en secciones/ítems
redactados y el título legible, y (c) exponer el **mapeo `question_id → dimensión`** y el texto
redactado por `question_id`.

### 5.1 Acceso al `.txt` original — decisión

Opciones evaluadas para que el `visualization-service` acceda al original:

- **(i) storage-service `GET /almacenamiento/artefacto/{tipo}/{id}`.** Descartada: ese endpoint
  sólo devuelve `contenido` cuando el artefacto es JSON (`metadata`/`analysis`). El `.txt`
  original se guarda como artefacto **`raw` binario**; `obtener_artefacto` no lee su texto
  (confirmado en `storage-service/app/routers/almacenamiento.py` y `core/store.py`). No sirve.

- **(ii) BD → `raw_data.raw_archivo_original` por `id_crudo`, luego leer el archivo de disco.**
  Elegida. Detalles verificados en el código:
  - El `instrument_id` del JSON es `"upload_<id_crudo>"`, pero el **parámetro HTTP** que recibe
    `/rag/index` por `instrumentoId` puede llegar como `"1"` (sin prefijo). Por eso la derivación
    acepta **ambas** formas: `id_crudo = int(str(instrumento_id).removeprefix("upload_"))`
    (y si no parsea, no hay BD-path → fallback disco de §5.1.1).
  - La ruta NO está en `InstrumentoProcesado` sino en **`RawData.raw_archivo_original`**
    (confirmado en `shared/models/raw_data.py`). Es una **tabla y consulta distinta** de la de
    `sources._resolver_desde_bd` (que lee `InstrumentoProcesado.ruta_json`). Reusamos el
    *patrón* de acceso (crear engine con `settings.DATABASE_URL`, `Session`, `select`, degradar
    en silencio si falta BD/driver), pero la consulta es
    `select(RawData.raw_archivo_original).where(RawData.id_crudo == id_crudo)`.

Se elige **(ii)**. Es consistente con cómo `sources.py` ya resuelve rutas por `id_crudo` desde
la BD y no inventa un canal nuevo.

**Resolución de la ruta a archivo (fix F1 — dos convenciones).** El valor de
`raw_archivo_original` es **relativo a la raíz de `storage/`** (el backend de upload persiste
`"raw/<hash>__enc_01_original.txt"`, verificado en
`instrument-service/app/storage/local_backend.py`: `ruta=f"{_RAW_SUBDIR}/{unique_name}"`). En
cambio, la ruta de *seed* (`scripts/seed_demo.py`) guarda `"storage/raw/<archivo>"`. Por eso
`ruta_original` **prueba ambas convenciones** y se queda con la que exista:

```python
candidatos = [
    settings.raw_path_abs.parent / rel,   # storage/ + "raw/..."  → caso upload (primario)
    settings.PROJECT_ROOT / rel,          # PROJECT_ROOT + "storage/raw/..." → caso seed
]
ruta = next((c for c in candidatos if c.is_file()), None)
```

(`settings.raw_path_abs.parent` es `…/storage`, idéntico a la raíz que usa el backend de upload
en `local_backend.leer`.)

#### 5.1.1 Fallback sin BD / dev local

Si la BD no está disponible (igual que hoy en `_resolver_desde_bd`, que degrada en silencio) o
`raw_archivo_original` es `NULL`, se intenta localizar el `.txt` en `settings.raw_path_abs` por
heurística de nombre: derivar el nombre base del `instrument.title`
(`"enc_01_respondido.csv"` → `"enc_01"`) y hacer `glob("*enc_01_original.txt")`. Si hay varios,
se toma el más reciente por `mtime`. Si nada casa, se degrada (ver §6.3).

### 5.2 Firmas

```python
@dataclass(frozen=True)
class SeccionOriginal:
    titulo: str              # p.ej. "Organización Y Planificación" (title-case del header)
    items: list[str]         # textos redactados en orden

@dataclass(frozen=True)
class EstructuraOriginal:
    titulo_instrumento: str | None   # de la cabecera "INSTRUMENTO:" del .txt
    secciones: list[SeccionOriginal]

def ruta_original(instrumento_id: str) -> Path | None: ...        # vía BD (2 convenciones), luego disco
def leer_texto_original(instrumento_id: str) -> str | None: ...   # lee el archivo si existe
def parsear_estructura(texto: str) -> EstructuraOriginal: ...     # título + secciones + ítems
def construir_mapa_dimension(estructura: EstructuraOriginal,
                             questions_likert: list[dict]) -> dict[str, tuple[str, str]]: ...
# devuelve question_id -> (nombre_dimension, texto_redactado); {} si no es aplicable (ver §5.4)
```

### 5.3 Parseo del `.txt`

`parsear_estructura` recorre líneas:

- **Título legible del instrumento (fix F3):** la primera línea que casa
  `^\s*INSTRUMENTO:\s*(.+?)\s*$` captura `titulo_instrumento` (p.ej. "Inventario de Estrategias
  de Aprendizaje y Estudio (IEAE)"). Esta cabecera **ya no se descarta**: es la única fuente del
  título real (ver §6.1 para su uso en la precedencia). El resto de cabeceras (`ID:`, `Fuente:`,
  `INSTRUCCIONES:`, las líneas de la escala `1 = …`, `FIN DEL INSTRUMENTO` y las filas de
  casillas `[ ] 1 …`) sí se ignoran.
- **Secciones:** una línea que casa `^-{2,}\s*(.+?)\s*-{2,}$` abre una sección nueva con ese
  título (normalizado a *Capitalización de Título*).
- **Ítems:** una línea que casa `^\s*(\d+)\.\s+(.+)$` es un ítem redactado; se guarda el texto
  sin el número, asociado a la sección abierta en curso. Las líneas de casillas de respuesta no
  casan este patrón y se ignoran.

El resultado es `EstructuraOriginal(titulo_instrumento, secciones[])` con los ítems en orden.

### 5.4 Método de mapeo `question_id → dimensión` — decisión y algoritmo

Dos métodos, con precedencia:

**1. Posicional contra el `.txt` (primario).** Algoritmo explícito (fix F4):

```python
def construir_mapa_dimension(estructura, questions_likert):
    plano = [(sec.titulo, item)
             for sec in estructura.secciones
             for item in sec.items]            # aplanado en orden de lectura
    if not plano or len(plano) != len(questions_likert):
        return {}                              # NO aplicable → el llamador usa el fallback
    mapa = {}
    for q, (titulo_dim, texto_item) in zip(questions_likert, plano):
        mapa[q["question_id"]] = (titulo_dim, texto_item)
    return mapa
```

- `questions_likert` es la lista de preguntas con `type == "likert"` en el orden del JSON
  (`q13..q33`). El `i`-ésimo ítem likert ↔ `i`-ésimo ítem redactado recorriendo secciones en
  orden.
- La **condición de aplicabilidad** es estrictamente `len(plano) == len(questions_likert)`. En
  inst_1 ambos son 21. Secciones vacías (sin ítems) simplemente no aportan tuplas al `plano`;
  ítems extra o faltantes rompen la igualdad de conteo y fuerzan el fallback — nunca un mapeo
  parcial silencioso.
- Esto resuelve la **colisión de prefijos truncados** (§2.2): "Habilidades para el examen"
  (q20–q22) y "Habilidades para jerarquizar" (q31–q33) se distinguen por su **posición**, no por
  el prefijo ambiguo. Además enriquece cada `ResumenItem.texto` con la pregunta redactada real.

**2. Por prefijo normalizado (fallback).** Si no hay `.txt`, o los conteos no cuadran, se agrupa
por el prefijo del nombre de columna hasta `_item`:

- Normalización/reparación de mojibake (sólo nombres de columna del JSON): primero se intenta
  reparar `cp1252↔utf-8` reinterpretando `nombre.encode("cp1252").decode("utf-8")` y
  quedándose con el resultado si produce un string con acentos válidos (si lanza
  `UnicodeError`, se deja el original). Luego se recorta el sufijo `_item\d+$`.
- **Etiqueta de dimensión final (fix F5):** como el prefijo truncado colisiona y queda feo, la
  etiqueta de dimensión del fallback se arma como **`"Dimensión <Prefijo Reparado> (agrupación
  aproximada)"`** (p.ej. *"Dimensión Habilidades Par (agrupación aproximada)"*), dejando claro
  en el propio texto citable que es una agrupación imprecisa. Si `section.name` del JSON
  aportara algo mejor que `"Reactivos del módulo"` (genérico, no sirve en inst_1), se preferiría;
  como en los datos reales no aporta, se usa el prefijo. Cuando dos `question_id` caen en el
  mismo prefijo colisionado se emite un **`WARNING`** ("colisión de prefijo truncado: la
  dimensión X fusiona ítems de secciones distintas").
- La etiqueta por ítem para `ResumenItem.texto` en este modo es
  `f"{prefijo_reparado} ítem {n}"` (p.ej. "Motivación ítem 1"), nunca el mojibake crudo.

**Se elige el método posicional como primario y el prefijo como fallback**, decidido así por los
hallazgos reales de §2.2. La elección es automática según la condición de conteo; se registra en
log a nivel `INFO` cuál se usó, para diagnóstico.

## 6. Chunks resultantes, metadata y degradación

### 6.1 Forma de los chunks

`sources.construir_chunks(artefacto, instrumento_id)` devuelve `list[ChunkIndexable]`:

```python
@dataclass(frozen=True)
class ChunkIndexable:
    texto: str
    clase: str          # "estructura" | "hallazgos"
    dimension: str      # "" para el resumen global / cabecera de estructura
```

**(A) Chunks de ESTRUCTURA** (qué mide el instrumento y cómo):
- Un chunk de **cabecera**: título real + `dc:description` y
  `survey_specific.constructo_principal` si existen. **Precedencia del título (fix F3):**
  `dc:title` → `estructura.titulo_instrumento` (cabecera del `.txt`) → `instrument.title`. En
  inst_1, como `dc:title` está vacío, el título efectivo es el del `.txt` ("Inventario de
  Estrategias de Aprendizaje y Estudio (IEAE)"), no "enc_01_respondido.csv".
- **Un chunk por sección/dimensión del `.txt`**: título de la dimensión + sus ítems redactados
  numerados. Si no hay `.txt`, se degrada a: etiqueta de dimensión (del prefijo, §5.4 método 2)
  + los nombres de columna normalizados de esa dimensión como ítems.

**(B) Chunks de HALLAZGOS** (estadística agregada, en prosa — §4.3):
- **Un chunk por dimensión** likert (media, DE, % extremo alto, ítem más alto/bajo con su texto,
  n).
- **Un chunk por numérica** (`promedio_gpa`, `horas_trabajo_semana`).
- **Un chunk por categórica/binaria** (distribución top-k).
- **Un chunk de resumen global** (n, dimensiones evaluadas, hallazgos salientes).

### 6.2 Nota sobre el título en la metadata de Chroma

La metadata de cada chunk sigue llevando `titulo` (ver §6.3). Ese `titulo` se calcula con la
misma precedencia de §6.1 (incluyendo el `.txt`), de modo que las fuentes citadas en el chat
muestren el título real del instrumento y no el nombre del CSV. `extraer_metadata` se extiende de
forma mínima para aceptar un `titulo_override` opcional (el del `.txt`), manteniendo su firma
retrocompatible con un parámetro con valor por defecto.

### 6.3 Metadata en Chroma

El router sigue escribiendo `{instrumentoId, titulo, tipo, investigador, kpis, investigacionId,
chunk_index}` **sin cambios de clave** (compatibilidad con `rag.py` y el frontend). Se **añaden**
dos campos escalares por chunk, sin romper nada:

- `clase_chunk`: `"estructura"` | `"hallazgos"`.
- `dimension`: nombre de la dimensión o `""`.

El filtro `where={"instrumentoId": {"$in": [...]}}` del chat sigue funcionando. `_construir_
fuentes` y `FuenteChatOut` no cambian (leen `instrumentoId/titulo/tipo/investigador/kpis/
fragmento`); los campos añadidos simplemente se ignoran ahí.

### 6.4 Numeración de ids y chunk_index (fix F7)

Como un `ChunkIndexable` puede expandirse en varias piezas (cuando su `texto` supera la ventana
y se re-trocea con `chunking.trocear`), la numeración se hace **sobre la lista aplanada**, nunca
sobre la lista original, para no duplicar `id` ni `chunk_index`:

```python
piezas: list[tuple[str, dict]] = []           # (texto, metadata_base_del_chunk)
for ch in chunks_ix:
    textos = [ch.texto] if len(ch.texto) <= chunking.VENTANA else chunking.trocear(ch.texto)
    for t in textos:
        piezas.append((t, {"clase_chunk": ch.clase, "dimension": ch.dimension}))

documents = [t for t, _ in piezas]
ids       = [f"{investigacionId}:{instrumentoId}:{n}" for n in range(len(piezas))]
metadatas = [ {**base_comun, **extra, "chunk_index": n}
              for n, (_, extra) in enumerate(piezas) ]
```

Así `id`/`chunk_index` son secuenciales y únicos aunque un chunk se expanda; la metadata
(`clase_chunk`, `dimension`) se propaga a todas sus piezas.

### 6.5 Degradación grácil (ningún caso rompe el indexado)

| Situación | Comportamiento |
|---|---|
| No hay `.txt` original (ni BD ni disco) | Estructura degrada a nombres de columna normalizados; mapeo por prefijo (§5.4 m2). Hallazgos se generan igual (no dependen del `.txt`). |
| Conteos `.txt`↔JSON no coinciden | `construir_mapa_dimension` devuelve `{}` ⇒ mapeo por prefijo; se loguea `WARNING`. |
| `respondents` vacío o ausente | No se generan chunks de hallazgos; sólo los de estructura. |
| Dimensión/ítem sin ningún valor válido (`n==0`) | `agregar_*` devuelve `None`; ese chunk no se emite (§4.4). Nunca se formatea `nan`. |
| Faltan `scale_min/scale_max` o `min>=max` | Likert asume 1..5; `pct_alto` por umbral de tercio superior sobre 1..5. |
| Valores no numéricos / `bool` en answers likert | `_num` los descarta (no abortan). |
| `metadata`/`survey_specific`/`dc:title` vacíos | Título cae a `.txt` y luego a `instrument.title`; cabecera usa lo que haya; nunca falla. |
| `.txt` ilegible / `UnicodeDecodeError` | `leer_texto_original` devuelve `None` (no inyecta `\ufffd`); se degrada a prefijo. |
| Un chunk individual > ventana | Se re-trocea con `chunking.trocear` heredando metadata; numeración aplanada (§6.4). |
| JSON sin `instrument`/sin preguntas | `construir_chunks` devuelve `[]`; el router marca el instrumento `omitido` (ruta ya existente). |

Patrón de implementación: cada bloque (`estructura`, cada tipo de hallazgo) va envuelto en su
propio `try/except` con log a nivel `WARNING` y continuación; una dimensión que falle no tumba
el resto. Esto espeja el estilo defensivo ya presente en `sources.py` (`_como_dict`,
`_como_lista`, `_texto`).

## 7. Cambios por archivo (contrato interno)

- **`app/core/agregacion.py`** (nuevo): §4. Puro, sin I/O; recibe listas/dicts y devuelve
  dataclasses y strings. Totalmente **unit-testable**.
- **`app/core/original_txt.py`** (nuevo): §5. I/O de disco + consulta BD a `RawData` (reusa el
  *patrón* de `sources._resolver_desde_bd`, con su propia consulta y la resolución de ruta de
  §5.1). El parseo (`parsear_estructura`, `construir_mapa_dimension`) es puro y unit-testable; la
  resolución de ruta se testea con un `.txt` temporal y la BD mockeada.
- **`app/core/sources.py`**:
  - `extraer_texto(...)` se conserva con su firma `(json) -> str` (compat con tests y como
    último fallback: si `construir_chunks` devolviera `[]` por un bug, el router aún puede
    trocear este `str`). Internamente puede delegar su cabecera a los nuevos módulos.
  - **Nuevo** `construir_chunks(artefacto, instrumento_id) -> list[ChunkIndexable]` (§6.1), que
    orquesta `original_txt` + `agregacion`.
  - `extraer_metadata` gana un parámetro opcional `titulo_override: str | None = None` (§6.2),
    retrocompatible; `extraer_kpis` sin cambios.
- **`app/routers/rag.py`** → `indexar`: en vez de `texto = extraer_texto(...)` +
  `chunking.trocear(texto)`, llama `chunks_ix = sources.construir_chunks(artefacto, id)`. Si
  `chunks_ix` está vacío, degrada al camino actual (`extraer_texto` + `trocear`) y, si aún así
  no hay texto, marca `omitido` (lógica ya existente). Aplana a `piezas`, numera y arma
  `documents`/`ids`/`metadatas` según §6.4. El resto (embeddings, upsert, respuesta) **no
  cambia**.
- **`app/core/chunking.py`, `ollama_client.py`, `prompt.py`, `chroma_client.py`,
  `embeddings.py`, schemas**: **sin cambios**.

El contrato HTTP de `/rag/index` y `/rag/chat` (request/response) queda idéntico.

## 8. Validación de entradas (por cada entrada externa)

| Entrada | Reglas |
|---|---|
| `instrumento_id` (param HTTP) y `instrument_id` (JSON) | Para la BD: `id_crudo = int(str(id).removeprefix("upload_"))`; acepta `"1"` y `"upload_1"`. Si no parsea ⇒ sin BD-path ⇒ fallback disco. Opcional para hallazgos (la agregación no necesita id_crudo). |
| `.txt` original (archivo) | Lectura `utf-8` **estricta**; `UnicodeDecodeError`/`OSError`/vacío ⇒ `None` ⇒ degradación por prefijo (no se usa `errors="replace"`, para no inyectar `\ufffd` en prosa citable). Límite blando de tamaño (2 MB) para no cargar binarios enormes por error. |
| `answers[q]` likert | `_num(valor)` (excluye `bool`, acepta int/float y str parseable); `None`/no numérico se descarta. |
| `answers[q]` numérica | `_num(valor)`; descartar inválidos. |
| `answers[q]` categórica/binaria | `str(valor).strip()`; vacío/`None` se omite del conteo. |
| `scale_min/scale_max` | Opcionales; default 1/5; si `min>=max` se ignoran y se usa 1..5. |
| `respondents` | Lista; si vacía/ausente ⇒ 0 chunks de hallazgos (no error). |

## 9. Invariantes y su dueño

- **"Nunca un chunk por respondente"** — dueño: `agregacion.py`, por construcción (sus funciones
  agregan sobre `respondents` y devuelven un objeto por dimensión; `sources` no itera
  respondentes para emitir chunks). Elegido ahí porque es la única capa que ve las respuestas.
- **"La metadata de Chroma siempre tiene al menos `{instrumentoId, titulo, tipo}`"** — dueño:
  `rag.py` al armar `metadatas` (igual que hoy; los campos nuevos son aditivos). Elegido ahí
  porque es el único punto que escribe en Chroma.
- **"El indexado nunca falla por datos incompletos"** — dueño: `sources.construir_chunks`
  (envoltura `try/except` por bloque) + la ruta `omitido` ya existente en `rag.py`. Elegido en
  `construir_chunks` porque es el orquestador que conoce qué bloque falló y puede continuar.
- **"Nunca `nan`/`\ufffd` en el texto citable"** — dueño: `agregacion` (§4.4, no formatea
  conjuntos vacíos) y `original_txt.leer_texto_original` (utf-8 estricto). Elegido en origen
  (donde se genera cada string) para que ningún consumidor tenga que sanear.
- **"Español en todo el texto generado"** — dueño: `agregacion.redactar_*` y las plantillas de
  estructura; no se interpola texto de origen inglés.

## 10. Testabilidad

- **Unit (sin I/O, lo más valioso):**
  - `agregacion`: dado un `respondents` sintético pequeño, verificar media/DE/`pct_alto`,
    ítem más alto/bajo, distribución categórica y las cadenas redactadas (formato de números,
    español). Casos borde: todos `None` ⇒ `None` (sin chunk, sin `nan`); un solo respondente;
    escala no 1..5; `bool` en answers (se excluye); str numérico con coma decimal.
  - `original_txt.parsear_estructura`: dado el `.txt` de ejemplo, `titulo_instrumento` capturado,
    6 secciones y 21 ítems en orden. `construir_mapa_dimension`: mapeo posicional correcto con la
    colisión de `Habilidades_par` resuelta; conteo desigual ⇒ `{}`; fallback por prefijo con
    mojibake reparado y etiqueta "(agrupación aproximada)".
  - `ruta_original`: con `raw_archivo_original = "raw/x_original.txt"` resuelve bajo
    `storage/`; con `"storage/raw/x_original.txt"` resuelve bajo `PROJECT_ROOT`; ambas con un
    `.txt` temporal y la consulta a `RawData` mockeada.
  - `sources.construir_chunks`: con un artefacto sintético, verificar nº y `clase_chunk` de los
    chunks y que la degradación (sin `.txt`, sin respondents) produce la combinación esperada;
    verificar que un chunk sobredimensionado se expande con ids/chunk_index únicos (§6.4).
- **Integración:** `POST /rag/index` sobre `storage/raw/*inst_1.estandarizado.v1.json` real
  (resolución por fallback disco), afirmando que los documentos indexados contienen prosa con
  medias/porcentajes y nombres de dimensión reales, y que el contrato de respuesta no cambió.
  La BD y Chroma se mockean/omiten según el patrón de los tests existentes del servicio.

El diseño es testable porque toda la lógica densa (estadística, parseo, mapeo) es pura y queda
aislada del I/O (BD, disco, Chroma, embeddings).

## 11. Supuestos

1. El `instrument_id` del JSON subido es `upload_<id_crudo>`; el parámetro HTTP puede venir con o
   sin el prefijo `upload_`. La derivación acepta ambas formas (§5.1, §8).
2. Los ítems likert del JSON están en el **mismo orden** que los ítems del `.txt` original
   (confirmado en inst_1: q13..q33 ↔ 21 ítems). El mapeo posicional depende de esto; si no se
   cumple (conteo desigual), degrada a prefijo sin romper.
3. Escala likert 1..5 por defecto cuando faltan `scale_min/max` (confirmado como caso real).
4. `raw_archivo_original` es una ruta relativa que resuelve bajo `storage/` (caso upload) o bajo
   `PROJECT_ROOT` (caso seed); `ruta_original` prueba ambas (fix F1). Requiere que el
   `visualization-service` comparta el working tree/volumen de `storage/`.
5. `numpy==1.26.4` y la stdlib bastan; no se añaden dependencias.

## 12. Riesgos

- **Mapeo posicional erróneo** si un instrumento futuro reordena ítems o mezcla likert con no
  likert intercalados. Mitigación: condición de conteo estricta + fallback por prefijo + log del
  método usado.
- **Dimensión fusionada en el fallback por prefijo** (p.ej. las dos "Habilidades para…" caen en
  `Habilidades_par`). Aceptado y señalizado: la etiqueta lleva "(agrupación aproximada)" y se
  emite `WARNING` (§5.4 m2). Sólo ocurre cuando no hay `.txt` o el conteo no cuadra; con `.txt`
  presente (caso normal) el mapeo posicional las separa.
- **`.txt` inaccesible desde el visualization-service** si corre en un contenedor sin el volumen
  de `storage/` montado o sin BD. Mitigación: degradación por prefijo (estructura con nombres de
  columna normalizados); los chunks de hallazgos siguen siendo buenos y resuelven el grueso del
  problema.
- **Mojibake no reparable** en algún encoding distinto a cp1252↔utf-8. Mitigación: si la
  reparación falla, se usa el string normalizado (NFKD) tal cual; sigue agrupando por prefijo.
- **Chunks de hallazgos demasiado densos** para `llama3.2:3b`. Mitigación: formato numérico
  compacto (1 decimal), un hecho por frase; el resumen global da el "titular" recuperable.
- **Coste de agregación** con muchos instrumentos/respondentes en un `/rag/index`. Es
  O(n·items) con numpy; 180×21 es trivial. Sin riesgo práctico a esta escala.
- **Deriva de esquema** si `domain_builder` cambia la forma de `respondents`/`answers`. Mitigado
  por el acceso defensivo (`_como_dict`/`_como_lista`, `_num`) y los tests unitarios.

## 13. Alcance (lo que NO cambia)

- Contrato HTTP de `/rag/index` y `/rag/chat` (request/response), claves existentes de metadata.
- `ollama_client.py` (el fix de `keep_alive='-1m'` ya está aplicado), `prompt.py`,
  `chunking.py`, `embeddings.py`, `chroma_client.py`, los schemas.
- No se añaden dependencias a `requirements.txt`.
- No se corrige la resolución del *fallback raw* (`sources._resolver_fallback_raw`), que para un
  upload resolvería al seed equivocado (`inst_01.v1.json`), por quedar fuera del encargo; el
  camino real de resolución del artefacto subido es storage-service/BD y no se toca.

## 14. Notas de respuesta a los hallazgos de la revisión (`design-review.json`)

Veredicto previo: **CHANGES_REQUESTED**. Las 10 observaciones se **atienden** (ninguna se
backloguea ni se ignora); los cambios son coherentes con los requisitos originales (mejora interna
de calidad del texto, sin tocar el contrato HTTP ni añadir dependencias).

- **F1 (HIGH) — Resolución del `.txt` por BD con convención de ruta equivocada.** Atendido en
  §5.1 (fix F1): `ruta_original` prueba **ambas** convenciones —
  `settings.raw_path_abs.parent / rel` (caso upload, primario) y `settings.PROJECT_ROOT / rel`
  (caso seed)— y usa la que exista. Supuesto 4 corregido en §11.
- **F2 (HIGH) — `raw_archivo_original` vive en `RawData`, no en `InstrumentoProcesado`; espacios
  de id.** Atendido en §5.1 (ii) y §8: `id_crudo = int(str(id).removeprefix("upload_"))` acepta
  `"1"` y `"upload_1"`; se consulta explícitamente
  `select(RawData.raw_archivo_original).where(RawData.id_crudo == id_crudo)`, documentando que es
  otra tabla/consulta distinta de `_resolver_desde_bd`.
- **F3 (MEDIUM) — Conflicto §6.1 vs §5.3 sobre el título real.** Atendido: §5.3 ahora **captura**
  `titulo_instrumento` con `^\s*INSTRUMENTO:\s*(.+)$` (ya no lo descarta) y lo expone en
  `EstructuraOriginal`; §6.1/§6.2 fijan la precedencia de título `dc:title → .txt →
  instrument.title`.
- **F4 (MEDIUM) — Algoritmo de mapeo posicional explícito.** Atendido en §5.4 método 1: se
  especifica el aplanado `plano = [(sec.titulo, item) …]`, la condición
  `len(plano) == len(questions_likert)` (si no, `{}` ⇒ fallback), el `zip` por índice y el
  guardado de `(dimensión, texto_redactado)` por `question_id`. Secciones vacías e ítems
  sobrantes quedan cubiertos.
- **F5 (MEDIUM) — Fallback por prefijo: etiqueta fusionada indistinguible.** Atendido en §5.4
  método 2: etiqueta explícita `"Dimensión <Prefijo> (agrupación aproximada)"`, `WARNING` de
  colisión y preferencia por `section.name` si aportara; documentada la fusión en §12.
- **F6 (MEDIUM) — Validación/typing de answers likert.** Atendido en §4.2: función única `_num`
  (excluye `bool`, acepta int/float y str parseable, `None` si no); `n` por dimensión = nº de
  respondentes con ≥1 `_num` no-`None`.
- **F7 (MEDIUM) — Re-troceo pierde metadata / ids duplicados.** Atendido en §6.4: se aplana cada
  `ChunkIndexable` a `piezas` **antes** de numerar; `id`/`chunk_index` secuenciales sobre la
  lista aplanada; `clase_chunk`/`dimension` se propagan a cada pieza.
- **F8 (MEDIUM) — Casos borde numéricos (`nan`, división por cero).** Atendido en §4.4: `n==0`
  ⇒ `agregar_*` devuelve `None` y no se emite chunk; porcentajes sólo con `n>0`; nunca se
  formatea `nan`.
- **F9 (NIT) — En fallback, `ResumenItem.texto` vs ejemplo de §4.3.** Atendido en §4.3: en modo
  degradado el ítem más alto/bajo se nombra con la etiqueta normalizada
  (`"<Prefijo> ítem <n>"`), no con el mojibake.
- **F10 (NIT) — `errors='replace'` vs reparación de mojibake.** Atendido en §8 y §2.2: el `.txt`
  se lee en **utf-8 estricto** y degrada a `None` ante `UnicodeDecodeError` (sin `\ufffd`); la
  reparación cp1252↔utf-8 se aplica **sólo** a los nombres de columna del JSON, cuyo mojibake es
  el real.

## 15. Respuesta a la revisión final (iteración 2 → APROBADO para implementar)

Veredicto previo: **CHANGES_REQUESTED (0 HIGH, 2 MEDIUM, 3 NIT)**. Las observaciones se integran
aquí como especificación vinculante para la implementación. Con esto el diseño queda **cerrado y
aprobado**; el loop de implementación debe seguir estas aclaraciones al pie de la letra.

### 15.1 (MEDIUM #1) Invariante del mapeo posicional + chequeo de consistencia barato

El mapeo posicional (§5.4 método 1) usa `len(plano) == len(questions_likert)` como condición de
aplicabilidad. Esto NO detecta un reordenamiento del mismo tamaño (porque el orden del JSON lo
fija el orden de columnas del CSV en `domain_builder`, no el `.txt`). Se resuelve así, de forma
**vinculante**:

1. **Invariante declarado (dueño: `original_txt.construir_mapa_dimension`).** El mapeo posicional
   ASUME que el orden de los ítems likert del JSON (`q13..q33`) coincide con el orden de lectura
   de los ítems del `.txt`. Este invariante se documenta como comentario en la función y en §11
   (supuesto 2, ya presente). El método **no detecta reordenamientos**; esa limitación es
   explícita y aceptada.

2. **Chequeo de consistencia barato (defensa en profundidad), OBLIGATORIO de implementar.**
   Antes de aceptar el mapeo posicional, extraer el **número de ítem embebido** en el nombre de
   columna del JSON (sufijo `_item(\d+)$`, p.ej. `Motivación_item3` → 3) y comparar su secuencia
   con la posición esperada **dentro de cada grupo de prefijo**. Regla concreta:
   - Agrupar los `questions_likert` por su prefijo normalizado (hasta `_item`), preservando el
     orden de aparición.
   - Para cada grupo, los números `_item\d+` deben ser **consecutivos y crecientes desde 1**
     (1,2,3…). Si en algún grupo la secuencia no es `1..k` creciente, se considera que el orden
     del JSON no es fiable para el mapeo posicional ⇒ **degradar a prefijo** con `WARNING`
     (`"orden de ítems no monotónico; se usa agrupación por prefijo"`).
   - Este chequeo es O(n) y no requiere el `.txt`. En inst_1 cada grupo (`Organización_y_` 1..7,
     `Habilidades_par` 1..3 y de nuevo 1..3, `Motivación` 1..3, `Recursos_de_apr` 1..3,
     `Estrategias_de_` 1..3) es monotónico por grupo, así que pasa y se usa el posicional.
   - NOTA sobre la colisión `Habilidades_par` (dos grupos 1..3): el chequeo se hace **por grupo
     de aparición contigua**, no por prefijo global, de modo que las dos tandas de
     `Habilidades_par_item1..3` se validan por separado y ambas son monotónicas. El posicional
     sigue siendo el método correcto (las separa por posición contra el `.txt`); el chequeo solo
     descarta reordenamientos patológicos.
   - Si el chequeo pasa pero `len(plano) != len(questions_likert)`, manda la condición de conteo
     (ya en §5.4): se degrada a prefijo. Ambas condiciones deben cumplirse para usar posicional.

   Registrar a nivel `INFO` el método finalmente usado (`posicional` | `prefijo`) y, si fue
   `prefijo`, el motivo (`conteo_desigual` | `orden_no_monotonico` | `sin_txt`).

### 15.2 (MEDIUM #2) Reescritura explícita de la precedencia de título en `extraer_metadata`

Hoy `sources.extraer_metadata` calcula
`titulo = instrument.title or dc:title or f"Instrumento {id}"`, con `instrument.title` (el nombre
del CSV) **por delante** de `dc:title`. Esto es lo contrario de la precedencia pedida. Añadir solo
un parámetro `titulo_override` NO basta: hay que **reordenar** la fórmula interna. Especificación
vinculante:

1. `extraer_metadata(instrumento_json, instrumento_id, titulo_override: str | None = None)`
   calcula el título con esta precedencia EXACTA (reemplazando la actual):

   ```python
   titulo = (
       _texto(dublin_core.get("dc:title"))      # 1º: título Dublin Core si el investigador lo puso
       or _texto(titulo_override)               # 2º: título legible del .txt (cabecera "INSTRUMENTO:")
       or _texto(instrument.get("title"))       # 3º: instrument.title (nombre del CSV) — último recurso
       or f"Instrumento {instrumento_id}"
   )
   ```

   Es decir, se **REORDENA** la precedencia actual (dc:title sube al primer puesto; el nombre del
   CSV baja al tercero). Este cambio es intencional y es el núcleo del fix F3/MEDIUM#2.

2. **Un único punto de verdad para el título.** Tanto el **chunk de cabecera de estructura**
   (§6.1) como la **metadata de Chroma** (§6.2) DEBEN derivar el título llamando a la misma
   `extraer_metadata(..., titulo_override=estructura.titulo_instrumento)`. No se calcula el título
   en dos sitios con lógicas distintas; `construir_chunks` obtiene el título una vez (vía
   `extraer_metadata`) y lo reutiliza para la cabecera. Esto elimina la posible divergencia que
   señaló la revisión entre §6.1 y §6.2.

3. **Compatibilidad de firma.** El tercer parámetro es opcional con default `None`, así que las
   llamadas existentes de `extraer_metadata(json, id)` siguen compilando; su comportamiento solo
   cambia en el orden de precedencia del título (que es justo lo que se quiere corregir). Revisar
   si algún test existente fija el comportamiento viejo (nombre del CSV como título) y
   actualizarlo para reflejar la nueva precedencia (dc:title/.txt primero).

### 15.3 NITs restantes (integrados, no bloqueantes)

- **NIT #3 (fuente de verdad del id).** `construir_chunks` deriva `id_crudo` **del parámetro
  `instrumento_id` del router** (vía `removeprefix("upload_")`); `artefacto["instrument_id"]` solo
  se usa como respaldo si el parámetro no parsea a entero. Documentado en §5.1/§8.
- **NIT #4 (chunks de estructura cortos).** Tras aplanar (§6.4), descartar toda pieza cuyo
  `texto.strip()` tenga longitud `< chunking.MIN_LONGITUD` (40), igual que hace `trocear` hoy,
  para no indexar piezas casi vacías. La cabecera y los chunks de hallazgos normales superan ese
  umbral con holgura; el descarte solo afecta a dimensiones patológicamente vacías.
- **NIT #5 (resumen global sin cierto tipo).** `redactar_resumen_global` selecciona hallazgos
  salientes de forma defensiva: si no hay dimensiones likert, omite las cláusulas de media
  alta/baja; si no hay numéricas, omite la cláusula numérica; si `hallazgos` está vacío, reporta
  solo `n` y la lista (posiblemente vacía) de dimensiones evaluadas, sin inventar cifras.

### 15.4 Estado del diseño

Con §15.1–§15.3 integrados, los 0 HIGH / 2 MEDIUM / 3 NIT de la última revisión quedan resueltos
en la especificación. El diseño está **aprobado para implementación**. El loop de implementación
debe tratar §15 como parte normativa del diseño (igual que §4–§9).
