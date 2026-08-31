---
inclusion: manual
---

# Modelo de Conocimiento — Indagata
## Separación entre información operativa e información semántica

**Versión:** 1.1  
**Fecha:** Agosto 2026  
**Propósito:** Definir el modelo de conocimiento correcto antes de cualquier implementación del pipeline semántico.  
**Documento relacionado:** `chunking_strategy.md` — Estrategia de Intelligent Enriched Chunking (IEC).

---

## Principio rector

Un sistema RAG tiene dos planos que no deben mezclarse:

**Plano operativo:** El sistema sabe *dónde está* el conocimiento, *quién lo cargó*, *cuándo llegó* y *en qué estado se encuentra*. Esta información sirve para operar, auditar y administrar el sistema. No aporta nada a la calidad de una respuesta generada.

**Plano semántico:** El sistema sabe *qué significa* ese conocimiento, *a quién describe*, *qué fenómenos educativos aborda*, *qué indicadores están presentes* y *en qué contexto fue producido*. Esta información es la que transforma una búsqueda vectorial en una respuesta útil.

Un embedding generado sobre `hash_md5`, `usuario_carga` o `ruta_original` no solo no ayuda: introduce ruido en el espacio vectorial. El modelo semántico debe contener exclusivamente información que un lector humano experto consideraría relevante para responder una pregunta educativa.

---

## 1. Modelo operativo — Información del sistema

### Propósito
Control interno, auditoría, trazabilidad técnica y administración del ciclo de vida del instrumento dentro del sistema.

### Dónde vive: PostgreSQL (schema `tt_rag`)

| Campo | Tabla | Tipo | Justificación |
|---|---|---|---|
| `instrumento_id` | `instrumento_procesado` | Integer PK | Identificador interno del sistema |
| `codigo` | `instrumento_procesado` | VARCHAR(20) | Código legible (ENC-042). Referencia humana, no semántica |
| `estado` | `instrumento_procesado` | VARCHAR(50) | Estado del pipeline (ingresado → vectorizado) |
| `fecha_procesamiento` | `instrumento_procesado` | DateTime | Cuándo fue procesado |
| `ruta_json` | `instrumento_procesado` | Text | Ruta al archivo JSON semántico en disco |
| `ruta_sav` | `instrumento_procesado` | Text | Ruta a versión SPSS |
| `hash_md5` | `raw_data` | VARCHAR(32) | Detección de duplicados |
| `usuario_carga` | `raw_data` | Integer FK | Quién cargó el archivo |
| `fecha_carga` | `raw_data` | DateTime | Cuándo llegó el archivo |
| `ruta_original` | `raw_data` | Text | Ubicación del archivo crudo para descarga |
| `nombre_original` | `raw_data` | VARCHAR(255) | Nombre del archivo tal como lo subió el usuario |
| `tipo_mime` | `raw_data` | VARCHAR(100) | Tipo MIME del archivo |
| `tamano_bytes` | `raw_data` | Integer | Tamaño del archivo |
| `schema_version` | `instrumento_procesado` | VARCHAR(10) | Versión del schema JSON usado |
| `vector_id` | `documento_vectorizado` | Text | ID del chunk en ChromaDB |
| `col_id` | `documento_vectorizado` | Text | Colección en ChromaDB |
| `tipo_chunk` | `documento_vectorizado` | VARCHAR(50) | Tipo del chunk vectorizado |
| `pregunta` / `respuesta` / `latencia` | `rag_log` | Varios | Auditoría de consultas RAG |
| `prompt_version` | `prompt` | Integer | Versionado de prompts del sistema |

### Regla de acceso
Esta información se consulta para: administrar el sistema, descargar el original, monitorear el pipeline, auditar consultas. **Nunca** se incluye en el contenido que será embebido ni en los metadatos de ChromaDB.

---

## 2. Modelo semántico — Representación de conocimiento

### Propósito
Ser la única fuente que alimenta el proceso de chunking, generación de embeddings y recuperación semántica. Cada campo debe responder a la pregunta: *¿esto ayuda al sistema a responder mejor una pregunta educativa?*

### Criterio de inclusión
Un campo pertenece al modelo semántico si cumple al menos una de estas condiciones:
- Un investigador lo necesita para interpretar correctamente los hallazgos del instrumento.
- Permite discriminar si este instrumento es relevante para una consulta educativa específica.
- Aporta contexto que el LLM necesita para generar una respuesta precisa y no alucinada.
- Habilita filtros temáticos, temporales o institucionales en la búsqueda semántica.

### Dónde vive: JSON semántico en `/storage/json/{instrumento_id}.json` + metadatos en ChromaDB

---

## 3. Distribución de campos en ChromaDB

ChromaDB almacena dos cosas por cada chunk: el **embedding** (calculado sobre el contenido textual) y los **metadatos** (campos estructurados para filtrado). Son dos espacios con propósitos distintos.

### 3.1 Metadatos de ChromaDB — Para filtrado y post-recuperación

Los metadatos no se embedden. Se usan para: acotar búsquedas (filtros `where`), enriquecer la respuesta generada, y mostrar la fuente al usuario.

| Campo en ChromaDB | Tipo | Uso |
|---|---|---|
| `instrumento_id` | int | Trazabilidad de vuelta a PostgreSQL |
| `codigo_instrumento` | string | Referencia legible en la respuesta (ENC-042) |
| `tipo_instrumento` | string | Filtro: encuesta / entrevista / prueba_estandarizada |
| `tipo_chunk` | string | Filtro: resumen / hallazgo / unidad_semantica |
| `titulo` | string | Mostrar al usuario como fuente |
| `institucion` | string | Filtro por institución |
| `periodo` | string | Filtro temporal (ej. "2023-1") |
| `poblacion` | string | Contexto de la fuente en la respuesta |
| `idioma` | string | Filtro de idioma |
| `kpis_ids` | string (JSON list) | Filtro semántico por KPI educativo |
| `kpis_nombres` | string | Mostrar KPIs asociados en la respuesta |
| `dimension` | string | Para chunks de tipo unidad_semantica: nombre de la dimensión |
| `score_relevancia` | float | Calculado durante indexación, usado en re-ranking |

**Nota sobre `kpis_ids`:** ChromaDB no soporta listas nativas en metadatos para filtros `$contains`. Se serializa como string JSON `"[3, 7, 12]"` y se filtra con `$contains` sobre el string. Limitación conocida del motor.

### 3.2 Contenido embebido — Lo que genera el vector

El embedding se calcula sobre el texto que realmente captura el significado semántico de ese chunk. Regla: si lo lees en voz alta y tiene sentido como conocimiento educativo, pertenece aquí. Si es un identificador o una ruta, no.

**Para chunk tipo `resumen_instrumento`:**
El contenido embebido es una narrativa que integra: qué es el instrumento, quién lo produce, a quién estudia, en qué periodo, con qué objetivo, qué fenómenos educativos aborda, qué KPIs están presentes y cuáles son los hallazgos principales.

**Para chunk tipo `unidad_semantica`:**
El contenido embebido es: nombre de la dimensión o sección + descripción de lo que mide + preguntas o ítems representativos + hallazgos o tendencias observadas en esa dimensión + KPIs relacionados con esa dimensión.

**Para chunk tipo `hallazgo`:**
El contenido embebido es: enunciado del hallazgo + evidencia cuantitativa o cualitativa que lo soporta + KPI al que aporta + implicaciones o contexto interpretativo.

**Lo que nunca se embede:** identificadores numéricos, rutas de archivo, fechas de carga, hashes, versiones de schema, nombres de usuario, estados del pipeline.

---

## 4. JSON semántico — Nueva propuesta

Este archivo es la representación de conocimiento del instrumento. No es un registro del sistema. No contiene datos administrativos.

```
instrumento_semantico.json
│
├── contexto                  ← Quién produce este conocimiento, sobre quién y cuándo
│   ├── titulo
│   ├── tipo_instrumento
│   ├── descripcion
│   ├── objetivo
│   ├── institucion_responsable
│   ├── poblacion_alcance
│   ├── periodo_inicio / periodo_fin
│   ├── idioma
│   ├── condiciones_uso
│   └── palabras_clave[]
│
├── dublin_core               ← Estandarización ISO 15836 para interoperabilidad
│   ├── dc_title
│   ├── dc_creator
│   ├── dc_subject[]
│   ├── dc_description
│   ├── dc_publisher
│   ├── dc_contributor
│   ├── dc_date
│   ├── dc_type
│   ├── dc_format
│   ├── dc_identifier         ← Identificador semántico (IND-ENC-042), NO el ID interno
│   ├── dc_source
│   ├── dc_language
│   ├── dc_relation
│   ├── dc_coverage
│   └── dc_rights
│
├── especifico                ← Metadatos propios del tipo de instrumento
│   └── (ver subsecciones 4.1, 4.2, 4.3)
│
├── kpis_inferidos[]          ← Vinculación con indicadores educativos
│   └── cada item:
│       ├── kpi_id
│       ├── nombre_kpi
│       ├── descripcion_kpi
│       ├── evidencia_textual    ← Por qué este instrumento aporta a este KPI
│       ├── score_inferencia
│       └── secciones_relacionadas[]
│
└── unidades_semanticas[]     ← Unidades de conocimiento para chunking
    └── cada item:
        ├── id_chunk            ← Identificador dentro de este documento (chunk_001)
        ├── tipo                ← resumen / hallazgo / dimension / seccion / area_competencia
        ├── titulo
        ├── descripcion
        ├── contenido_narrativo  ← Texto enriquecido listo para embedding
        ├── kpis_asociados[]    ← KPI IDs vinculados a esta unidad
        └── datos_cuantitativos ← Estadísticas o valores si aplica (opcional)
```

### 4.1 Bloque `especifico` para Encuestas

```
especifico:
  n_items_total
  escala_respuesta          ← "Likert 1-5", "Sí/No", "Opción múltiple"
  dimensiones[]:
    nombre_dimension
    descripcion
    n_items
    items_representativos[]
    hallazgos_observados     ← Texto libre con resultados de esa dimensión
  metodologia_aplicacion    ← "Autoadministrada", "Asistida", "En línea"
  tasa_respuesta            ← Si está disponible
  limitaciones[]
```

### 4.2 Bloque `especifico` para Entrevistas

```
especifico:
  tipo_entrevista           ← "Semiestructurada", "Estructurada", "Grupos focales"
  n_preguntas_guia
  duracion_estimada
  guion_tematico[]:
    tema
    pregunta_guia
    preguntas_de_profundizacion[]
    hallazgos_cualitativos   ← Síntesis de respuestas observadas
  perfil_entrevistados
  tecnica_analisis          ← "Análisis de contenido", "Análisis temático"
  limitaciones[]
```

### 4.3 Bloque `especifico` para Pruebas estandarizadas

```
especifico:
  n_reactivos_total
  areas_competencia[]:
    nombre_area
    descripcion
    n_reactivos
    nivel_cognitivo          ← Taxonomía Bloom: recordar / comprender / aplicar...
    hallazgos_observados
  escala_calificacion
  normas_referencia          ← Nacional, internacional, institucional
  poblacion_normativa
  coeficiente_confiabilidad  ← Alpha de Cronbach si aplica
  validez                    ← Tipo de evidencia de validez
  limitaciones[]
```

---

## 5. Trazabilidad semántica entre chunks y documentos

### El problema

Cada chunk recuperado por el retriever debe poder ser atribuido a su instrumento de origen. Esta atribución tiene dos propósitos distintos que requieren soluciones distintas:

- **Atribución técnica:** el sistema necesita saber a qué instrumento pertenece el chunk para presentar la fuente al usuario y para registrar en `rag_log`. Esta es trazabilidad de sistema.
- **Atribución semántica:** el LLM necesita saber de qué instrumento, institución y periodo proviene la evidencia para generar una respuesta correctamente contextualizada. Si no lo sabe, generará atribuciones incorrectas aunque el dato sea verdadero. Esta es trazabilidad de conocimiento.

Estas dos necesidades no se resuelven con el mismo mecanismo.

### Solución en tres capas

**Capa 1 — Metadatos de ChromaDB (trazabilidad técnica)**

`instrumento_id` y `codigo_instrumento` viven en los metadatos del chunk, nunca en el contenido embebido. ChromaDB los devuelve junto con cada resultado de búsqueda sin que hayan influido en el vector. Esta capa resuelve: ¿a qué registro de PostgreSQL apunta este chunk? ¿Qué código legible mostrar al usuario como fuente?

**Capa 2 — Ancla semántica en el contenido (trazabilidad de significado)**

Cada chunk incluye una frase de anclaje al inicio del contenido embebido que lleva contexto interpretativo, no datos administrativos. Esta frase integra los elementos semánticos mínimos para que el dato del chunk sea interpretable de forma autónoma:

```
"En [tipo de instrumento] sobre [tema principal], aplicado por [institución] 
a [descripción de la población] durante [periodo]..."
```

Ejemplo concreto:
```
"En la encuesta de satisfacción estudiantil aplicada por la Universidad 
Autónoma del Estado a estudiantes de licenciatura durante el ciclo 2023-1, 
la dimensión de Experiencia Docente muestra que..."
```

Esto no es información administrativa. Es el contexto sin el cual el dato del chunk no tiene significado interpretable. El LLM necesita esta información para generar *"Según la encuesta aplicada por X en 2023-1..."* en lugar de *"Según los datos disponibles..."*.

**Capa 3 — Jerarquía de chunks mediante referencia semántica**

El chunk de tipo `resumen_instrumento` actúa como la representación completa del documento. Los demás chunks son hijos semánticos de ese resumen. La relación jerárquica se expresa en los metadatos de ChromaDB mediante el campo `chunk_padre`, que apunta al `id_chunk` del resumen (por ejemplo `chunk_000`), no a un ID de base de datos.

Esta jerarquía habilita una estrategia de recuperación en dos pasos cuando se necesita: recuperar los chunks más relevantes y luego recuperar el resumen del instrumento al que pertenecen para construir una respuesta con mayor contexto.

### Regla de diseño

> El contenido embebido nunca contiene identificadores, rutas, fechas de carga ni ningún dato cuyo único propósito sea operar el sistema. Contiene únicamente información que un investigador necesita para interpretar correctamente la evidencia.

---

## 6. Chunks de tipo hallazgo — Justificación del modelo independiente

### Por qué los hallazgos merecen chunks propios

Los hallazgos son el conocimiento destilado del instrumento: son la respuesta directa a las preguntas que los usuarios de la plataforma van a hacer. Cuando un investigador consulta *"¿qué dice la evidencia sobre la deserción en instituciones públicas?"* o *"¿qué hallazgos existen sobre bienestar estudiantil en 2023?"*, la respuesta más útil y precisa no es el resumen completo del instrumento sino el hallazgo específico que aborda esa pregunta.

Si los hallazgos permanecen embebidos dentro del chunk de su dimensión o sección, el retriever solo los recupera cuando también recupera el contenido completo de esa dimensión. Esto tiene dos consecuencias negativas:

- El chunk puede superar el contexto óptimo de embedding (demasiado texto diluye la señal semántica del hallazgo específico).
- El score de similitud se calcula sobre la unidad completa, no sobre el hallazgo. Una pregunta muy específica puede no recuperar el chunk correcto aunque el hallazgo esté presente dentro de él.

Un chunk de hallazgo independiente tiene mayor probabilidad de ser el top-1 o top-2 recuperado para preguntas directas sobre resultados, evidencia o cifras específicas.

### El riesgo: hallazgo huérfano

Un chunk de hallazgo sin contexto suficiente crea un problema grave de atribución. El LLM recibe *"el 67% de los estudiantes reportó intención de abandono"* sin saber de qué instrumento, institución, año o población proviene. La respuesta generada puede ser factualmente correcta en el dato pero incorrecta en la atribución, que es exactamente el tipo de error que una plataforma académica no puede permitir.

### Solución: hallazgo con contexto heredado mínimo

El chunk de tipo `hallazgo` no es solo el enunciado del hallazgo. Incluye:

1. **Ancla semántica** (heredada del instrumento): tipo + institución + periodo + población. Igual que en cualquier otro chunk.
2. **Enunciado del hallazgo**: el hallazgo principal en texto claro.
3. **Evidencia de soporte**: dato cuantitativo o cualitativo que sustenta el hallazgo.
4. **Vinculación a KPI**: a qué indicador educativo aporta este hallazgo.
5. **Implicación**: qué significa este hallazgo en el contexto educativo (una o dos oraciones interpretativas).

La implicación es importante porque transforma el chunk de un dato crudo en conocimiento interpretable, que es exactamente lo que el LLM necesita para generar respuestas fundamentadas sin alucinar.

### El umbral para chunk independiente

No todos los hallazgos justifican un chunk propio. El criterio es: **¿puede este hallazgo responder de forma autónoma una pregunta educativa relevante?**

- Hallazgo con dato cuantitativo claro + KPI asociado + implicación: chunk independiente.
- Observación descriptiva de una sola oración sin sustento: permanece embebida en la unidad semántica de su dimensión.
- Hallazgo que solo tiene sentido leyendo la dimensión completa: permanece en la unidad semántica.

La generación de chunks de hallazgo es responsabilidad del LLM durante el pipeline de procesamiento. El sistema le instruye para identificar 2-5 hallazgos sustanciales por instrumento que cumplan el umbral.

### Implicación para el modelo de unidades semánticas

La estructura de `unidades_semanticas` en el JSON semántico ahora incluye dos tipos diferenciados:

**Tipo `dimension` / `seccion` / `area_competencia`:** Unidades de contenido del instrumento. Agrupan ítems o preguntas cohesivas. El hallazgo observado en esa unidad se incluye dentro de ella para mantener la coherencia interna.

**Tipo `hallazgo`:** Unidades de conocimiento extraídas. No agrupan preguntas — son la síntesis interpretativa de un resultado significativo. Pueden cruzar dimensiones si el hallazgo involucra más de una. Llevan referencia a las dimensiones de las que fueron extraídos mediante el campo `dimensiones_origen`.

Esta distinción refleja la diferencia entre *la estructura del instrumento* (cómo está organizado) y *el conocimiento que produce* (qué revela).

---

## 7. Estructura actualizada de unidades semánticas

La estructura de `unidades_semanticas` en el JSON semántico es el resultado del proceso de Intelligent Enriched Chunking definido en `chunking_strategy.md`. La cantidad y tipo de unidades es **variable y determinada dinámicamente por el LLM** para cada instrumento. No existe una cantidad fija por tipo de instrumento.

```
unidades_semanticas[]:

  Tipo resumen_instrumento:
    id_chunk                ← siempre "chunk_000". Raíz de la jerarquía.
    chunk_padre             ← null
    tipo                    ← "resumen_instrumento"
    titulo                  ← Título descriptivo del instrumento
    contenido_narrativo     ← Ancla semántica + narrativa completa:
                               qué es, quién lo produce, a quién estudia,
                               qué KPIs aborda, hallazgos globales, limitaciones
    kpis_asociados[]        ← Todos los KPI IDs presentes en el instrumento

  Tipo unidad_semantica:
    id_chunk                ← ej. "chunk_001", "chunk_002". Puede ser "chunk_002a"
                               si es resultado de división por límite de tokens.
    chunk_padre             ← "chunk_000" (siempre el resumen)
    tipo                    ← "unidad_semantica"
    titulo                  ← Nombre de la dimensión, sección o área
    descripcion             ← Qué mide esta unidad (campo del JSON, no embebido)
    contenido_narrativo     ← Ancla semántica + descripción de la unidad +
                               ítems o preguntas representativos (semánticamente) +
                               hallazgos observados en esta unidad +
                               KPIs evidenciados aquí + datos cuantitativos si existen
    kpis_asociados[]        ← KPI IDs vinculados a esta unidad
    datos_cuantitativos     ← Opcional. Estadísticas, n, %, promedios.

  Tipo hallazgo:
    id_chunk                ← ej. "chunk_007"
    chunk_padre             ← "chunk_000" (siempre el resumen)
    tipo                    ← "hallazgo"
    titulo                  ← Enunciado conciso del hallazgo
    dimensiones_origen[]    ← id_chunk[] de las unidades de las que fue extraído
    contenido_narrativo     ← Ancla semántica + enunciado del hallazgo +
                               evidencia cuantitativa o cualitativa de soporte +
                               KPI al que aporta (nombre explícito) +
                               implicación interpretativa (1-2 oraciones)
    kpis_asociados[]        ← Mínimo 1 KPI ID para que sea chunk independiente
    datos_cuantitativos     ← El dato central del hallazgo. Obligatorio si existe.
```

**Nota sobre el campo `plan_chunking`:** El JSON semántico incluye un campo `plan_chunking` que registra el razonamiento del LLM durante el análisis semántico previo a la generación. Este campo no se embebe ni se indexa — existe para auditoría, reproducibilidad y justificación académica del modelo de chunks generado.

---

## 8. Justificación de cada decisión

### Por qué el `dc_identifier` es semántico pero `instrumento_id` no lo es

`instrumento_id` es un número autoincremental de base de datos. No tiene significado fuera del sistema. `dc_identifier` es un código construido con intención (`IND-ENC-042`) que identifica el instrumento como objeto de conocimiento, puede citarse en informes y tiene valor fuera del contexto técnico. El primero es una llave de base de datos; el segundo es un nombre.

### Por qué `kpis_inferidos` pertenece al JSON semántico

Los KPIs no son metadatos administrativos. Son el vínculo entre el instrumento y los fenómenos educativos que estudia. Cuando un usuario pregunta *"¿qué instrumentos abordan deserción escolar?"*, el sistema necesita que esa vinculación esté disponible para el retriever y para el LLM al construir la respuesta. Si solo estuviera en PostgreSQL, el RAG no lo vería sin un paso adicional de consulta relacional en cada búsqueda.

### Por qué `evidencia_textual` en `kpis_inferidos`

No es suficiente con decir que un instrumento está relacionado con el KPI "Tasa de deserción". El LLM necesita saber *cómo* está relacionado para generar una respuesta fundamentada. La evidencia textual —"la dimensión 3 del instrumento mide la intención de abandono a través de 8 ítems de satisfacción con el servicio educativo"— es lo que convierte una etiqueta en conocimiento usable.

### Por qué `contenido_narrativo` en `unidades_semanticas`

El embedding no se genera sobre campos estructurados en formato clave-valor. Se genera sobre texto continuo con coherencia semántica. El campo `contenido_narrativo` es una prosa sintetizada que integra el título, la descripción, los hallazgos y los KPIs de esa unidad. Un modelo de embeddings entiende "La dimensión de Satisfacción Académica revela que el 67% de los estudiantes percibe deficiencias en la retroalimentación docente, lo cual se vincula directamente al KPI de Rendimiento Académico" mucho mejor que un JSON con cinco claves separadas.

### Por qué `hallazgos_observados` está dentro de `especifico` y no es una sección aparte

Los hallazgos de una dimensión son inseparables de la dimensión misma. Separarlos crearía chunks huérfanos sin contexto suficiente. El retriever necesita recuperar "la dimensión X muestra el hallazgo Y" como una unidad, no en dos fragmentos que requieren ser reunidos por el LLM.

### Por qué `datos_cuantitativos` es opcional

No todos los instrumentos tienen datos cuantitativos procesables. Una entrevista cualitativa no tiene porcentajes. Forzar ese campo introduciría valores vacíos o fabricados, que degradan la calidad del embedding. Lo que no existe no debe representarse.

### Por qué `periodo_inicio` / `periodo_fin` en `contexto` y en metadatos de ChromaDB

En `contexto` del JSON semántico porque el LLM necesita saber cuándo fue aplicado el instrumento para generar respuestas temporalmente precisas ("este instrumento del ciclo 2023-1 muestra..."). En metadatos de ChromaDB porque el retriever necesita poder filtrar por periodo cuando el usuario consulta tendencias en un rango de tiempo específico. Sirve a dos propósitos distintos en dos capas distintas.

### Por qué `palabras_clave` en `contexto` y `dc_subject` en Dublin Core son campos distintos

`palabras_clave` son los términos que el equipo investigador asignó libremente al instrumento. `dc_subject` es la clasificación formal según el estándar Dublin Core, que puede incluir tesauros controlados como UNESCO o ERIC. Tienen origen diferente y propósitos diferentes: las palabras clave mejoran la búsqueda coloquial; el subject Dublin Core habilita interoperabilidad con repositorios institucionales.

---

## 9. Tabla de decisión — Dónde va cada tipo de información

| Tipo de información | PostgreSQL | JSON semántico | Metadatos ChromaDB | Contenido embebido |
|---|:---:|:---:|:---:|:---:|
| Identificadores internos (IDs, hashes) | ✓ | — | — | — |
| Trazabilidad técnica (rutas, fechas de carga, mime) | ✓ | — | — | — |
| Estado del pipeline | ✓ | — | — | — |
| Auditoría de consultas RAG | ✓ | — | — | — |
| Versiones de schema y prompts | ✓ | — | — | — |
| Metadatos Dublin Core | referencia FK | ✓ | filtro parcial | ✓ (en narrativa) |
| Contexto del instrumento (titulo, objetivo, institución) | referencia FK | ✓ | ✓ (filtro) | ✓ (ancla semántica) |
| Metadatos específicos por tipo | — | ✓ | — | ✓ (en narrativa) |
| KPIs inferidos con evidencia | ✓ (pregunta_kpi) | ✓ | ✓ (IDs para filtro) | ✓ (evidencia en narrativa) |
| Hallazgos sustanciales (con umbral) | — | ✓ (chunk propio) | ✓ (tipo_chunk=hallazgo) | ✓ (con ancla + evidencia + implicación) |
| Hallazgos menores (sin umbral) | — | ✓ (dentro de dimensión) | — | ✓ (embebidos en su unidad) |
| Datos cuantitativos | — | ✓ (opcional) | — | ✓ (si existen) |
| Identificador semántico (dc_identifier) | — | ✓ | ✓ (código legible) | — |
| Periodo de aplicación | ✓ (FK a metadatos) | ✓ | ✓ (filtro) | ✓ (ancla semántica) |
| Institución responsable | ✓ (FK a instituciones) | ✓ | ✓ (filtro) | ✓ (ancla semántica) |
| Jerarquía chunk → resumen | — | ✓ (chunk_padre) | ✓ (chunk_padre) | — |
| Ancla semántica (tipo+institución+periodo+población) | — | — | — | ✓ (preámbulo de todo chunk) |
| Referencia a dimensiones origen (en hallazgo) | — | ✓ (dimensiones_origen) | — | — |

---

## 10. Resumen del modelo

**PostgreSQL** es la fuente de verdad operativa. Gestiona el ciclo de vida, la trazabilidad, los registros de auditoría y las relaciones entre entidades del sistema.

**JSON semántico** es la representación de conocimiento. Es el único artefacto que alimenta el pipeline de vectorización. Contiene exclusivamente información que un experto educativo necesita para interpretar el instrumento y que el LLM necesita para responder preguntas sobre él. Incluye la jerarquía de chunks mediante `chunk_padre` y `dimensiones_origen`.

**Metadatos de ChromaDB** son el índice de filtrado semántico. Permiten acotar búsquedas por dimensiones relevantes (tipo, institución, KPI, periodo, jerarquía) sin necesidad de embeddings. Son un subconjunto del JSON semántico seleccionado por su utilidad como filtro o trazabilidad técnica.

**Contenido embebido** es la narrativa de conocimiento. Es texto continuo que abre siempre con el ancla semántica del instrumento de origen (tipo + institución + periodo + población) y desarrolla el significado específico de esa unidad. El ancla garantiza que cada chunk sea interpretable de forma autónoma sin contener datos administrativos. Es lo que el modelo de embeddings convierte en un vector de significado y lo que el LLM usa para generar respuestas correctamente atribuidas.
